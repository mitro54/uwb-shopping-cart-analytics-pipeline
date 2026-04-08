# Datan Sukupuu (Data Lineage)

Tämä kaavio esittää tarkasti dbt-projektimme datamallien riippuvuudet toisistaan. Se on datainsinöörin vastine arkkitehtuurikuvalle – se ei kerro _mitä järjestelmiä käytämme_, vaan _miten data virtaa tiedostosta toiseen_ ja mitä `ref()` -viittauksia mallit käyttävät.

```mermaid
graph LR
    %% Data Sources
    subgraph Lähdedata
        CSV[(Raw CSV Data\n'Ostoskärryjen \n sensoridata')]
    end

    %% Bronze Layer
    subgraph Staging - Bronze
        bronze_csv_data{{bronze_csv_data.sql\n'Datan luku ja validointi'}}
    end

    %% Silver Layer
    subgraph Puhdistus - Silver
        silver_positions{{silver_positions.sql\n'Tuotantotason siivous \n& Session_id luonti'}}
    end

    %% Gold Layer
    subgraph Analytiikka - Gold
        f_kaynti{{f_kaynti.sql\n'Fact:\nKauppareissut & Aggregaatit'}}
        dim_karry{{dim_karry.sql\n'Dimension:\nKärryjen metatiedot'}}
        f_osastokaynti{{f_osastokaynti.sql\n'Fact:\nTyhjä / Tuleva malli'}}
    end

    %% Riippuvuudet (dbt ref)
    CSV -->|Datan Ingestio| bronze_csv_data
    bronze_csv_data -->|ref 'bronze_csv_data'| silver_positions
    silver_positions -->|ref 'silver_positions'| f_kaynti
    silver_positions -->|ref 'silver_positions'| dim_karry
    silver_positions -.->|ref 'silver_positions'| f_osastokaynti

    %% Tyylittelyt Medallion -teemalla
    classDef source fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    classDef bronze fill:#cd7f32,stroke:#5c4033,stroke-width:2px,color:#fff
    classDef silver fill:#c0c0c0,stroke:#696969,stroke-width:2px,color:#000
    classDef gold fill:#ffd700,stroke:#b8860b,stroke-width:2px,color:#000

    class CSV source
    class bronze_csv_data bronze
    class silver_positions silver
    class f_kaynti,dim_karry,f_osastokaynti gold
```

### Lineagen Merkitys
Tästä dbt:n sisäisestä hierarkiasta näkee selkeästi, miksi teimme nuo äskeiset korjaukset:
1. Jos `silver_positions` -logiikka (esim. geofence) muuttuu, se valuu **suoraan alas** kaikkiin Gold-tason malleihin (Fakta- ja Dimensiotaulut perivät valmiiksi puhtaan datan).
2. Tuleva osastovierailujen malli (`f_osastokaynti`) on helppo vääntää, koska voimme viitata siinä ainoastaan puhtaaseen Silver-kantaan, jolloin yksikään osastovierailu ei voi syntyä haamudatan, öisten aukioloaikojen ohi tai seinien sisältä!

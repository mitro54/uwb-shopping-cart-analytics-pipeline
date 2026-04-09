# ByteBuddies - Ylätason arkkitehtuuri

Alla on kuvattu projektin ylätason data-arkkitehtuuri, joka noudattaa Medallion-rakennetta (bronze, silver, gold). Tämä kaavio havainnollistaa, miten ostoskärryjen raaka sensoridata muuttuu analytiikassa ja raporteissa käytettäväksi liiketoimintatiedoksi.

```mermaid
graph TD
    classDef source fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:black;
    classDef bronze fill:#cd7f32,stroke:#5c4033,stroke-width:2px,color:black;
    classDef silver fill:#c0c0c0,stroke:#696969,stroke-width:2px,color:black;
    classDef gold fill:#ffd700,stroke:#b8860b,stroke-width:2px,color:black;
    classDef bi fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:black;

    %% Lähdejärjestelmät
    subgraph Data_Sources["Lähdejärjestelmät"]
        CSV["<span style='color:#000 !important'>ostoskärryjen sensoridata<br>csv-tiedostot</span>"]:::source
    end

    %% Data Warehouse / dbt prosessointi
    subgraph DWH["Tietovarasto ja dbt-transformaatiot"]
        
        %% Bronze
        subgraph Bronze["🥉 Bronze-kerros (raakadata)"]
            stg["<span style='color:#000 !important'>bronze_csv_data<br>datan luku ja muodon määritys</span>"]:::bronze
        end
        
        %% Silver
        subgraph Silver["🥈 Silver-kerros (puhdistettu ja rikastettu)"]
            silv["<span style='color:#000 !important'>silver_positions<br>laadun suodatus, geofencing,<br>sessioiden pilkkominen ja jitter-karsinta</span>"]:::silver
        end
        
        %% Gold
        subgraph Gold["🥇 Gold-kerros (liiketoimintadata)"]
            gold_f["<span style='color:#000 !important'>f_kaynti & f_osastokaynti<br>valmiit faktataulut asioinneista</span>"]:::gold
            gold_d["<span style='color:#000 !important'>dim_karry & dim_osastot<br>laitteiston ja kaupan master data</span>"]:::gold
        end

        stg -->|dbt run| silv
        silv -->|dbt run| gold_f
        silv -->|dbt run| gold_d
    end

    %% Raportointi ja Analyysi
    subgraph Analytics["Loppukäyttö ja analytiikka"]
        BI["<span style='color:#000 !important'>Power BI / analytiikkatyökalut<br>esim. odbc-yhteyden yli</span>"]:::bi
    end

    CSV -.->|ingestio / lataus| stg
    gold_f --> BI
    gold_d --> BI
```

## Arkkitehtuurin vaiheet:
1. **Lähdejärjestelmät:** Ostoskärryt tuottavat reaaliaikaista (viiveellä siirrettävää) lokaatiodataa csv-muodossa. Z-koordinaatti on rajattu heti alussa pois keveyden vuoksi.
2. **Bronze (raakadata):** `bronze_csv_data` -malli ottaa datan vastaan muuttumattomana. Tässä vaiheessa tiedot validoidaan teknisesti (tietotyypit).
3. **Silver (puhdistettu ja rikastettu):** `silver_positions` -malli putsaa epäilyttävät datapisteet pois schemassa määriteltyjen rajojen mukaisesti (esim. q > 35) ja laskee nopeuden (m/s) sekä etäisyydet esilaskentana. Tässä kerroksessa toteutetaan ankarat tuotantotason siivoussäännöt: geofencing (rajojen ja lataustelakoiden poisto), aukioloaikojen suodatus, sekä pitkien signaalitaukojen (yli 15 min) pilkkominen eri asioinneiksi uuden `session_id`:n avulla.
4. **Gold (liiketoimintadata):** Viedään data tasolle, jossa se vastaa suoraan liiketoiminnan kysymyksiin: kuinka pitkiä kauppareissut ovat ja millä alueilla karttaa vietetään eniten aikaa. Sisältää valmiit faktataulut (`f_kaynti`, `f_osastokaynti`) sekä dimensiotaulut (`dim_osastot`, `dim_karry`), muodostaen yhdessä helppokäyttöisen tähtimallin (star schema).
5. **Loppukäyttö:** Helposti hyödynnettävä ja skaalautuva muoto, johon analyytikot tai BI-työkalut (esim. Power BI) voivat yhdistää suoraan, välttäen raskaiden kyselyiden pyörittämistä lennosta.

# Silver-kerroksen Logiikkakaavio (silver_positions.sql)

Silver-kerroksen dbt-malli sisältää erittäin rikkaan CTE-rakenteen (Common Table Expressions), jonka läpi alkuperäinen tutkijan kehittämä datanpuhdistuslogiikka ohjelmoitiin. Jokainen tietokantakyselyn vaihe putsaa tai rikastaa dataa eteenpäin seuraavalle tasolle. 

Alla on esitetty vuokaaviona tämän jättimäisen kyselyn toimintalogiikka ja suodattimet:

```mermaid
graph TD
    %% TYYLITTELYT
    classDef bronze fill:#cd7f32,stroke:#5c4033,stroke-width:2px,color:#fff;
    classDef cte fill:#f5f5f5,stroke:#999,stroke-width:1px,color:#333;
    classDef filter fill:#ffebee,stroke:#c62828,stroke-width:1.5px,color:#000;
    classDef process fill:#e3f2fd,stroke:#1565c0,stroke-width:1.5px,color:#000;
    classDef silver fill:#c0c0c0,stroke:#696969,stroke-width:2px,color:#000;

    %% ALKU
    STG["stg_csv_data (Bronze-taulu)"]:::bronze

    %% CTE 1
    subgraph CTE1 [1. Peruspuhdistus CTE]
        STG --> F1{"Pisteiden salli-laatu (q > 0)"}:::filter
        F1 --> F2{"Geofencing (Kaupan rajojen varmentaminen)"}:::filter
        F2 --> F3{"Latauspisteiden (häiriöt) eliminointi"}:::filter
        F3 --> F4{"Myymälän aukioloaikojen karsinta (Aamu-Ilta)"}:::filter
    end

    %% CTE 2
    subgraph CTE2 [2. Liikkeet CTE]
        F4 --> P1["Window function: Hae kärryn edellinen X, Y ja Aika (LAG)"]:::process
    end

    %% CTE 3
    subgraph CTE3 [3. Rikastettu CTE]
        P1 --> P2["Laske kuljettu etäisyys metriksi (Pythagoras / 100.0)"]:::process
        P2 --> P3["Laske aikaero (sekuntit_edellisestä)"]:::process
    end

    %% CTE 4
    subgraph CTE4 [4. Jitter-suodatus CTE]
        P3 --> F5{"Datahyppy yli seinien? (Estä nopeudet > 3.0 m/s)"}:::filter
    end

    %% CTE 5
    subgraph CTE5 [5. Sessiomerkintä CTE]
        F5 --> P4["Session Katkaisu: Jos aikaero > 15 min, liputa rivi is_new_session = 1"]:::process
    end

    %% CTE 6
    subgraph CTE6 [6. Sessiot CTE (Generointi)]
        P4 --> P5["Laske kumulatiivinen SUM() lipuista saadaksesi session_id"]:::process
        P5 --> P6["Luo uniikki reissukoodi full_session_id (MD5 hash)"]:::process
    end

    %% LOPPU (TAULU)
    P6 -.-> OUT["silver_positions (Silver-taulu valmistuu)"]:::silver
```

### Logiikan Vaiheet tiivistettynä:
Tällä palasista (CTE) koostetulla rakenteella saamme siivottua miljoonia rivejä signaalimeteliä äärimmäisellä suorituskyvyllä.
Koska dbt ketjuttaa nämä CTE:t peräkkäin yhdeksi koodi-blokiksi, se pystyy samanaikaisesti hyppäämään virheellisiksi leimattujen pisteiden yli ja silti luomaan myöhemmin tarkat ajantasaiset reitit ja keston mittarit, täysin häiriövapaasti.

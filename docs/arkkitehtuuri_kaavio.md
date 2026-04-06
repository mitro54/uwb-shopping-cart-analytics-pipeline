# ByteBuddies - Ylätason Arkkitehtuuri

Alla on kuvattu projektin ylätason data-arkkitehtuuri, joka noudattaa Medallion-rakennetta (Bronze, Silver, Gold). Tämä kaavio havainnollistaa, miten ostoskärryjen raaka sensoridata muuttuu analytiikassa ja raporteissa käytettäväksi liiketoimintatiedoksi.

```mermaid
graph TD
    classDef source fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    classDef bronze fill:#cd7f32,stroke:#5c4033,stroke-width:2px,color:#fff;
    classDef silver fill:#c0c0c0,stroke:#696969,stroke-width:2px,color:#000;
    classDef gold fill:#ffd700,stroke:#b8860b,stroke-width:2px,color:#000;
    classDef bi fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;

    %% Lähdejärjestelmät
    subgraph Data_Sources["Lähdejärjestelmät"]
        CSV[Ostoskärryjen sensoridata<br>csv-tiedostot]:::source
    end

    %% Data Warehouse / dbt prosessointi
    subgraph DWH["Tietovarasto & dbt-transformaatiot"]
        
        %% Bronze
        subgraph Bronze["🥉 Bronze-kerros (Raakadata)"]
            stg[stg_csv_data<br>Datan luku ja muodon määritys]:::bronze
        end
        
        %% Silver
        subgraph Silver["🥈 Silver-kerros (Puhdistettu & Rikastettu)"]
            silv[silver_positions<br>Laadun suodatus, Geofencing,<br>Sessioiden pilkkominen & Jitter-karsinta]:::silver
        end
        
        %% Gold
        subgraph Gold["🥇 Gold-kerros (Liiketoimintadata)"]
            gold_visits[Kauppareissut ja osastovierailut<br>Käyttömäärät]:::gold
            gold_routes[Reitit ja kuumuuskartat]:::gold
        end

        stg -->|dbt run| silv
        silv -->|dbt run| gold_visits
        silv -->|dbt run| gold_routes
    end

    %% Raportointi ja Analyysi
    subgraph Analytics["Loppukäyttö & Analytiikka"]
        BI[Analytiikka & Visualisointi<br>esim. raportointityökalut]:::bi
    end

    CSV -.->|Ingestio / Datan lataus| stg
    gold_visits --> BI
    gold_routes --> BI
```

## Arkkitehtuurin vaiheet:
1. **Lähdejärjestelmät:** Ostoskärryt tuottavat reaaliaikaista (viiveellä siirrettävää) lokaatiodataa CSV-muodossa. Z-koordinaatti on rajattu heti alussa pois keveyden vuoksi.
2. **Bronze (Raakadata):** `stg_csv_data` -malli ottaa datan vastaan muuttumattomana. Tässä vaiheessa tiedot validoidaan teknisesti (tietotyypit).
3. **Silver (Puhdistettu & Rikastettu):** `silver_positions` -malli putsaa epäilyttävät datapisteet pois `q`-arvon avulla ja laskee nopeuden (m/s) sekä etäisyydet. Tässä kerroksessa toteutetaan ankarat tuotantotason siivoussäännöt: Geofencing (rajojen ja lataustelakoiden poisto), aukioloaikojen suodatus, sekä pitkien signaalitaukojen (yli 15 min) pilkkominen eri asioinneiksi uuden `session_id`:n avulla.
4. **Gold (Liiketoimintadata):** Viedään data tasolle, jossa se vastaa suoraan liiketoiminnan kysymyksiin: kuinka pitkiä kauppareissut ovat ja millä alueilla karttaa vietetään eniten aikaa. Tässä vaiheessa validoidaan koko reissut (poistetaan esim. liian lyhyet alle 3 minuutin, tai matkallisesti (alle 30m) olemattomat "haamuasioinnit" kokonaan analytiikasta).
5. **Loppukäyttö:** Helposti hyödynnettävä ja skaalautuva muoto, johon analyytikot tai BI-työkalut voivat yhdistää suoraan.

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
            silv_diag["<span style='color:#000 !important'>silver_device_diagnostics<br>Laitteistoliputukset (ei roskan poistoa)</span>"]:::silver
        end
        
        %% Gold
        subgraph Gold["🥇 Gold-kerros (liiketoimintadata)"]
            gold_f["<span style='color:#000 !important'>f_kaynti & f_osastokaynti<br>valmiit faktataulut asioinneista</span>"]:::gold
            gold_d["<span style='color:#000 !important'>dim_karry & dim_osastot<br>kaupan master data</span>"]:::gold
            gold_iot["<span style='color:#000 !important'>f_verkko_laatu & f_laite_status<br>Laitteisto- ja katvediagnostiikka</span>"]:::gold
        end

        stg -->|dbt run| silv
        stg -->|dbt run| silv_diag
        silv -->|dbt run| gold_f
        silv -->|dbt run| gold_d
        silv_diag -->|dbt run| gold_iot
    end

    %% Raportointi ja Analyysi
    subgraph Analytics["Loppukäyttö ja analytiikka"]
        BI["<span style='color:#000 !important'>Power BI / analytiikkatyökalut<br>Parquet-tiedostojen luku</span>"]:::bi
    end

    CSV -.->|ingestio / lataus| stg
    gold_f -->|Export Parquet| BI
    gold_d -->|Export Parquet| BI
    gold_iot -->|Export Parquet| BI
```

## Arkkitehtuurin vaiheet:
1. **Lähdejärjestelmät:** Ostoskärryt tuottavat reaaliaikaista (viiveellä siirrettävää) lokaatiodataa csv-muodossa. Z-koordinaatti on rajattu heti alussa pois keveyden vuoksi.
2. **Bronze (raakadata):** `bronze_csv_data` -malli ottaa datan vastaan muuttumattomana. Tässä vaiheessa tiedot validoidaan teknisesti (tietotyypit).
3. **Silver (puhdistettu ja rikastettu):** Datan prosessointi haarautuu kahteen erilliseen putkeen:
   - **Kaupan alan analytiikka:** `silver_positions` putsaa datapisteet tiukasti rajojen mukaisesti (esim. q > 35) ja poistaa ulkopuoliset kävelyt. Tämä jättää jälkeensä vain kliinistä aitoa ostosdataa.
   - **IoT-laitevalvonta:** `silver_device_diagnostics` säilyttää kaiken roskadatan nimenomaan virheiden profilointia varten: se tunnistaa ja liputtaa katvealueet (q<35) ja siirtymän jitterit asettamatta poistosuodatusta.
4. **Gold (liiketoimintadata):** Viedään data tasolle, jossa se vastaa suoraan liiketoiminnan kysymyksiin: 
   - **Myymäläanalytiikka:** `f_kaynti`, `f_osastokaynti`, `dim_osastot` muodostavat tähtimallin myymälän läpäisyn ja tuottojen analysointiin.
   - **Laitteistoanalytiikka:** `f_verkko_laatu` ja `f_laite_status` luovat 1x1m tarkkuuden kuumuuskarttoja katvealueista sekä päivätason laitekohtaisia virheprosentteja (esim. signaalien laatu ja hypyt).
5. **Loppukäyttö:** Tietokantataulut viedään dbt-ajojen päätteeksi automaattisesti fyysisiksi, nopeiksi ja sarakepohjaisiksi `.parquet` -tiedostoiksi (External Materialization). Tämän ansiosta analyytikot tai BI-työkalut (esim. Power BI) voivat lukea dataa täydellä teholla vapaasti (Data Contract) aiheuttamatta alkuperäisen duckdb-tietokannan lukittumista (Zero-locking architecture).

# Datan Sukupuu (Linjasto)

Tämä kaavio esittää tarkasti dbt-projektimme datamallien riippuvuudet toisistaan. Se on datainsinöörin vastine arkkitehtuurikuvalle – se ei kerro _mitä järjestelmiä käytämme_, vaan _miten data virtaa tiedostosta toiseen_ ja mitä `ref()` -viittauksia mallit käyttävät.

```mermaid
graph LR

    %% Lähdedata
    subgraph Lahteen_tuonti["Lähdedata"]
        CSV[Ostoskärryjen sensoridata<br>csv-tiedostot]
    end

    %% Bronze
    subgraph Bronze["Bronze - Raakadata"]
        bronze_csv_data{{bronze_csv_data.sql<br>Datan luku ja muodonmääritys}}
    end

    %% Silver
    subgraph Silver["Silver - Puhdistuksessa haarautuva data"]
        silver_positions{{silver_positions.sql<br>Ostosdatan tuotantotason siivous<br/>& Session_id luonti}}
        silver_device_diagnostics{{silver_device_diagnostics.sql<br>Laitediagnostiikan eristys ja liputus}}
    end

    %% Gold
    subgraph Gold["Gold - Liiketoimintamallit"]
        f_kaynti{{f_kaynti.sql<br>Fakta: Kauppareissut}}
        f_osastokaynti{{f_osastokaynti.sql<br>Fakta: Osastovierailut}}
        dim_karry{{dim_karry.sql<br>Dimensio: Kärryjen metatiedot ja elinkaari}}
        dim_osastot{{dim_osastot.sql<br>Dimensio: Osastot}}
        f_verkko_laatu{{f_verkko_laatu.sql<br>Fakta: Katvealueiden kuumuuskartta}}
        f_laite_status{{f_laite_status.sql<br>Fakta: Laitteiden virhe% ja tilastot}}
    end

    %% Riippuvuudet (dbt ref)
    CSV -->|Datan lataus| bronze_csv_data
    
    bronze_csv_data -->|ref| silver_positions
    bronze_csv_data -->|ref| silver_device_diagnostics
    
    silver_positions -->|ref| f_kaynti
    silver_positions -->|ref| dim_karry
    silver_positions -->|ref| f_osastokaynti
    
    silver_device_diagnostics -->|ref| f_verkko_laatu
    silver_device_diagnostics -->|ref| f_laite_status
```

### Linjaston (Lineage) Merkitys
Tästä dbt:n sisäisestä hierarkiasta näkee selkeästi suomalaisen data-arkkitehtuurimme ydinajatuksen:
1. **Laadunhallinnan eriyttäminen:** Koska `silver_positions` -logiikka ja `silver_device_diagnostics` -logiikka haarautuvat heti raakadatan (Bronze) jälkeen ylöspäin, pysyy myymälän ostosvirta täysin puhtaana kohinasta ja roskadatasta (katvealueet), mutta samalla IoT-laitevalvonta kykenee tutkimaan täydellisesti viottuneita verkko-ongelmia rikkomatta liiketoiminnan lukuja!
2. **Keskitetty logiikka (Single Source of Truth):** Jos esimerkiksi myymälän seiniin tehdään laajennus (x/y rajojen muutos), kynnysarvo muutetaan ainoastaan Silver-tason koodiin. Kaikki ylemmät myymälän Gold-tason mallit perivät puhtaan uuden todellisuuden täysin automaattisesti ilman että raportteja tarvitsee muokata.

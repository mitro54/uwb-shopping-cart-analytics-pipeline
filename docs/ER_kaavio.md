# Tietokantojen riippuvuudet (ER-kaavio)

Alla on kuvattu valmiin tuotantotasoisen **Gold-kerroksen** arkkitehtuuri, eli ne taulut, jotka analytiikkaputki rakentaa analysoitavaksi ja tuotantoon. 

Arkkitehtuuri on jaettu kahteen loogiseen tähtimalli-tyyppiseen (Star Schema) kokonaisuuteen: myymäläanalytiikkaan sekä laitteiston diagnostiikkaan.

```mermaid
erDiagram
    %% ULOTTUVUUDET (Dimensions / Master Data)
    DIM_KARRY {
        string node_id PK "Kärryn tunniste (MAC / sarja)"
        string snro "Generoitu sarjanumero"
        timestamp luotu "Ensimmäinen havainto"
        timestamp viim_havainto
    }

    DIM_OSASTOT {
        int osasto_id PK "Vakioitu osaston tunniste"
        string nimi "Osaston nimi"
        float alku_x
        float alku_y
        float loppu_x
        float loppu_y
    }

    %% KÄYTTÖTAPAUS 1: Myymäläanalytiikka (Retail Analytics)
    F_KAYNTI {
        string kaynti_id PK "Uniikki sessiotunniste (Session ID)"
        string node_id FK "Kärryn tunniste"
        date kaynti_paiva
        int kaynti_tunti
        int kaynti_viikonpaiva
        timestamp alku "Kauppareissun alku"
        timestamp loppu "Poistuminen"
        int kesto_sekunteina
        float matka "Kuljettu matka (m)"
        float keskinopeus "m/s"
        int pisteita "Signaalien määrä"
        float levittaytyvyys_m "Laskennallinen hajonta"
    }

    F_OSASTOKAYNTI {
        string kaynti_id FK "Mihin kauppareissuun liittyy"
        string node_id FK
        int osasto_id FK "Mihin osastoon liittyy"
        string osaston_nimi
        timestamp osasto_sisaantulo
        timestamp osasto_poistuminen
        int vietetty_aika_sekunteina
        float matka_osastolla_m
        int havainnot_osastolla
    }

    %% KÄYTTÖTAPAUS 2: Laitediagnostiikka (IoT Monitoring)
    F_LAITE_STATUS {
        string node_id PK,FK "Kärryn tunniste"
        date pvm PK "Päivämäärä"
        int total_pings "Signaalien kokonaismäärä"
        int weak_signals "Heikot signaalit (q < 35)"
        int out_of_bounds_pings "Eksymiset seinien ulkopuolelle"
        int jumps "Luonnottomien siirtymien lukumäärä"
        float avg_q "Päivän keskimääräinen laatuarvo"
        float error_rate_pct "Vikojen suhde kokonaisuuteen (Error Rate %)"
    }

    F_VERKKO_LAATU {
        int grid_x PK "1x1m ruudukon (Grid) x"
        int grid_y PK "1x1m ruudukon (Grid) y"
        int total_pings 
        float avg_quality "Ruudun keskimääräinen signaalilaatu"
        float low_quality_pct "Heikkojen signaalien osuus"
    }

    %% Relaatiot
    DIM_KARRY ||--o{ F_KAYNTI : "suorittaa (1:N)"
    F_KAYNTI ||--o{ F_OSASTOKAYNTI : "sisältää vierailuja (1:N)"
    DIM_OSASTOT ||--o{ F_OSASTOKAYNTI : "kohteena (Spatial Join)"
    
    DIM_KARRY ||--o{ F_LAITE_STATUS : "monitoroidaan päivittäin (1:N)"
```

### Taulujen kuvaus

**Perustiedot (Dimensions / Master Data):**
* **DIM_KARRY**: Laajennettu perustietotaulu laitteille (ostoskärryille). Sisältää elinkaaritiedot teknistä valvontaa varten.
* **DIM_OSASTOT**: Staattisesta esiladatusta tiedostosta (Seed) rakennettu taulu, joka määrittää kaupan fyysiset rajat ja osastojen alueet sijaintikyselyitä varten.

**Myymäläanalytiikka (Fact Tables):**
* **F_KAYNTI**: Järeä tapahtumataulu (Fact), jokainen rivi edustaa yhtä aitoa kauppareissua. Kertoo reissun avainluvut (KPI), aikaleimat ja viikonpäiväyhteenvedot.
* **F_OSASTOKAYNTI**: Yksityiskohtainen taulu jokaisen kauppareissun sisäisistä etapeista (rakentuu sijaintipohjaisella risteyslogiikalla eli Spatial Joinilla). Tämän avulla saadaan raporttinäkymällä (Dashboard) avattua yhden asiakkaan kauppareissu ja tutkittua minuutti minuutilta pysähdykset ja viipymät eri osastoilla.

**Laiteanalytiikka (IoT Diagnostics):**
* **F_LAITE_STATUS**: Kytkeytyy suoraan kärryihin. Päivätason luotettavuusyhteenveto jokaiselle laitteelle; varoittaa teknistä tutkijaa rikkoutuvista akuista tai hajoavista sensoreista, näyttämällä puhtaita virheprosentteja (Error Rate) päiväkohtaisesti.
* **F_VERKKO_LAATU**: Sijaintiin kiinteästi sidottu, yksittäisistä kärryistä irrallinen signaalien kuumuuskartta (Heatmap). Jakaa kaupan lattiapinta-alan yhden neliömetrin kokoisiin resoluutioruutuihin (Grid) ja laskee absoluuttisen signaalinlaadun tälle fyysiselle alueelle, jotta verkon asentajat voivat tarkistaa kyseisen sijainnin mahdolliset fyysiset esteet (esim. suuret metallihyllyt tai kylmälaitteet).

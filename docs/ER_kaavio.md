# Entity-Relationship (ER) -kaavio

Alla on kuvattu valmiin tuotantotasoisen **Gold-kerroksen** arkkitehtuuri, eli ne taulut, jotka dbt rakentaa BI-työkaluille analysoitavaksi ja tuotantoon. 

Nyt kun meillä on myös tuo `osasto.csv` mukana rakennelmassa, tietokannan relationaalinen malli näyttää loistavalta Star Schema -tyyppiseltä rakenteelta!

```mermaid
erDiagram
    DIM_KARRY {
        string node_id PK "Kärryn uniikki tunniste"
        string snro "Generoitu sarjanumero"
        timestamp luotu "Ensimmäinen havainto yleensä"
        timestamp viim_havainto
    }

    F_KAYNTI {
        string kaynti_id PK "Uniikki Session ID (full_session_id)"
        string node_id FK "Kärryn tunniste"
        date kaynti_paiva
        int kaynti_tunti
        int kaynti_viikonpaiva
        timestamp alku "Kauppareissun alku"
        timestamp loppu "Poistuminen"
        int kesto_sekunteina
        float matka "Kuljettu matka (m)"
        float keskinopeus "m/s"
        int pisteita "Signaalien lkm"
        float levittaytyvyys_m "Hajonta"
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

    OSASTOT_SEED {
        int osasto_id PK "CSV Seed ID"
        string nimi "Osaston nimi"
        float alku_x
        float alku_y
        float loppu_x
        float loppu_y
    }

    DIM_KARRY ||--o{ F_KAYNTI : "tekee"
    F_KAYNTI ||--o{ F_OSASTOKAYNTI : "sisältää vierailuja"
    OSASTOT_SEED ||--o{ F_OSASTOKAYNTI : "kohteena (Spatial Join)"
```

### Taulujen kuvaus
* **DIM_KARRY**: Dimensiotaulu laitteille (ostoskärryille).
* **OSASTOT_SEED**: Staattinen dbt Seed -taulu, jota ylläpidetään CSV-tiedostosta. Määrittää fyysiset kaupan alueet.
* **F_KAYNTI**: Järeä faktataulu. Kertoo koko kauppareissun KPI:t, aikaleimat ja yhteenvedot. Tämä on paras taulu viikonpäiväanalyyseille!
* **F_OSASTOKAYNTI**: Yksityiskohtainen faktataulu (rakentamani Spatial Join -kaavan pohjalta). Tämän avulla saadaan dashboardilla klikattua auki yksi kauppareissu ja tutkittua minuutilleen "Missä tämä asiakas vietti ne 45 minuuttia".

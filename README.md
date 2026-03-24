# ByteBuddies – UWB Shopping Cart Analytics

Projekti analysoi sisätiloissa tapahtuvan ostoskärryn liikkumista
UWB (Ultra-Wideband) -paikannusdatan avulla. Tuloksena syntyy
visualisaatioita asiakasvirroista, kuumista alueista, nopeuksista
ja ruuhka-ajoista.

---

## Pikaopas

### 1. Kloonaa repositorio ja synkkaa kirjastot

```bash
git clone https://gitlab.com/<org>/bytebuddies.git
cd bytebuddies
uv sync
```

(Optional) Mikäli tarvii asentaa uv:
```
curl -Ls https://astral.sh/uv/install.sh | sh
```

### 2. (Jos edes tarvitaan) Täytä ympäristömuuttujat
cp .env.example .env
- Avaa .env ja täytä xxx

## Projektirakenne

bytebuddies/
│
├── .gitignore                          # Määrittelee tiedostot, joita EI viedä Gitlabiin (esim. isot CSV:t, salasanat, .venv)
├── .env.example                        # Esimerkki ympäristömuuttujista (esim. tietokannan osoite ja tunnukset)
├── docker-compose.yml                  # Docker pystytys ohjeet
├── Makefile                            # (Optional) Pikakomennot
├── README.md                           # Projektin pikaohje (miten kloonata, asentaa uv:lla ja ajaa)
│
├── pyproject.toml                      # uv:n hallinnoima tiedosto: projektin metatiedot ja riippuvuudet
├── uv.lock                             # Lukitsee pakettien versiot, jotta koko tiimillä on sama ympäristö
├── mkdocs.yml                          # Dokumentaatio! MkDocs-sivuston konfiguraatiotiedosto (navigaatio, teema, asetukset)
│
├── docs/                               # MkDocs-dokumentaatio ja Scrum-artefaktit
│   ├── index.md                        # Dokumentaation etusivu (MkDocsin oletussivu)
│   ├── projektisuunnitelma.md          # Projektisuunnitelma ja Scrum-käsikirja
│   ├── komennot.md                     # (Optional) Mahdollisten scription komennot
│   ├── arkkitehtuuri.md                # Kuvaus siitä, miten data liikkuu (ETL-putken rakenne)
│   ├── pohjakuvat/                     # Kaupan alkuperäiset UWB-pohjakuvat (esim. .png tai .svg)
│   └── sprint_log/                     # (Optional) Tänne voi kerätä sprinttien retromuistiinpanot
│       ├── sprint_01_retro.md
│       └── sprint_02_retro.md
│
├── data/                               # Paikallinen datakansio (HUOM: Tätä kansiota ei viedä Gitiin kokonaan!)
│   ├── raw/                            # Alkuperäiset suuret UWB CSV-tiedostot (Projekti-tiimi tuo tänne omat raaka-datat)
│   ├── processed/                      # Putsatut ja muokatut väliaikaiset datatiedostot
│   └── sample_data.csv                 # Pieni (esim. 100 rivin) näytedata testausta varten
│
├── dbt/                                # dbt-projekti DuckDB:lle/MariaDB:lle
│   ├── dbt_project.yml                 # dbt-projektin asetukset
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_carts.sql
│   │   │   ├── stg_positions.sql
│   │   │   └── stg_sessions.sql
│   │   ├── marts/                      # Avain informaatio asiakkaalle (Voidaan visualisoida)
│   │   │   ├── f_cart_paths.sql
│   │   │   ├── f_cart_speeds.sql
│   │   │   └── f_time_buckets.sql
│   │   └── schema.yml                  # testit + dokumentit malleille
│   ├── seeds/
│   │   └── zones.csv                   # esim. vyöhykemäärittelyt (manuaaliset)
│   ├── macros/
│   │   └── time_bucketing.sql
│   ├── snapshots/
│   └── analyses/
│
├── database/                           # Tietokantaan liittyvät skriptit
│   └── init_db.sql                     # SQL-skripti, joka luo taulut (carts, locations, zones) Dockerin käynnistyessä
│
├── src/                                # Varsinainen lähdekoodi
│   │
│   ├── etl/                            # Datan siirto ja putsaus (Extract, Transform, Load)
│   │   ├── extract.py                  # Skripti CSV-tiedostojen lukemiseen
│   │   ├── transform.py                # Datan putsaus (esim. virheellisten koordinaattien poisto, aikaleimat)
│   │   └── load.py                     # Datan siirto tietokantaan
│   │
│   ├── analysis/                       # Analyysit ja liiketoimintalogiikka
│   │   ├── heatmap.py                  # Kuumien alueiden laskenta
│   │   ├── speed_calc.py               # Ostoskärryjen nopeuksien ja läpimenoaikojen laskenta
│   │   └── time_analysis.py            # Ruuhka-aikojen ja käytön jakautumisen analysointi
│   │
│   └── visualization/                  # Kuvaajien ja näkymien luonti
│       ├── plot_heatmap.py             # Generoi lämpökarttakuvan kaupan pohjakuvan päälle
│       └── plot_charts.py              # Generoi tilastolliset pylväs- ja viivadiagrammit
│
└── notebooks/                          # Jupyter Notebookit (Vapaamuotoisempaan datan tutkiskeluun)
    ├── 01_01_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Toni)
    ├── 01_02_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Joni)
    ├── 01_03_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Mitro)
    ├── 01_04_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Panu)
    └── 01_05_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Tuija)



## Teknologiat ja perustelut

| Työkalu / kirjasto | Käyttö projektissa | Miksi valittiin |
|---|---|---|
| Python | Projektin yleinen ohjelmointikieli | Sopii hyvin datankäsittelyyn, visualisointiin ja automaatioon |
| uv | Riippuvuuksien ja virtuaaliympäristön hallinta | Nopea ja yksinkertainen tapa pitää tiimillä yhtenäinen ympäristö |
| DuckDB | Paikallinen analytiikkatietokanta | Kevyt, nopea ja toimii hyvin suoraan CSV-datan kanssa |
| dbt-core | Datan transformointi SQL-malleilla | Mallien hallinta, testaus, dokumentointi ja riippuvuuksien ohjaus |
| dbt-duckdb | dbt-adapteri DuckDB:lle | Mahdollistaa dbt-putken ajamisen suoraan DuckDB:tä vasten |
| pandas / polars | Mahdollinen esikäsittely ja datan tutkiminen | Kätevä raakadatassa havaittuihin tarkistuksiin ja kokeiluihin |
| matplotlib / plotly | Visualisoinnit | Soveltuu lämpökarttoihin, aikasarjoihin ja käyttöjakaumiin |
| MkDocs + Material for MkDocs | Projektidokumentaatio | Markdown-pohjainen, helppo julkaista GitLab Pagesiin |
| Jupyter Notebook | Tutkiva analyysi ja prototypointi | Hyvä datan alustavaan tarkasteluun ja visualisointikokeiluihin |

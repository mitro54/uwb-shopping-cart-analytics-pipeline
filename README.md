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

#### 1.1 uv asennus
(Optional) Mikäli tarvii asentaa uv:
```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

#### 1.2 Jupyter lab kehitys ympäristön käynnistys

```bash
uv run jupyter lab
```

#### 1.3 Mkdocs käynnistys

```bash
uv run mkdocs serve
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
├── gitlab-ci.yml                       # Testiputki 
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
├── bytebuddies_dbt/                    # dbt-projekti DuckDB:lle  
│   ├── dbt_project.yml                 # dbt-projektin asetukset  
│   ├── models/  
│   │   ├── bronze/  
│   │   ├── silver/  
│   │   └── gold/                       # Avain informaatio asiakkaalle  
│   ├── seeds/  
│   │   └── zones.csv                   # esim. vyöhykemäärittelyt (manuaaliset)  
│   ├── macros/  
│   │   └── time_bucketing.sql  
│   ├── snapshots/  
│   └── analyses/  
│  
└── notebooks/                          # Jupyter Notebookit (Vapaamuotoisempaan datan tutkiskeluun)  
    ├── 01_01_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Toni)  
    ├── 01_02_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Joni)  
    ├── 01_03_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Mitro)  
    ├── 01_04_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Panu)  
    └── 01_05_data_exploration.ipynb       # Datan alkuvaiheen tutkiminen (Tuija)  


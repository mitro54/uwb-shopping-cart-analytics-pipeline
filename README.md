# ByteBuddies – UWB Shopping Cart Analytics

Projekti analysoi sisätiloissa tapahtuvan ostoskärryn liikkumista UWB (Ultra-Wideband) -paikannusdatan avulla. Tuloksella pyritään ymmärtämään asiakasvirtoja, paikannusdatan eheyttä ja kauppaympäristön käyttöä.

## Tavoitteet ja ongelmanasettelu

Projektin tavoitteena on hyödyntää UWB-paikannustekniikkaa tarjoamaan syvällistä tietoa kauppaympäristön asiakasvirroista. Keskeisiä haasteita, joita projekti pyrkii ratkaisemaan, ovat:

*   **Asiakasvirtojen seuranta:** Miten asiakkaat liikkuvat eri osastojen välillä ja mitkä alueet ovat suosituimpia?
*   **Paikannusdatan eheys:** Paikannuksen palveluntarjoaja haluaa tietää paikannusdatan eheyden.
*   **Datan laadun hallinta:** UWB-datan muuntaminen raakadatasta (Bronze) puhdistetuksi ja analyysivalmiiksi (Gold) kerrokseksi.
*   **Automaatio:** Analyysiprosessien automatisointi agenttipohjaisen järjestelmän avulla, vähentää manuaalista työtä ja virhealttiutta.
*   **Visualisointi:** Monimutkaisen spatiaalisen datan muuntaminen helposti tulkittaviksi heatmap- ja virtavisualisoinneiksi.

## Miten projekti toimii?

Projekti koostuu kolmesta päävaiheesta:

1.  **Datan prosessointi (dbt & DuckDB):** UWB-paikannusdata kerätään ja prosessoidaan Medallion-arkkitehtuurin mukaisesti (Bronze -> Silver -> Gold). Tässä vaiheessa raakadatasta puhdistetaan virheet ja siitä luodaan analyysivalmiit aggregaatit.
2.  **Agenttipohjainen analyysi:** Projektissa käytetään agentteja (Python-pohjaisia), jotka suorittavat monimutkaisia tehtäviä automaattisesti. Agentit voivat esimerkiksi laskea tilastoja, suorittaa klusterointia (kuten K-means) tai valmistella visualisointeja.
3.  **Visualisointi:** Lopputuloksena on useita visualisointeja, kuten PowerBI, Jupyter Notebookit ja Streamlit-dashboard, jotka näyttävät heatmap-kuvia, asiakasvirtoja ja muita asiakkaalle tärkeitä mittareita.

## Datan prosessointi (Medallion-arkkitehtuuri)

Projekti hyödyntää dbt-työkalua ja DuckDB-tietokantaa datan prosessointiin käyttäen niin kutsuttua Medallion-arkkitehtuuria, joka jakaa datan kolmeen kerrokseen:

*   **Bronze (Raakadata):** Sisältää alkuperäisen, muuttamattoman UWB-paikannusdatan sellaisena kuin se on kerätty.
*   **Silver (Puhdistettu data):** Tässä kerroksessa raakadata puhdistetaan, virheet korjataan ja data rikastetaan (esim. koordinaattien käsittely). Data on jo helpommin analysoitavissa olevassa muodossa.
*   **Gold (Analyysivalmis data):** Tässä kerroksessa data on aggregoitu ja muokattu vastaamaan liiketoiminnan tarpeita. Täältä löytyvät esimerkiksi valmiit taulukot asiakasvirroista, osastokohtaisista analyyseista ja heatmap-visualisointeja varten.

## Analyysit ja Agentit

Projektin ytimessä on Python-pohjainen agenttijärjestelmä, joka automatisoi datan analysointia ja visualisointia.

*   **Agentit (`agents/`):** Automaattiset agentit suorittavat tehtäviä, kuten datan klusterointia (esim. K-means algoritmi), tilastollisia laskentoja ja visualisointien valmistelua. Agentit on jaettu toiminnallisiin osiin (kuten `analytics` ja `plotter`), mikä tekee järjestelmästä modulaarisen.
*   **Jupyter Notebookit (`notebooks/`):** Notebookit toimivat sekä kehitysympäristönä että dokumentaation osana. Niitä käytetään alkeelliseen datan tutkintaan (Exploratory Data Analysis - EDA), kokeelliseen analyysiin ja uusien analyysimenetelmien testaamiseen.

## Arkkitehtuurin periaatteet

Projektin kehitystä ja datan prosessointia ohjaavat seuraavat periaatteet:

*   **Modulaarisuus:** Agentit ja dbt-mallit on suunniteltu itsenäisiksi yksiköiksi, mikä helpottaa laajentamista ja ylläpitoa.
*   **Medallion-arkkitehtuuri:** Datan prosessointi noudattaa selkeää kerrosmallia, joka varmistaa datan laadun ja luotettavuuden.
*   **Automatisointi:** Pyrkimys minimoida manuaaliset työvaiheet käyttämällä agentteja ja CI/CD-automaatiota.
*   **Dokumentointi:** Kaikki tärkeät arkkitehtuuripäätökset (ADR) ja prosessit on dokumentoitu selkeästi.

## Käytetyt Teknologiat

*   **Python:** Projektin pääohjelmointikieli.
*   **dbt (data build tool):** Datan transformointi ja mallintaminen SQL-pohjaisesti.
*   **DuckDB:** In-process SQL-tietokanta tehokasta analyysiä varten.
*   **uv:** Moderni ja nopea Python-pakettien hallinta ja ympäristön hallinta.
*   **MkDocs:** Projektin dokumentaation ylläpito ja julkaisu.
*   **Jupyter Lab:** Interaktiivinen ympäristö datan analysointiin.
*   **Streamlit:** Dashboard-käyttöliittymän rakentamiseen.

---

## Pikaopas

### 1. Kloonaa repositorio ja synkkaa kirjastot

```bash
git clone git@gitlab.dclabra.fi:ttm25sai/projekti1/bytebuddies.git
cd bytebuddies
uv sync
```

#### 1.1 uv asennus
(Optional) Mikäli tarvitsee asentaa uv:
```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

#### 1.2 Jupyter lab kehitysympäristön käynnistys

```bash
uv run jupyter lab
```

#### 1.3 MkDocs käynnistys

```bash
uv run mkdocs serve
```

#### 1.4 Streamlit Dashboardin käynnistys

```bash
uv run python main.py
```

### 2. Täytä ympäristömuuttujat
```bash
cp .env.example .env
```
- Avaa `.env` ja täytä tarvittavat tiedot (esim. tietokantayhteydet).

## Projektirakenne

bytebuddies/  
│  
├── .gitignore                          # Määrittelee tiedostot, joita EI viedä Gitlabiin  
├── .gitlab-ci.yml                      # CI/CD-automaatio  
├── .python-version                     # Projektin Python-versio  
├── app.py                              # Streamlit Dashboard -käyttöliittymä
├── get_coordinates.py                  # Koordinaattien haku/käsittely  
├── main.py                             # Projektin pääskripti  
├── pyproject.toml                      # uv:n hallinnoima tiedosto: projektin metatiedot ja riippuvuudet  
├── README.md                           # Projektin pikaohje  
├── style.css                           # Tyylitiedosto  
├── uv.lock                             # Lukitsee pakettien versiot  
├── mkdocs.yml                          # MkDocs-konfiguraatio  
│  
├── agents/                             # Agenttien logiikka ja toiminta  
├── bytebuddies_dbt/                    # dbt-projekti DuckDB:lle  
│   ├── dbt_project.yml                 # dbt-projektin asetukset  
│   ├── models/                         # dbt-mallit (bronze, silver, gold)  
│   ├── seeds/                          # Alustavat tiedot (esim. osastot.csv)  
│   └── macros/                         # dbt-makrot  
├── data/                               # Paikallinen datakansio  
│   ├── processed/                      # Puhdistetut ja muokatut tiedostot  
│   └── ...                             # (Esim. raw data)  
├── docs/                               # MkDocs-dokumentaatio  
│   ├── ADR-dokumentaatio.md            # Arkkitehtuuripäätökset (ADR)  
│   ├── agentti_arkkitehtuuri.md        # Agenttien arkkitehtuuri  
│   ├── data_analyyseja.md              # Tehdyt analyysit  
│   ├── dbt-ohje.md                     # dbt-käyttöohjeet  
│   ├── index.md                        # Dokumentaation etusivu  
│   └── ...                             # (Muuta dokumentaatiota)  
├── image/                              # Projektin kuvat ja grafiikat  
├── notebooks/                          # Jupyter Notebookit (Datan tutkiminen ja analyysi)  
│   ├── 01_01_data_exploration.ipynb    
│   ├── 01_02_data_exploration.ipynb    
│   ├── 01_03_data_exploration.ipynb    
│   ├── 01_04_data_exploration.ipynb    
│   ├── 01_05_diagnostics_analysis.ipynb
│   ├── 01_06_gold_data_generation.ipynb
│   ├── 02_01_plot_zones.ipynb          
│   └── 02_02_plot_zones_from_csv.ipynb 
└── scripts/                            # Apuskriptit ja automaatio

## Tulevaisuuden kehityssuunnat

Projektin kehitys jatkuu useissa eri vaiheissa:

*   **Dashboardin laajentaminen:** Streamlit-dashboardin ominaisuuksien ja visualisointityyppien lisääminen.
*   **Agenttien laajentaminen:** Uusien analytiikka- ja automaatioagenttien lisääminen monimutkaisempiin tehtäviin.
*   **Integraatiot:** Mahdollisuus yhdistää data muihin lähteisiin ja automatisoida raportointisyklejä.

## Yhteistyö ja osallistuminen

Projektin kehitys perustuu ketterään (Scrum) menetelmään.

*   **Kehitystyö:** Projektissa käytetään GitLabia versionhallintaan ja CI/CD-automaatioon.
*   **Dokumentointi:** Kaikki keskeiset arkkitehtuuripäätökset (ADR) ja prosessit on dokumentoitu MkDocs-sivustolle (`/docs`).
*   **Kommunikaatio:** Projektin etenemisestä ja tehtävistä sovitaan säännöllisissä sprint-suunnitteluissa ja viikkopalavereissa.

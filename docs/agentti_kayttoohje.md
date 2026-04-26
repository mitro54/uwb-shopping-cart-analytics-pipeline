# ByteBuddies käyttöliittymän käyttöohje
Tätä järjestelmää voidaan ajaa sekä terminaalissa että Streamlit-sovelluksena

1) Terminaalissa komennolla:
```bash
uv run python -m agents.main [KOMENTO] [ARGUMENTIT]

# Esimerkki
uv run python -m agents.main ask "Mitä osastoja kaupassa on ja millä osastolla asiakkaat viettävät keskimäärin pisimpään aikaa?"
```
tai

2) Streamlit-sovelluksena komennolla:
```bash
uv run python main.py
```
Tai vaihtoehtoisesti:
```bash
uv run streamlit run app.py
```

## 1. Ajo terminaalissa

### 1.1 Tietokantarakenteen hallinta (`schema`)
Tämä komento näyttää agentin ymmärtämän kuvan tietokannasta (taulut ja sarakkeet).
**Näytä nykyinen rakenne:**
```bash
uv run python -m agents.main schema
```
**Päivitä rakenne (jos tietokanta on muuttunut):**
```bash
uv run python -m agents.main schema --refresh
```
### 1.2 Kertaluonteiset kysymykset (`ask`)
Käytä tätä, kun haluat nopean vastauksen tiettyyn kysymykseen. Orkestraattori koordinoi vastauksen.
**Esimerkki:**
```bash
uv run python -m agents.main ask "Mikä on ollut keskimääräinen kauppakäynnin kesto (f_kaynti) tällä viikolla?"
```
**Käytä säiettä (muistaa aiemman keskustelun tässä säikeessä):**
```bash
uv run python -m agents.main ask "Piirrä niistä graafi" --thread "liikenne_analyysi"
```

### 1.3 Interaktiivinen keskustelu (`chat`)
Käynnistää jatkuvan keskustelun agentin kanssa. Tämä on paras tapa tehdä syvällistä tutkimusta.
**Käynnistä chat:**
```bash
uv run python -m agents.main chat
```
**Lopettaminen:** Kirjoita `quit`, `exit` tai `q`.

### 1.4 Agenttien muistin hallinta (`memory`)
Tarkastele, kuinka paljon agentti on kerännyt palautetta ja oppinut.
**Näytä tilastot:**
```bash
uv run python -m agents.main memory stats
```
*(Näyttää hyvien/huonojen palautteiden määrän ja tallennetut vuorovaikutukset.)*
## Palautteen antaminen (Feedback Loop)
Aina kun käytät `ask`- tai `chat`-komentoja, järjestelmä kysyy vastauksen jälkeen palautetta:
```text
Feedback [g=good / b=bad / Enter=skip]:
```
- **g (Good):** Tallentaa vastauksen onnistuneena esimerkkinä. Agentti yrittää matkia tätä tyyliä jatkossa.
- **b (Bad):** Tallentaa vastauksen varoituksena. Agentti yrittää välttää vastaavia virheitä jatkossa.
- **Enter (Skip):** Ei tallenna palautetta.

### Vinkkejä
1. **Ole tarkka:** Jos haluat visualisoinnin, sano se suoraan: *"Piirrä heatmap..."*
2. **Säikeet:** Käytä `--thread`-argumenttia, jos haluat palata samaan aiheeseen myöhemmin (esim. `--thread "sprint_1_analyysi"`).
3. **Kieli:** Agentti vastaa suomeksi, mutta ymmärtää myös englantia.

## 2. Ajo Streamlit-sovelluksena

Streamlit-sovelluksessa on graafinen käyttöliittymä, jossa voit keskustella agentin kanssa ja tarkastella sen muistia.

Agenttien ajo vaatii Ollama-palvelimen käynnistämisen taustalla, joitakin malleja (testattu qwen malleilla).  
Varajärjestelmänä toimii Google GenAI, jos Ollama ei ole käytettävissä. Tällöin tarvitaan Google GenAI API-avain, joka täytyy lisätä `.env.example` tiedostoon, jonka jälkeen tiedosto täytyy nimetä `.env` tiedostoksi. Tämän jälkeen voit käynnistää sovelluksen komennolla:
```bash
uv run python main.py
```
Tai vaihtoehtoisesti:
```bash
uv run streamlit run app.py
```


### 2.1 Navigointi ja sivun valinta

Sovelluksen vasemmassa sivupalkissa on navigointivalikko, josta voit vaihtaa eri näkymien välillä:
- **📈 Liiketoiminta Dashboard:** Valmiit KPI-mittarit ja trendit.
- **💬 Agenttichat:** Älykäs analyysi ja visualisoinnit luonnollisella kielellä.
- **📊 Tietokantakyselyt:** Rajapinta suoriin SQL-hakuihin.
- **🗺️ Myymäläanalytiikka:** Spatiaalinen analyysi (lämpökartat, reitit).
- **🛠️ Advanced Features:** Ylläpito- ja konfiguraatiotyökalut.
- **🖼️ Generoidut kuvaajat:** Galleriat aiemmin luoduista visualisoinneista.

Sivupalkissa sijaitsevat myös agenttien mallivalinnat (🤖 LLM-mallit).

### 2.2 API-avaimen lisäys

Jos haluat käyttää Google Gemini pilvipalvelua, sinun täytyy lisätä Google GenAI API-avain `.env.example` tiedostoon, jonka jälkeen tiedosto täytyy nimetä `.env` tiedostoksi.

### 2.3 Agenttichat

Agenttichat-osiossa voit keskustella agenttien kanssa ja kysyä kysymyksiä dataan liittyen. Voit myös antaa palautetta agenttien vastauksista painamalla "Hyvä" tai "Huono" painiketta. Voit myös antaa palautetta antamalla tyhjän viestin ja painamalla "Lähetä" painiketta. Nämä tallentuvat agentin muistiin ja auttavat sitä parantamaan vastauksiaan tulevaisuudessa.

### 2.4 Datatutkimus

Tässä osiossa voit selata tietokannan tauluja ja niiden sisältöä. Lisäksi voit suorittaa SQL-kyselyitä ja tarkastella tuloksia taulukkona.

### 2.5 Visualisoinnit

Tässä osiossa voit tarkastella agenttien luomia visualisointeja.

### 2.6 Dashboardit

Sovellus sisältää kaksi eri käyttötarkoituksiin optimoitua dashboardia:

1.  **📈 Liiketoiminta Dashboard (`app.py` -> Liiketoiminta):**
    - Tarkoitettu kauppiaalle ja liiketoiminnan johdolle.
    - Mittarit: Käyntimäärät, keskiviipymät, osastojen suosio ja asiakassegmentointi (esim. pikakäynnit).
    - Suodatus: Aika, viikonpäivä ja erikoistapahtumat.

2.  **🌙 Technical Explorer (`notebooks/overnight_explorer/overnight_explorer.py`):**
    - Tarkoitettu paikannusyritykselle tekniseen laadunvarmistukseen.
    - Ominaisuudet: Paikannustarkkuuden analyysi (RMSE, CEP95), jitter- ja drift-seuranta sekä yöaikainen diagnostiikka.
    - Käynnistys: `uv run streamlit run notebooks/overnight_explorer/overnight_explorer.py`

### 2.7 Advanced Features (Ylläpito)

Tämä osio on tarkoitettu järjestelmän pääkäyttäjille ja sisältää kolme keskeistä työkalua:
- **🤖 LLM & API Konfiguraatio:** Kielimallien ja API-osoitteiden dynaaminen hallinta.
- **📅 Erikoistapahtumat:** Mahdollisuus lisätä ja muokata myyntisesonkeja tai juhlapyhiä suoraan UI:sta.
- **🗺️ Osastojen määrittely:** Interaktiivinen työkalu, jolla voit määritellä uusia osastoalueita myymälän pohjakuvaan klikkaamalla tai koordinaateilla.

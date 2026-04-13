# Asiakaskäyttäytymisen Analyysi ja K-Means DuckDB -arkkitehtuurissa

Tämä dokumentti kuvaa, miten Jupyter Notebookissa kehitetty koneoppimislogiikka (K-Means) ja edistynyt visuaalinen analytiikka (Sesonkivertailut, Lämpökartat ja Valtaväylät) sovitetaan uuteen dbt/DuckDB -tietovarastoarkkitehtuuriin.

## DuckDB ja K-Means: Toimisiko algoritmi suoraan Gold-taulusta?

**Kysymys:** *Jos sama K-means -logiikka ajetaan Gold-taulusta (`f_kaynti`) saatuun dataan, toimisiko se suoriltaan eli ilman muutoksia?*

**Vastaus:** Logiikka toimii loistavasti, mutta koodia pitää hieman muuttaa, sillä **Gold-taulu tekee asioista huomattavasti helpompaa**.

Nykyisessä Jupyter-koodissa tehdään vaihe `1. Lasketaan reittien rikastetut ominaisuudet (Feature Engineering)...` suoraan raa'asta Pandas-datasta. Lasketaan siellä itse asioinnin keston (`kesto_min`), kuljettu matka (`matka_m`), laajuus (`reitin_laajuus_m2`) ja keskinopeus (`keskinopeus_m_min`).

Koska ollaan nyt rakennettu dbt:llä Gold-tason `f_kaynti` -faktataulu, tietokanta on **jo laskenut** nämä arvot valmiiksi. Ei siis enää tehdä esilaskentaa Pandasilla, vaan hypätään suoraan koneoppimiseen. 

### Mitä koodissa tulee muuttaa?

1. Haet `f_kaynti` -taulun suoraan DuckDB:stä DataFrameksi.
2. Muutat koneoppimiseen syötettävien muuttujien (`ml_features`) nimet vastaamaan Gold-taulun sarakkeita.
3. K-Means (vaihe 2) ja visualisointi (vaihe 3) pysyvät lähes täysin koskemattomina.

**Esimerkki siitä, miltä uusi, suoraviivaisempi koodi näyttäisi Gold-dataa käytettäessä:**

```python
# 1. Haetaan valmis, jo aggregoitu data suoraan DuckDB Gold-taulusta
import duckdb
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

df_gold = duckdb.sql("SELECT * FROM f_kaynti").df()

# 2. Valitaan sarakkeet koneoppimista varten (käytetään Gold-taulun nimiä!)
# HUOM: Varmista, että tarvittavat sarakkeet löytyvät taulusta (ks. huomio alla)
ml_features = ['kesto_sekunteina', 'matka', 'levittaytyvyys_m', 'keskinopeus']
X = df_gold[ml_features].copy()

# KORJAUS OUTLIER-ONGELMAAN: Logaritminen muunnos
for col in ml_features:
    X[col] = np.log1p(X[col])

# Standardoidaan data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Etsitään 2 klusteria
kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
df_gold['klusteri'] = kmeans.fit_predict(X_scaled)

# Tunnistetaan kuka on kuka (lyhyt kesto = läpikävelijä)
lapikavelija_idx = df_gold.groupby('klusteri')['kesto_sekunteina'].mean().idxmin()
df_gold['asiakasprofiili'] = df_gold['klusteri'].apply(
    lambda x: 'Läpikävelijä' if x == lapikavelija_idx else 'Tutkiskelija'
)
```

---

## ⚠️ Kriittinen huomio: Puuttuvat Pysähdys- ja Jonotusmuuttujat (Dwell Time)

Yllä oleva suoraviivaistus paljastaa arkkitehtuurisen siirtymän ydinhaasteen. Nykyisessä Pandas-koodissa lasketaan K-Means-mallia ja sesonkianalyysiä varten erittäin tärkeitä mittareita, jotka pohjautuvat `PYSÄHDYS_RAJA_M = 0.15` -vakioon:
1. **`viipymaaika_sek`**: Kokonaisaika paikallaan.
2. **`pysahdykset_kpl`**: Yli 15 sekunnin keskeytyksettömät jaksot paikallaan.
3. **`jonotus_sek`**: Kassa-alueelle saapumisen paikallaanoloaika (viimeiset 120 datapistettä/sekuntia).

**Miten nämä käsitellään DuckDB/dbt -mallissa?**

Jos haluat pitää K-Means-mallisi yhtä tarkkana kuin ennenkin (käyttäen pysähdyksiä klusteroinnin perusteena), näitä *ei* tulisi enää laskea Pandasissa `df_cleaned` -datasta (koska Gold-arkkitehtuurissa loppukäyttäjällä ei pitäisi olla tarvetta koskea Silver-tason miljoonien rivien event-logiin Pandasilla).

**Ratkaisu:** Näiden ominaisuuksien laskenta viedään dbt-mallinnukseen SQL:llä:
* **Viipymä ja Pysähdykset:** Siirretään `f_kaynti` -taulun CTE-vaiheeseen. SQL:ssä voidaan käyttää Window-funktioita tunnistamaan "stop blockit" (vastaavasti kuin Pandasissa teit `.shift().cumsum()`).
* **Kassajonotus:** Lisätään uusi mittari Gold-tauluun, jossa eristetään esimerkiksi ikkunafunktiolla (`ROW_NUMBER() OVER(PARTITION BY session_id ORDER BY aika DESC) <= 120`) reissun häntä ja summataan sen paikallaanoloaika.

Kun nämä on koodattu dbt-puolelle kertaalleen, `df_gold` -kysely palauttaa *kaikki* K-Meansin ja sesonkianalyysin tarvitsemat sarakkeet suoraan yhdessä taulussa sekunnin murto-osassa.

---

## Miten visuaalinen analytiikka (Valtaväylät ja Lämpökartat) istuu uuteen malliin?

1. **Jakaumat ja Lämpökartat (Volyymi & Nopeus):**
   * Koska `f_kaynti` -faktataulussa on valmiiksi sarakkeet `kaynti_tunti` ja `kaynti_viikonpaiva` sekä esilasketut kestot ja keskinopeudet, Pandasin pivot-taulujen teko (kuten koodissasi: `volume_pivot = df_features.pivot_table(...)`) nopeutuu valtavasti. Aikamuunnoksia tai `.groupby` -hakuja raakadatasta ei enää tarvita. Voit jopa ajaa pivot-laskennan suoraan DuckDB:n SQL:llä ja tuoda Pythoniin vain valmiin pienen ruudukon piirrettäväksi.

2. **Myymälän Valtaväylät (Spatiaalinen 2D-Histogrammi):**
   * Plotlyn/Matplotlibin `hist2d` vaatii yksittäisiä X/Y-koordinaatteja.
   * Gold-tason `f_kaynti` ei sisällä yksittäisiä pisteitä, vaan aggregaatin koko reissusta.
   * **Arkkitehtuurinen ratkaisu:** Kun haluat piirtää valtaväylät profiileittain, yhdistät DuckDB:ssä K-Meansin tuottamat profiilit takaisin Silver-dataan. 
   * *Työnkulku:* K-Means antaa tiedon "Sessio 123 on Läpikävelijä". Teet DuckDB:hen nopean kyselyn: `SELECT x, y FROM silver_positions WHERE full_session_id = '123'` ja syötät tämän koodisi `axes[0].hist2d(df_lapi['x'], df_lapi['y'], ...)` -funktiolle.

3. **Sesonkianalyysi (Syyskuu vs. Joulukuu):**
   * Aikasarjavertailu on Gold-kerroksessa äärimmäisen suoraviivaista. Koodissa jaksojen määrittely maskeilla on oikea tapa, mutta dbt-arkkitehtuurissa voidaan suodattaa vertailukaudet (`kaynti_paiva` perusteella) jo suoraan SQL-kyselyssä kun haetaan dataa DuckDB:stä Pandas-muotoon, säästäen näin RAM-muistia lokaalilla koneella.
```
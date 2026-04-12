# Power BI & DuckDB (Parquet) Yhdistämisopas

Tässä projektissa analytiikan tietovarasto ("Data Warehouse") pyörii lokaalina DuckDB-moottorina (dbt-putki), joka käsittelee raskaan Bronze- ja Silver-tason datan miljoonine riveineen. 

**Välttääksemme tietokantalukitukset ja resurssipulan (esim. "taulu on varattu" -virheet), Gold-tason mittaristot tulostetaan yksittäisinä "sarakepohjaisina" Parquet-tiedostoina!** Power BI kykenee märehtimään suuria määriä Parquet-tiedostoja uskomattomalla nopeudella!

Dbt valmistaa uudet Parquet-tiedostot aina hakemistoon: `bytebuddies\data\gold\`

## 1. Datan Mallinnus Power BI:ssä

Näin yhdistät Power BI:n dataan niin, että raportointi ei haittaa taustalla tapahtuvaa dbt-ajojen tiedonlatausta.

1. Avaa Power BI Desktop ja valitse **Hae tiedot (Get Data)** -> **Lisää... (More...)**.
2. Kirjoita avautuvaan hakukenttään `Parquet` ja valitse se.
3. Power BI pyytää tiedoston polkua. Hae paikalliselta tietokoneeltasi hakemistosta `data/gold/` haluamasi mittaristo, esimerkiksi:
   * `f_kaynti.parquet`
   * `f_osastokaynti.parquet`
   * `dim_karry.parquet`
   * `dim_osastot.parquet`
   * `f_verkko_laatu.parquet`
   * `f_laite_status.parquet`
4. Paina **Yhdistä (Connect)** tai **Avaa (Open)**.
5. Ruudulle aukeaa esikatselu datasta. Paina **Lataa (Load)**.

Toista tämä prosessi niille ylläolevassa listassa oleville tiedostoille, joita tarvitset dashboardillasi.

> [!IMPORTANT]  
> Power BI lataa tiedot Parquet-sarakemuodossa RAM-muistiin paljon nopeammin kuin CSV-tiedostoja tuodessa. Vaikka dataa olisi satoja miljoonia rivejä (esim. `f_verkko_laatu`), mallin päivitys on dynaamista. Aina kun ajat komentorivillä `uv run dbt run --select gold`, vanhat Parquet-tiedostot ylikirjoittuvat silmänräpäyksessä uudemmalla datalla. Painamalla Power BI:ssä vain "Päivitä (Refresh)", saat aina uusimmat tiedot.

## 2. Mallien Liittäminen (Relaatiot)

Koska dbt tulostaa nämä Gold-tason taulut irtonaisina tiedostoina, sinun on ehkä yhdistettävä ne uudelleen toisiinsa Power BI:n **Mallinäkymässä (Model view)**. Vedä vain taulujen välille viivat samoilla logiikoilla kuin projektin [ER-kaavio](ER_kaavio.md) määrittää (esim. `node_id` Dimensiosta kiinni vastaavaan ID-kenttään Faktan puolella).

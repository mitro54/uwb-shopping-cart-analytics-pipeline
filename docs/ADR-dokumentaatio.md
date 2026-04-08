# Teknologiat ja perustelut (ADR)

## Tiivistelmä

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


## Työkalut

**Python:**
Projektiin sopiva koodikieli, joka taipuu sujuvasti kaikkiin toimiin. Laajin kirjastovalikoima data-analytiikkaan; toimii saumattomasti dbt:n, DuckDB:n ja Jupyterin kanssa

**uv:**
Korvaa pip + venv yhdellä työkalulla, luo täysin toistettavan ympäristön uv.lock-tiedoston avulla. Toimii identtisesti Windowsilla, macOS:llä ja Linuxilla. Vältytään Dockerin käytöltä ainakin projektin alkupuolella vaikka tiimiläiset toimivat eri OS ympäristöissä.

**DuckDB:**
Saraketallennus ja vektorisoitu suoritus tekevät sadoista miljoonista riveistä hallittavia paikallisella koneella ilman erillistä palvelinta; lukee CSV-tiedostot suoraan `read_csv_auto` -funktiolla ilman erillistä latausta, ja sen CSV-lukija on nopeutunut lähes 3× viime versioiden aikana.

**dbt-core:**
dbt (Data Build Tool) hallinnoi SQL-mallit, niiden väliset riippuvuudet, automaattiset testit ja dokumentaation yhtenä kokonaisuutena. Mallit kirjoitetaan `.sql`-tiedostoihin ja dbt huolehtii oikeasta ajojärjestyksestä. Kaikki on versionhallinnassa ja tiimi voi tehdä muutoksia turvallisesti.

**dbt-duckdb:**
DuckDB-adapteri dbt:lle. Ilman adapteria dbt ei tiedä miten ottaa yhteyttä tietokantaan tai miten ajaa mallit sitä vasten. dbt-duckdb mahdollistaa koko putken ajamisen paikallisesti ilman pilveä tai erillistä palvelinta.

**pandas & polars:**
Pandas datan käsittelyn treenaamiseen. Sopiva työkalu aloittelijoille.

Polars on nopea DataFrame-kirjasto datankäsittelyyn. Pandas on tutumpi, mutta polars on merkittävästi nopeampi isoilla aineistoilla, koska se käyttää sarakepohjaista muistinkäsittelyä ja Rust-pohjaista toteutusta. Sopii hyvin tähän projektiin, joissa CSV-dataa tarvitsee tarkastella tai esikäsitellä ennen dbt-putken ajamista.

**matplotlib / seaborn / plotly:**
Matplotlib visualisointiin, sopii staattisiin PNG-exportteihin, Seaborn hienompiin kuvaajiin ja Plotly interaktiivisiin kuvaajiin notebookeissa

**MkDocs + Material:**
Markdown-pohjainen, ei vaadi erillistä rakennusjärjestelmää, julkaistaan automaattisesti GitLab CI/CD -pipelinella

**JupyterLab:**
Mahdollistaa nopean datantarkastelun suoraan DuckDB:stä SQL-kyselyillä ennen kuin koodi siirretään varsinaisiin Python-moduuleihin

## Tietokanta-arkkitehtuuri: Raaka-Jalostettu -malli (Kärrydata)

**Päätös:**
Jaetaan analytiikkatietokanta (DuckDB/dbt) logaaliin rakenteeseen, jossa on puhdas raakadata (`havainto`), dimensiotaulut (`osasto`, `karry`) ja jalostettu aggregointidata (`kaynti`, `osastokaynti`). Mallinnus optimoidaan puhtaasti 2D-paikannukseen (x- ja y-koordinaatit), eikä projektissa toteuteta raskasta kolmiportaista Medallion-arkkitehtuuria (Bronze/Silver/Gold).

**Tilanne ja ongelma:**
Projektissa on kyse ostoskärryjen sensoridatan (x,y-koordinaatit ja aikaleimat) analysoinnista. Tarvitsemme tietokantarakenteen, joka pystyy varastoimaan suuren määrän toistuvia koordinaattipisteitä (event log), mutta josta saadaan samalla salamannopeasti ulos liiketoimintatason analytiikkaa (esim. kauppakäyntien matkat ja osastovierailujen kestot). Vaikka projektissa käsitellään staattista koulutusaineistoa, ohjelmistoarkkitehtuurin tulee mallintaa oikeaa, jatkuvasti laajentuvaa IoT-ympäristöä ("Design for scale, implement for scope").

**Miksi valittiin:**
1. **Suorituskyvyn eriyttäminen (OLTP vs OLAP):** Raakadata (`havainto`) ottaa nopeasti vastaan valtavia määriä pisteitä ilman raskaita relaatiotarkastuksia. Jalostetut data-mallit (`kaynti`, `osastokaynti/alue_kaynti`) puolestaan tiivistävät satojatuhansia rivejä selkeiksi asiointikerroiksi. BI-kyselyt kohdistetaan vain ja ainoastaan erittäin nopeisiin jalostettuihin tauluihin.
2. **"Data Enrichment" (Esilaskenta):** Etäisyydet (`matka`) ja viipymät (`kesto`) lasketaan vain tasan kerran dbt-putkessa tai Python-skriptissä uusia `kaynti`-rivejä muodostettaessa. Niitä ei tarvitse koskaan purkaa raportointityökalujen lennosta laskettaviksi pullonkauloiksi. 
3. **Geometristen alueiden hallinta Dimensiona:** Osastot ohjataan taulussa `osasto` ns. Bounding box -menetelmällä (`alku_x`, `loppu_x` jne.). Tämä tekee tilasääntöjen muuttamisesta ja kyselyistä äärimmäisen yksinkertaisia ilman raskaita GIS/Paikkatieto-laajennuksia.
4. **Resurssien hallinta:** Arkitehtuuri eristää massiivisen koordinaattidatan tärkeästä liiketoimintahistoriasta. Raakadata-taulu voidaan teknisesti arkistoida tai tyhjentää esim. 1 vuoden välein ilman analytiikkatiedon katoamista. Lisäksi `viim_havainto` -kentillä (Kärry-taulussa) on helppo monitoroida IoT-laitteiden teknistä "elossa-oloa" eristämällä ylläpitokyselyt raakadatasta.

## Tietokanta-arkkitehtuuri: Dimensiotaulut Gold-kerroksessa (Star Schema)

**Päätös:**
Projektissa laajennettiin dbt-käyttöä täyteen Medallion -arkkitehtuuriin (Bronze -> Silver -> Gold). Tämän myötä teimme tietoisen arkkitehtuurisen linjauksen sijoittaa kaikki konformiset dimensiotaulut (kuten `dim_osastot` ja `dim_karry`) suoraan ylimpään **Gold-kerrokseen**, aivan faktataulujen (`f_kaynti` ja `f_osastokaynti`) viereen. Seedeistä ladattava data muutetaan dynaamisiksi Gold-tason `table` -materialisoiduiksi dimensioiksi.

**Tilanne ja ongelma:**
Datatiimin piti päättää pitkien dbt-putkien osalta, mihin kerrokseen perinteiset Master Data -taulut (kuten osastojen fyysiset rajat `seeds/osastot.csv` -tiedostosta) materialisoidaan. Pieniä referenssejä voidaan periaatteessa hallita "puhtaassa" Silver-tasossa heti, mutta se olisi rikkonut analytiikkatason eheyden.

**Miksi valittiin:**
1. **BI-työkalujen (Star Schema) palveleminen:** Sijoittamalla kaikki dashboardin tarvitsemat taulut (sekä Faktat että niitä selittävät Dimensiot) samaan Gold-kansioon, voimme muodostaa täydellisen ja modernin Star Schema -kokonaisuuden yhdelle tasolle. Raportointityökalun ei tarvitse koskaan "kurkkia" Silver-kerrokseen hakeakseen metatietoja osastojen nimistä.
2. **Käyttöoikeudet ja Abstraktio:** Gold-kerros on tarkoitettu vain puhtaaseen analytiikkaan ja loppukäyttäjille valmiina datamarttina. Silver-kerros on tässä projektissa ("silver_positions.sql") pyhitetty erittäin monimutkaiselle moottorilogiikalle (CTE:t, Jitter-suodatus, Geofencing ja signaalikatkojen katkaisu). Pitämällä Dimensiot Gold-tasolla faktojen vieressä pidämme loppukäyttäjän näkymän irrotettuna raskaan siivousvaiheen tietokantaprosesseista.
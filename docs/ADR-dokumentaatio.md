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
2. **"Data Enrichment" (Esilaskenta Window-funktioilla):** Etäisyydet (`dist_m`) ja viipymät (`sekuntia_edellisesta`) lasketaan vain tasan kerran dbt:n Silver-kerroksessa. Tämä toteutetaan SQL:n `LAG()` -ikkunafunktioilla (Window Functions), jotka yhdistävät edellisen havaintopisteen suoraan nykyiseen vertailua varten. Tätä tietokannalle erittäin raskasta peräkkäistä laskentaa ei tarvitse eikä saa koskaan purkaa BI-raportointityökalujen lennosta laskettavaksi pullonkaulaksi.
3. **Geometristen alueiden hallinta Dimensiona:** Osastot ohjataan taulussa `osasto` ns. Bounding box -menetelmällä (`alku_x`, `loppu_x` jne.). Tämä tekee tilasääntöjen muuttamisesta ja kyselyistä äärimmäisen yksinkertaisia ilman raskaita GIS/Paikkatieto-laajennuksia.
4. **Resurssien hallinta ja IoT-valvonta (`dim_karry`):** Arkitehtuuri eristää massiivisen koordinaattidatan tärkeästä liiketoimintahistoriasta. Koska `dim_karry` -dimensiotaulu on "esilaskenut" sisäänsä kunkin fyysisen laitteen (`node_id`) `luotu` ja `viim_havainto` -aikaleimat, voimme monitoroida ostoskärryjen sensorien teknistä elossaoloa silmänräpäyksessä. Tämä on kriittistä laitehallinnalle: esimerkiksi rikkoutuneet tai virrattomat laitteet voidaan havaita tutkimalla ainoastaan tätä sadan rivin dim-taulua, jolloin vältetään raskaiden satojen miljoonien rivien skannaus kunkin laitteen viimeisen elonmerkin löytämiseksi.

## Tietokanta-arkkitehtuuri: Dimensiotaulut Gold-kerroksessa (Star Schema)

**Päätös:**
Projektissa laajennettiin dbt-käyttöä täyteen Medallion -arkkitehtuuriin (Bronze -> Silver -> Gold). Tämän myötä teimme tietoisen arkkitehtuurisen linjauksen sijoittaa kaikki konformiset dimensiotaulut (kuten `dim_osastot` ja `dim_karry`) suoraan ylimpään **Gold-kerrokseen**, aivan faktataulujen (`f_kaynti` ja `f_osastokaynti`) viereen. Seedeistä ladattava data muutetaan dynaamisiksi Gold-tason `table` -materialisoiduiksi dimensioiksi.

**Tilanne ja ongelma:**
Datatiimin piti päättää pitkien dbt-putkien osalta, mihin kerrokseen perinteiset Master Data -taulut (kuten osastojen fyysiset rajat `seeds/osastot.csv` -tiedostosta) materialisoidaan. Pieniä referenssejä voidaan periaatteessa hallita "puhtaassa" Silver-tasossa heti, mutta se olisi rikkonut analytiikkatason eheyden.

**Miksi valittiin:**
1. **BI-työkalujen (Star Schema) palveleminen:** Sijoittamalla kaikki dashboardin tarvitsemat taulut (sekä Faktat että niitä selittävät Dimensiot) samaan Gold-kansioon, voimme muodostaa täydellisen ja modernin Star Schema -kokonaisuuden yhdelle tasolle. Raportointityökalun ei tarvitse koskaan "kurkkia" Silver-kerrokseen hakeakseen metatietoja osastojen nimistä.
2. **Käyttöoikeudet ja Abstraktio:** Gold-kerros on tarkoitettu vain puhtaaseen analytiikkaan ja loppukäyttäjille valmiina datamarttina. Silver-kerros on tässä projektissa ("silver_positions.sql") pyhitetty erittäin monimutkaiselle moottorilogiikalle (CTE:t, Jitter-suodatus, Geofencing ja signaalikatkojen katkaisu). Pitämällä Dimensiot Gold-tasolla faktojen vieressä pidämme loppukäyttäjän näkymän irrotettuna raskaan siivousvaiheen tietokantaprosesseista.

## Tietokanta-arkkitehtuuri: Silver-tason suodatuslogiikan keskittäminen

**Päätös:**
Ostoskärryjen raskaat IoT-datan perkaussäännöt (Geofencing, Jitter-suodatus, aikaikkunat ja session_id:n generointi) päätettiin rakentaa ja keskittää täysin Silver-kerroksen yhteen dbt-malliin (`silver_positions.sql`). Arvojen valinnat (esim. max hyppy 3.5 m/s, aukioloajat, Q-laatu > 35) sidottiin saumattomasti dbt:n yhtenäiseen `schema.yml` määritykseen.

**Tilanne ja ongelma:**
IoT-datan alkuperäinen puhdistus suunniteltiin alun perin Python/Jupyter-puolella havaitun analytiikan perusteella. Ongelmana dbt-putkessa oli, miten ja minne nämä lukuisat kriittiset fysiologiset ja lokaatiolliset säännöt (kuten virheellisten latauspisteiden poisto, aukioloaikojen filtteröinti ja ostoskärryn pitkän liikkumattomuuden liputus "uudeksi asioinniksi") tulisi koodata tietovarastossa, jotta vältytään sekavalta koodin toistolta useammissa myöhemmissä Fakta-tauluissa.

**Miksi valittiin:**
1. **Silver-logiikan eheys:** Yhdistämällä kaikki puhdistussäännöt selkeisiin, peräkkäisiin CTE-blokkeihin (Common Table Expressions) yhdellä arkkitehtuurisella tasolla, varmistetaan se, että jokainen ylempi Gold-taulu (`f_kaynti`, `f_osastokaynti`) kykenee luottamaan raa'an asiointidatan laatuun 100-prosenttisesti. Jos esimerkiksi Jitter-sääntöä halutaan löysentää (3.5 -> 5.0 m/s), muutos tehdään vain yhteen Silver-malliin, ja se valuu kaikkialle alaspäin.
2. **Kynnysarvojen automattinen valvonta (Schema-Määräävyys):** Arvojen ylläpito on siirretty tietokannan SQL-koodin lisäksi dbt:n YAML-testeihin (`schema.yml`). Näin tietokanta-arkkitehtuuri ei ainoastaan suodata tuotantoarvoja, vaan myös automaattisesti testaa niiden läpäisyä suhteessa asetettuihin rajoihin, turvaten mallinnuksen inhimillisiltä muutoksilta jatkossa.

## Tietokanta-arkkitehtuuri: Kahdennettu analytiikkaputki (IoT vs Myymälä)

**Päätös:**
Bronze-tason raakadata eriytetään Silver-tasolla kahteen täysin erilliseen malliin: `silver_positions` (myymäläanalytiikkaan) ja `silver_device_diagnostics` (laitteiston toiminnan monitorointiin). Kumpikin malli palvelee eri Gold-tason faktatauluja omilla liiketoimintalogiikoillaan.

**Tilanne ja ongelma:**
IoT-laitteiston toimittaja ja myymälän liiketoimintajohto tarvitsivat analytiikkaa selkeästi ristiriitaisin intressein. Myymälä haluaa kliinistä, suodatettua ostoskäyttäytymistä, josta kaikki laitevirheet, jitterit ja signaalikatveet on suodatettu armotta pois. Paikannuslaitteiden toimittaja ("paikannusyritys") taas tarvitsee kiinni nimenomaan nämä virheellisesti käyttäytyvät laitteet ja myymälän katvealueet laitekannan laadun takaamiseksi. Viankorjaus ja myymäläanalytiikka samasta yhdestä suppilosta olisi johtanut mahdottomaan kompromissiin suodatuksen kireydessä - se mikä on myymäläanalytiikalle roskaa, on laitevalvonnalle kultaa.

**Miksi valittiin:**
1. **Datan eheyden suojaaminen käyttäjätason intressein:** Rakentamalla laitteistolle oma malli, joka ei hukkaa (suodata) heikkolaatuisia (q < 35) tai epätodellisen nopeita (m/s > 3.5) rivejä, vaan ainoastaan liputtaa ne boolean-muodolla (esim. `is_jitter`, `is_low_quality`), mahdollistamme rikkinäisen tiedon tiivistämisen Gold-tasolla. Tämän rinnalla myymälädata voi säilyä tiukasti laatusuodatettuna puhtaana ostoskäyttäytymisenä toisessa mallissaan.
2. **Kuumuuskarttatyyppinen vianetsintä (Heatmap):** Raaka diagnostiikkamalli valmistaa datan josta kääntyy helposti `f_verkko_laatu` faktataulu, joka pystytään sitomaan vapaavalintaiseen esim. 1x1 metrin fyysiseen grid-resoluutioon. Tämän vuoksi ohjaus Dashboardeilla voidaan palauttaa nopealla laskennalla tilaohjatuksi sensorivikojen löytämiseksi.

## Tekninen Arkkitehtuuri: Raportoinnin irtikytkentä (Tietokannasta Parquet-tulosteeseen)

**Päätös:**
Aiempi ratkaisu yhdistää Power BI suoraan DuckDB-tietokantatiedostoon ODBC-ajurin kautta korvattiin taltioimalla kaikki dbt:n Gold-tason (`gold/` -kansio) luomat taulut automaattisina asynkronisina `.parquet` -tiedostoina `data/gold/` -hakemistoon asettamalla default materialisaatioksi `external`. Tällöin Power BI yhdistää vain flat-tiedostoihin tietokannan sijaan.

**Tilanne ja ongelma:**
IoT-koostedatan myötä dbt-muunnoksista ja lukevissa Power BI -näkymissä käytettävistä fact-tauluista muodostui erittäin raskaita. DuckDB on äärimmäisen nopea suljettu paikallinen tiedosto, mutta "yhden tiedoston" -tietokantana samanaikaiset pitkäkestoiset massakirjoitukset (dbt run) sekä raskaat visualisointikyselyt ajurin yli (Power BI refresh) aiheuttivat säännöllisesti ns. tietokannan varauslukituksia (Table Reserved / Database Locked -virheet), jotka kaatoivat usein molemmat prosessit. 

**Miksi valittiin:**
1. **Zero-Locking -arkkitehtuuri:** Muuttamalla `dbt_project.yml` kautta kaikki Gold-tason mittaristot "external" materialisaatioiksi, DuckDB kääntää taulut salamannopeasti levylle erillisiksi tiedostoiksi. Power BI on sisäänrakennetusti erikoistunut sarakepohjaisten Parquet-tiedostojen erittäin massiiviseen lukuun. Tiedostojen lukeminen levyltä "read only" -tyyppisesti vapaasti ei aiheuta enää kilpailutilanteita (Race Condition) DuckDB:n sisäisestä tilasta dbt-ajojen putken kanssa.
2. **Data Contract -periaate:** Tietohakemistoon ilmestyvät staattiset Parquet-tiedostot muodostavat selkeän ja testatun rajapinnan (ns. Data Contract) analytiikan rakentajien ja dashboardin piirtäjien välillä. Raportoijat eivät voi enää teknisesti sorkkia dbt:n omaa varastoa tai lukita epähuomiossa keskeneräisiä malleja.
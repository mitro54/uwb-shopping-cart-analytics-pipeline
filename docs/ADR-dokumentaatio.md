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
DuckDB-adapteri dbt:lle. Ilman adapteria dbt ei tiedä miten ottaa yhteyttä tietokantaan tai miten ajaa mallit sitä vasten. dbt-duckdb mahsitavallistaa koko putken ajamisen paikallisesti ilman pilveä tai erillistä palvelinta.

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

## Tietokanta-arkkitehtuuri: Tuotantotason datan siivousasetukset ja liiketoimintasäännöt

**Päätös:**
IoT-datan virhelähteet ja myymälän operatiiviset poikkeamat (kuten hylätyt kärryt) siivotaan pois ennalta määritetyillä liiketoimintasäännöillä ja fysiologisilla rajoilla.

**Miksi valittiin:**
* **Q-arvon kynnys (`Q_THRESHOLD` / `q_threshold`):** IoT-signaaleissa (esim. UWB) on usein kohinaa, joka voi vääristää koordinaatit hetkellisesti kymmenien metrien päähän. Heikkolaatuisten pisteiden karsiminen estää "seinien läpi teleporttaamisen".
* **Aukioloaikojen rajaus (`SHOP_HOURS`):** Yöllinen liikehdintä koostuu myymälän hyllytyksestä, siivouksesta tai laitteiston kalibroinnista. Nämä rajataan pois, jotta data edustaa vain aitoja asiakasvirtoja ja asiointia.
* **Ongelmallisten alueiden poisto (`PROBLEMATIC_COORDS`):** Esimerkiksi latauspisteillä olevat ostoskärryt lähettävät dataa jatkuvasti samasta paikasta tuntikausia. Ilman näiden alueiden geofencing-poistoa viipymäaika-analyysit ja lämpökartat vääristyisivät massiivisesti.
* **Geofencing-validoinnit (`CHECKOUT_ZONE` ja `START_ZONE`):** Pakottamalla sessio alkamaan sisäänkäynniltä ja päättymään kassoille karsitaan pois laitteiden satunnaiset uudelleenkäynnistymiset keskellä kauppaa, sekä työntekijöiden kärryjen siirtelyt, jotka eivät ole aitoja ostoskierroksia.
* **Paikallaanolo-leikkuri (Säde ja aikaraja):** Asiakkaat ja henkilökunta hylkäävät toisinaan kärryjä keskelle myymälää. Leikkuri (esim. 20 min paikallaan) katkaisee reissun. Logiikka vaatii *säteen* (radius) eikä vain puhdasta nollaliikettä, koska IoT-laitteiden koordinaateissa on aina pientä huojuntaa (jitter), vaikka fyysinen laite olisi täysin paikallaan.
* **Jitter- ja fysiologiset filtterit (Matka-, nopeus- ja aikarajat):** Rajat perustuvat ihmisen liikkumiskykyyn. Kärryä ei voi työntää yli 3.5 m/s, eikä asiointi yleensä kestä alle 3 minuuttia tai kulje alle 30 metriä. Spatiaalinen hajonta (`MIN_SPATIAL_SPREAD`) vaatii, että reitti on liikkunut aidosti eri puolilla myymälää, karsien pois paikallaan hyppivät "haamureitit".


---

# 2. Asiakaskäyttäytymisen Analyysi ja Logiikan Selitykset

## Session ID: Miten data pilkotaan asioinneiksi?

IoT-ostoskärryt lähettävät koordinaattidataa taukoamatta. Laitteella ei ole painiketta, josta asiakas kertoisi aloittavansa tai lopettavansa ostokset. Siksi yhtenäinen datavirta on pilkottava yksittäisiksi kauppareissuiksi (sessioiksi) erillisen säännöstön avulla.

### Miten logiikka toimii teknisesti?
Sessioiden tunnistaminen tapahtuu etsimällä datasta "laukaisimia" (triggers), jotka tarkoittavat, että kärryn käyttäjä on loogisesti vaihtunut:
1. **Laitteen vaihtuminen:** Datarivin `node_id` on eri kuin edellisellä rivillä.
2. **Aukko ajassa (Time Gap):** Peräkkäisten datapisteiden välillä on yli 15 minuutin hiljaisuus (esim. kärry viety varastoon tai ulos alueelta).
3. **Kassa-alueelta poistuminen:** Kärry on ollut edellisessä pisteessä kassa-alueella (`CHECKOUT_ZONE`), mutta ei ole enää uudessa pisteessä. Tämä tarkoittaa, että edellinen asiakas maksoi ostoksensa ja uusi asiakas on ottanut kärryn käyttöön.

Kun jokin näistä ehdoista täyttyy, koodi merkitsee kyseiselle riville lipun: `is_new_session = 1` (muulloin arvo on 0). Tämän jälkeen datalle ajetaan **kumulatiivinen summa** (SQL:ssä `SUM(is_new_session) OVER (...)`, Pythonissa `.cumsum()`). Tämä muuttaa yksittäiset 0- ja 1-liput nousevaksi numerosarjaksi (1, 1, 1... 2, 2, 2... 3, 3, 3...). 

### Miksi tämä tehdään juuri näin?
* **Suorituskyky:** Kumulatiivinen summa on ns. vektorisoitu operaatio. Sen ajaminen kymmenille miljoonille riveille on tuhansia kertoja nopeampaa kuin datan läpikäynti rivi riviltä (for-looppaaminen).
* **MD5 Full Session ID:** Lopuksi laitteen ID ja tämä juokseva numero yhdistetään (esim. `kärryA_2`) ja niistä luodaan MD5-tiiviste. Tämä siksi, että tietokannan Gold-kerros saa tasapitkän ja uniikin pääavaimen (Primary Key), joka nopeuttaa taulujen yhdistämistä (JOIN).
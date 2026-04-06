# Scrum-dokumentaatio

## Sprint 1 – Projektin alustus ja EDA

### Suunnittelupalaveri  - 23.3.2026 klo 18.30

Löysimme Epiikan, jonka pohjalta alamme valmistelemaan projektia.

Scrumin dokumentointi siili-blogiin ja muut dokumentoinnit Gitlab pages. Sovimme ryhmän toimintatavoista, aikataulusta ja kävimme läpi mitä Scrum tapahtumissa tapahtuu. Nelipäiväinen työviikko, ma-to.

Päätimme, että ekan sprintin suurin työ on jokaiselle dataan tutustuminen Jupyter Notebookkeja käyttäen ja projektin alustus. Jokaiselle annettiin tehtäväksi tutustuminen dataan eri kantilta. Muistiinpanotlöydöksistä, joista sitten rakennetaan käyttäjätarinoita epiikan tueksi.

#### Suunnittelupalaverin tuotokset
- Sprint Goal määritelty
- Alustava Sprint Backlog muodostettu
- Työskentelykäytännöt sovittu

#### Sprintin tehtävät

-  Työkalujen käyttöönotto
-  Arviointiperusteisiin tutustuminen
-  Kehitysympäristön pystyttäminen omalle koneelle
-  Työtehtävien jako
    - tehtävien karkeustasot: epiikka, käyttäjätarina, tehtävä
- Sprintin toimenpiteistä sopiminen
    - dailyt, demo, retro
- Projektityöskentelyn aloittaminen (taskit Gitlabista)
- Projektin git-repo ja kansiorakenne
- Ensimmäinen README ja projektisuunnitelma
- EDA: datasetin kokoonpano, datalaadun tarkistus, alustavat visualisoinnit 


#### Sprint Goal
Luoda yhteinen tekninen ja toiminnallinen pohja projektin aloittamiselle sekä muodostaa ymmärrys datan rakenteesta ja laadusta.

#### Alustava Sprint Backlog
Tutustutaan dataan (notebooks, EDA)
Projektin alustus ja versionhallinta
Selkeä repo- ja hakemistorakenne

#### Sprintin Increment (toteutunut/kehittyvä)
- [x] Projektirepositorio luotu
- [x] Scrum-käytännöt sovittu
- [x] Kehitysympäristö osittain valmis
- [x] Alustava ymmärrys datasta muodostettu

#### Sprint DoD

- Repo luotu ja dokumentoitu
- Scrum-käytännöt sovittu
- Alustava data-analyysi tehty, pääpiirteiset löydökset dokumentoitu
- Tiimillä yhteinen ymmärrys datasta ja sen rajoituksista
- Ensimmäinen demo tehty

#### Sprintin backlog (Kehitystiimi)

Päivitetään suunnittelupalaverissa. Tiimi antaa ennusteen, mitä toiminnallisuutta seuraava versio sisältää. Tehtävien tuntiarviot ovat suuntaa-antavia. Sprinttien ennustettavuus perustuu tiimin kokemukseen eikä yksittäisiin tuntimääriin.

- Kehitysympäristö
    - [x] Docker kontin pystytys (Joni) 30 min [REMOVED]
    - [x] Projektin rakenne (Tomi) 5 min
    - [x] Dataformaatti (Toni) 2 h
- Data
    - [x] Miten asiakas liikkuu kaupassa (Toni) 2 h
    - [x] Datan laatu (Panu) 4 h
    - [x] Datan mahdollisuudet (Kaikki) 2 h / hlö
    - [x] Sijainnin laatu (Joni) 10 h
    - [x] Datateoriat/yhteydet (Mitro) 8 h
- Käyttäjätarinat
    - [x]  Käyttäjätarinoiden tarkentaminen datan analyysin perusteella (Kaikki)  1 h / hlö

#### Daily scrum
Sprintin aikana pidetään päivittäinen Daily Scrum. Alla kirjaukset päivien edetessä.

### Daily tiistai

- Kävimme Scrumin toimintoja vielä tarkemmin läpi, Tuija oli selvittänyt paljon ja selvensi kaikille. Ei ollut ongelmia ja Mitro oli aloittanut jo datan plottausta Jupyterissä.

**Paikalla: Mitro, Tuija, Joni ja Panu**

### Daily keskiviikko

- Tutustuttiin Jarin agenttihärveliin. Ei ongelmia.

**Paikalla: Mitro, Tuija, Panu**

### Daily torstai

- Käytiin läpi Mitron löydöksiä

**Paikalla: Mitro, Tuija, Panu, Toni**

### Sprint Review - ma 30.3.2026 klo 17.00

#### Mikä toimi hyvin

- Saatiin projekti käyntiin
- Dokumenttaatio saatu alkuun
- Datan tutkiminen on alkanut
- Tiimi on motivoitunut

#### Mikä ei toiminut

- Palavereihin osallistuminen vaihtelevaa
- Scrum on vielä vähän hakusessa
- Mikä datassa on arvokasta ja miten sitä voi hyödyntää on vielä epäselvää

#### Parannusehdotukset

- Enemmän yhteistä aikaa datan tutkimiseen
- Selkeämpi kuva siitä, mitä datasta halutaan selvittää

#### Tiimin fiilis

- Hyvä fiilis, motivoitunut tiimi
- Odotukset korkealla

#### Yhteenveto 

- Saatiin projekti käyntiin
- Dokumentointi saatu alkuun
- Datan tutkiminen on alkanut
- Tiimi on motivoitunut

**Paikalla: kaikki**

### Sprint Retro -  ma 30.3.2026  klo 18.00

- Asiakas voi puuttua asioihin ja vaikuttaa projektiin
- Issueita on sulkematta

## Sprint 2 – Dataputken suunnittelu ja Bronze-ingestion

### Suunnittelupalaveri – 30.3.2026 klo 18.30

Vahvistimme projektisuunnitelman ja valitsimme arkkitehtuuriksi Bronze-Silver-Gold medalllion mallin. Tässä sprintissä siirrymme datan tutkimisesta sen tekniseen hallintaan. Päätimme käyttää DuckDB-tietokantaa ja dbt-työkalua datan muuntamiseen. Aloitamme työskentelyn alkupäästä ja valmistellen projektia.

#### Suunnittelupalaverin tuotokset
- Sprint Goal määritelty

- Alustava Sprint Backlog muodostettu

Arkkitehtuuripäätökset lukittu (DuckDB + dbt + Medallion)

#### Sprintin tehtävät
- Lopullisen projektisuunnitelman vahvistaminen

- dbt-projektin alustus

- Dataputken arkkitehtuurin Bronze - Silver - Gold kuvauksen luonti

- Datan esikäsittely: Keinoja löytää validia dataa

- Bronze-tason tietomalli: Taulujen rakenteen suunnittelu ja luonti

- Dokumentaation päivitys

#### Sprint Goal
Vahvistaa lopullinen projektisuunnitelma sekä toteuttaa toimiva Bronze-tason ingestion, jossa raakadata ladataan DuckDB-ympäristöön dbt-työkalua hyödyntäen.

#### Sprint Backlog
[x] dbt-projektin alustus (Mitro)

[x] Bronze-taulujen luonti: SQL-mallit raakadatan lataamiseen (Tuija)

[x] Dokumentaatio: Dokumentaation päivitys työn edetessä (Joni)

[x] Dataputken arkkitehtuurikuvaus (Panu)

#### Sprintin Increment (toteutuva)

Toimiva dbt-projekti kytkettynä DuckDB-tietokantaan

Raakadata (Bronze) käytettävissä jatkojalostusta varten

#### Sprint DoD
[x] dbt-alustettu ja toimiva

[x] Bronze-taulut valmiit, ladatut

[x] Dokumentaatio päivitetty ajan tasalle

[ ] Dataputken arkkitehtuuri on kuvattu ja tiimin hyväksymä

### Daily tiistai  
Keskusteltiin miten dbt lähtee päälle. Mietittiin, että voisi lisätä läpinäkyvyyttä ulkopuolelle. Mietittiin datan rakennetta.
    
Paikalla kaikki: Joni, Toni, Panu, Tuija, Mitro

### Daily eskiviikko
    
Mitro esitteli, jopa filosofisia mietteitä asiakkaista dataan pohjautuen.
    
Paikalla kaikki Joni, Toni, Panu, Tuija, Mitro
    
### Daily Torstai
    
Keskusteltiin, että tää viikko on aika mellow ja ensi viikolla aletaan tekemään modeleita jolloin saadaan harppauksin eteenpäin.
    
Paikalla Joni, Toni, Panu, Mitro

## Sprint 3 – Silver-malli

**Tavoitteet:**

Normalisoidut Silver-taulut ja aggregaatiot
Dimensiotaulujen luonti

**Tehtävät:**

Silver-taulujen transformointi Bronze-datasta
Dimensiotaulujen ja avainmittareiden määrittely
Dokumentaatiopäivitykset (mkdocs, hedgehoc sprintit)

**DoD:**

Silver-taulut valmiit ja testatut
Dimensiotaulut oikein ja testit OK
Dokumentaatio ajan tasalla


-------
## Product Backlog

Koska käytettävän datan perusrakenne (x- ja y-koordinaatit, aikaleima ja kärry-ID)on tiedossa etukäteen, projektin alussa määritellään ja toteutetaan alustava erustietomalli. Mallia tarkennetaan ja laajennetaan Scrum-periaatteiden mukaisesti sprinttien aikana analyysitarpeiden kasvaessa.

Status:

[TODO] - alempi prioriteetti
[READY] - priorisoitu, valmis sprinttiin
[DONE]  - valmis, DoD täyttynyt
[REMOVED] - poistettu / korvattu


Product Backlog -itemien tila merkitään backlog-listaan. Valmiit itemit säilytetään näkyvissä historiatiedoksi, mutta niitä ei enää priorisoida tai oteta sprintteihin.


#### Epiikka
- Asiakaskäyttäytymisen ymmärtäminen ostoskärrydatan avulla


#### Tekninen backlog-item: Perustietomallin määrittely – 2–3 SP [READY]

Kuten kehitystiimi
haluamme määritellä ja toteuttaa perustietomallin
(x, y, aikaleima, kärry_id),
jotta paikannusdata voidaan tallentaa ja käyttää analyyseissä.


#### User Story: Kauppareissujen pituus – 3 SP [READY] 

Kuten kauppias
haluan analysoida asiakkaiden kauppareissujen keston
jotta voin ymmärtää asiakkaiden käyttäytymistä ja myymälän toimivuutta.
   
**Hyväksymiskriteerit:**
- Kauppareissun alku ja loppu tunnistetaan datasta
- Kesto voidaan laskea
- Tulokset esitetään tilastollisesti

#### User Story: Asiakkaiden kulkureitit – 5 SP [READY] 

Kuten kauppias
haluan tutkia asiakkaiden käyttämiä kulkureittejä
jotta voin ymmärtää, miten asiakkaat liikkuvat myymälässä.

**Hyväksymiskriteerit:**
 - Reitit voidaan visualisoida kaupan pohjakuvan päällä
 - Visualisointi perustuu paikannusdataan
 - Useamman asiakkaan reittejä voidaan tarkastella

#### Tekninen backlog-item: Datan suodatus ja rajaus – 3 SP [READY] 

Kuten kehitystiimi
haluamme suodattaa epäoleelliset ja virheelliset sijaintipisteet
jotta analyysit perustuvat luotettavaan aineistoon.
   
**Hyväksymiskriteerit:**
- Kaupan rajojen ulkopuoliset pisteet tunnistetaan
- Poistetut pisteet voidaan raportoida

#### User Story: Kuumat alueet (heatmap) – 3 SP [TODO] 

Kuten kauppias
haluan nähdä myymälän kuumat alueet
jotta voin tunnistaa alueet, joissa asiakkaat viettävät eniten aikaa.
   
 **Hyväksymiskriteerit:**
 - Heatmap muodostetaan paikannusdatan perusteella
 - Aikaväli on rajattavissa

#### User Story: Pysähdyspaikat ja pysähdysajat – 5 SP [TODO] 
Kuten kauppias  
haluan tunnistaa asiakkaiden pysähdyspaikat ja pysähdysajat  
jotta voin analysoida tuotteiden ja alueiden kiinnostavuutta.  
   
**Hyväksymiskriteerit:**
- Pysähdys määritellään liikkumattomuuden perusteella
- Pysähdykset voidaan visualisoida

#### User Story: Paikannustarkkuuden analyysi – 8 SP [TODO] 

Kuten paikannusyrityksen edustaja
haluan analysoida paikallaan olevien laitteiden sijaintivaihtelua
jotta voin arvioida paikannusjärjestelmän tarkkuutta.

#### User Story: Datan kohinan ja virhepisteiden analyysi – 8 SP [TODO]

Kuten paikannusyrityksen edustaja
haluan tunnistaa epäloogiset tai kaupan ulkopuolella olevat sijaintipisteet
jotta voin arvioida datan laatua ja käytettävyyttä.

#### Tekninen backlog-item: Silver-mallista Gold-malliin [TODO]

Kehittäjänä
haluan, että data kulkee Silver-kerroksen mallien kautta Gold-kerroksen malleihin dbt:n `ref()`-viittausten avulla
jotta dataputki on selkeä, toistettava ja testattava ilman manuaalisia välivaiheita.

**Hyväksymiskriteerit:**
- Gold-mallit viittaavat Silver-malleihin `ref()`-funktiolla
- `dbt run` ajaa mallit oikeassa järjestyksessä (Silver ennen Goldia)
- `dbt test` vahvistaa Gold-taulujen avainmittarit
- Lineage-kaavio näyttää selkeän ketjun Bronze → Silver → Gold

#### User Story: Aikarajauksella suodatettava dashboard [TODO]

Asiakkaana
haluan tarkastella dashboardin dataa päivä-, viikko- ja kuukausitasolla
jotta voin seurata asiakaskäyttäytymistä ja myymälän toimivuutta haluamaltani aikaväliltä.

**Hyväksymiskriteerit:**
- Dashboardissa on valitsin, jolla aikaväli valitaan (päivä / viikko / kuukausi)
- Kaikki visualisoinnit päivittyvät valitun aikavälin mukaan

#### Tekninen backlog-item: Gold-tauluista data BI-alustalle [TODO]

Kehittäjänä
haluan, että Gold-kerroksen taulut ovat käytettävissä BI-alustalla (Streamlit)
jotta analyytikot ja asiakkaat voivat hyödyntää jalostettua dataa ilman suoraa tietokantayhteyttä.

**Hyväksymiskriteerit:**
- Streamlit lukee datan suoraan DuckDB:n Gold-tauluista
- Yhteydenotto tapahtuu vain yhden konfiguraatiotiedoston kautta

#### Jatkokehitysidea: Ulkoisten datalähteiden yhdistäminen [TODO]

## Projektin yhteenveto

## Koko ryhmän työaikayhteenveto


















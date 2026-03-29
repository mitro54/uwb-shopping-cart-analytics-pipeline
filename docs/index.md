---
Projektiopinnot 1: Datan hallinta - ByteBuddies
===

[toc]

# Tehtävänanto
Projektin tavoitteena on analysoida ja visualisoida sisätiloissa tapahtuvaa ostoskärryjen liikkumista UWB‑paikannusdataa hyödyntäen. Projekti sisältää suurikokoisen CSV‑muotoisen raakadatamassan esikäsittelyn (ETL/ELT), tallentamisen tietokantaan sekä analyysin, jossa tarkastellaan kärryjen liikkeitä kaupan pohjakuvassa, läpimenoaikoja, kuumia alueita, nopeuksia ja käytön jakautumista eri ajankohtina. Tulokset esitetään tilastollisina analyyseina ja visuaalisina kuvaajina eri vuorokauden- ja viikonajoille, ja tavoitteena on tuottaa ymmärrettävää tietoa asiakasvirroista sekä ideoida mahdollisia lisäarvoa tuottavia jatkoanalyyseja, kuten ulkoisten datalähteiden yhdistämistä.

Projekti on toteutettava tiukasti Scrum‑menetelmää noudattaen, sisältäen selkeästi määritellyt sprintit, roolit, backlogit sekä säännölliset sprinttiseremoniat, ja työskentelyn eteneminen dokumentoidaan osana projektin lopputuloksia.

Projektin lopputulos muodostuu sprinttien aikana syntyvistä inkrementeistä, ja projektin etenemistä arvioidaan sprinttikohtaisesti Scrum-viitekehyksen mukaisesti.

# Projektiryhmä
- Joni Helminen
- Mitro Vaskela
- Panu Eklund
- Toni Kiuru
- Tuija Aumala

# Scrum-roolit 

Roolit kiertävät sprinttikohtaisesti. Jokaisessa sprintissä on nimetty:

- Tuoteomistaja (Produt Owner, PO)
    * Vastaa priorisoinnista
    * Ymmärtää liiketoiminnan tarpeet
    * Pitää backlogia ajan tasalla
    * Yhteys tiimiin ja sidosryhmiin
- Scrum Master (SM)
    * Poistaa esteitä
    * Tukee tiimiä
    * Ei johda, vaan mahdollistaa

- Kehitystiimi (Developer Team)

    * Itseohjautuva
    * Moniosaava (kaikki tarvittava osaaminen)
    * Ei jäykkiä rooleja
# Data-aineisto

* CSV.tiedoston rakenne
* ~140 000 000 riviä

# Definition of Done (DoD)

* Määrittää milloin työ on valmis
* Kaikkien noudatettava

## Tekniset kriteerit
- MariaDB
- Jupyterlab -kontit ETL-prosessia varten
## Toiminnalliset kriteerit (Features)

1. Tulosten raportointi.

2. Toimiva koodi, jota asiakas voi käyttää jatkossa.
**Kauppias:**

    * Asiakkaiden käyttämien reittien tutkimiseen.
    * Asiakasmäärien tutkimiseen
    * Asiakkaiden käyttäytymisen tutkimiseen (kauppareissujen pituus, pysähdyspaikat ja -ajat, jne.)

    **Paikannusyritys:**

    * Paikannustarkkuuden tutkimiseen paikallaan olevien laitteiden avulla (esim. paikan keskihajonta)
    * Paikannuksen hyvyyden/käytettävyydentutkimiseen. (esim. kaupan ulkopuolle olevien pisteiden lkm. tai paikassa olevan “kohinan” määrä.)

3. Koodin dokumentaatio.


Lisäksi inkrementti katsotaan valmiiksi, kun:
- se on integroitu yhteiseen repositorioon
- se on demonstroitu sprinttikatselmuksessa
- siihen liittyvä dokumentaatio on päivitetty


# Käytetyt työkalut ja menetelmät

- [Gitlab](https://gitlab.dclabra.fi)
Projektinhallinta toteutetaan Gitlab-järjestelmässä muodostamalla projektiryhmälle oma projekti, johon tallennetaan kaikki projektin artefaktit (l. tuotokset), esimerkiksi lähdekoodi ja dokumentaatio. Projektin tehtävänhallinta toteutetaan Gitlabin issue boardin avulla.

- [Clockify](https://app.clockify.me/tracker)
Projektin eteen tehtyä työmäärää seurataan wakatime-pluginilla (ohjelmointi) ja Clockify-työkalulla. Projektin ajan tehdään “oikeita töitä” ja kirjataan tehdyt työt ylös.

- [Docker](https://docker.com)
- [Visual Studio Code](https://code.visualstudio.com/)
- DCLabran [Disco-alusta](https://disco.dclabra.fi)

- Scrum-menetelmä : Virallinen [Scrum-ohje](https://scrumguides.org/docs/scrumguide/v2020/2020-Scrum-Guide-Finnish.pdf)

**Huom!** Työajanseurantaa käytetään oppilaitoksen vaatimusten täyttämiseen, ei Scrumissa käytettävänä ohjaus- tai arviointimittarina.

----

# Scrum-rakenne ja etenemismalli

## Sprintit


- Daily scrum ma-to klo 20.00
    - Miten menee
    - Onko ongelmia
- Retro maanantaisin klo 17.00
    - Mikä toimi hyvin
    - Mikä ei toiminut
    - Parannusehdotukset
    - Tiimin fiilis
    - Yhteenveto 
- Sprinttikatselmus maanantaisin klo 18.00
    - Tarkastellaan kehitetty tuoteversio
- Seuraavan sprintin suunnittelu maanantaisin klo 19.00
    - Suunnitellaan seuraavan sprintin työt
- Sprint Review (Demo)

    * Näytetään valmis toimiva tuote
    * Saadaan palautetta
    *
    Sprint Review järjestetään jokaisen sprintin lopussa.
    Projektin aikana pidetään lisäksi kaksi laajempaa demoa sidosryhmille.

## Aikataulu
Roolit on laitettu kiertämään niin, että ensimmäisten viiden viikon aikana jokainen on ollut jokaisesa roolissa kerran. Loput voidaan joko arpoa tai sopia muuten.

|Sprintti|Viikko|Alkaa |Päättyy|[Tuoteomistaja](https://gitlab.dclabra.fi/wiki/s/HJQT28UHU)|[Scrummaster](https://gitlab.dclabra.fi/wiki/s/r1Ilh8USL) |
| -------- | -------- | --------  |---|---|---|
| 1 | 13| 23.3.2026| 27.3.2026|Tuija|Panu|
| 2 | 14| 30.3.2026| 3.4.2026|Joni|Tuija|
| 3 | 15| 6.4.2026| 10.4.2026|Toni|Joni|
| 4 | 16| 13.4.2026| 17.4.2026|Mitro|Toni|
| 5 | 17| 20.4.2026| 24.4.2026|Panu|Mitro|
| 6 | 18| 27.4.2026| 1.5.2026|||
| 7 | 19| 4.5.2026| 8.5.2026|||
| 8 | 20| 11.5.2026| 15.5.2026|||

## Artefaktit

- Product Backlog (PBL)
- Definition of Done (DoD)
- Sprint Backlog

## Mittarit ja seuranta

* Velocity (vain valmiit työt)
* Burndown chart (edistyminen)
* Tehtävien jatkuva päivitys

## Työmääräarviot

Story pointit kuvaavat käyttäjätarinoiden suhteellista vaativuutta (perustuen työmäärään, monimutkaisuuteen ja epävarmuuteen), eivätkä ne vastaa suoraan käytettyä aikaa.

Arviointi tehdään kehitystiimin toimesta käyttäen Fibonacci-asteikkoa (1, 2, 3, 5, 8, 13). Tarinoita arvioidaan suhteessa toisiinsa, ja liian suuret tarinat pilkotaan ennen sprinttiin ottamista


----
# Sprint 1

## Suunnittelupalaveri  - 23.3.2026 klo 18.30

Löysimme Epiikan, jonka pohjalta alamme valmistelemaan projektia.

Scrumin dokumentointi siili-blogiin ja muut dokumentoinnit Gitlab pages. Sovimme ryhmän toimintatavoista, aikataulusta ja kävimme läpi mitä Scrum tapahtumissa tapahtuu. Nelipäiväinen työviikko, ma-to.

Päätimme, että ekan sprintin suurin työ on jokaiselle dataan tutustuminen Jupyter Notebookkeja käyttäen ja projektin alustus. Jokaiselle annettiin tehtäväksi tutustuminen dataan eri kantilta. Muistiinpanotlöydöksistä, joista sitten rakennetaan käyttäjätarinoita epiikan tueksi.


### Suunnittelupalaverin tuotokset
- Sprint Goal määritelty
- Alustava Sprint Backlog muodostettu
- Työskentelykäytännöt sovittu


## Sprintin tehtävät

-  Työkalujen käyttöönotto
-  Arviointiperusteisiin tutustuminen
-  Kehitysympäristön pystyttäminen omalle koneelle
-  Työtehtävien jako
    - tehtävien karkeustasot: epiikka, käyttäjätarina, tehtävä
- Sprintin toimenpiteistä sopiminen
    - dailyt, demo, retro
- Projektityöskentelyn aloittaminen (taskit Gitlabista)


## Sprint Goal
Luoda yhteinen tekninen ja toiminnallinen pohja projektin aloittamiselle sekä muodostaa ymmärrys datan rakenteesta ja laadusta.

## Sprintin Increment (toteutunut/kehittyvä)
- [x] Projektirepositorio luotu
- [x] Scrum-käytännöt sovittu
- [ ] Kehitysympäristö osittain valmis
- [ ] Alustava ymmärrys datasta muodostettu


## Sprintin backlog (Kehitystiimi)

Päivitetään suunnittelupalaverissa. Tiimi antaa ennusteen, mitä toiminnallisuutta seuraava versio sisältää. Tehtävien tuntiarviot ovat suuntaa-antavia. Sprinttien ennustettavuus perustuu tiimin kokemukseen eikä yksittäisiin tuntimääriin.

- Kehitysympäristö
    - [ ] Docker kontin pystytys (Joni) 30 min
    - [ ] Projektin rakenne (Tomi) 5 min
    - [ ] Dataformaatti (Toni) 2 h
- Data
    - [ ] Miten asiakas liikkuu kaupassa (Toni) 2 h
    - [ ] Datan laatu (Panu) 4 h
    - [ ] Datan mahdollisuudet (Kaikki) 2 h / hlö
    - [ ] Sijainnin laatu (Joni) 10 h
    - [ ] Datateoriat/yhteydet (Mitro) 8 h
- Käyttäjätarinat
    - [ ]  Käyttäjätarinoiden tarkentaminen datan analyysin perusteella (Kaikki)  1 h / hlö


## Daily scrum
Sprintin aikana pidetään päivittäinen Daily Scrum. Alla kirjaukset päivien edetessä.

### tiistai 24.3.2026  klo 20.00
- Kävimme Scrumin toimintoja vielä tarkemmin läpi, Tuija oli selvittänyt paljon ja selvensi kaikille. Ei ollut ongelmia ja Mitro oli aloittanut jo datan plottausta Jupyterissä.
Paikalla: Mitro, Tuija, Joni ja Panu

### keskiviikko 25.3.2026 klo 20.00
- Tutustuttiin Jarin agenttihärveliin. Ei ongelmia.
- Paikalla: Mitro, Tuija, Panu 

### torstai 26.3.2026 klo 20.00
- Käytiin läpi Mitron löydöksiä
- Paikalla: Mitro, Tuija, Panu, Toni

## Sprint Review - ma 30.3.2026 klo 17.00

(Kirjataan sprintin päättyessä)

## Sprint Retro -  ma 30.3.2026  klo 18.00

(Kirjataan sprintin päättyessä)

-------
# Product Backlog

Koska käytettävän datan perusrakenne (x- ja y-koordinaatit, aikaleima ja kärry-ID)on tiedossa etukäteen, projektin alussa määritellään ja toteutetaan alustava erustietomalli. Mallia tarkennetaan ja laajennetaan Scrum-periaatteiden mukaisesti sprinttien aikana analyysitarpeiden kasvaessa.

Status:

[TODO] - alempi prioriteetti
[READY] - priorisoitu, valmis sprinttiin
[DONE]  - valmis, DoD täyttynyt
[REMOVED] - poistettu / korvattu


Product Backlog -itemien tila merkitään backlog-listaan. Valmiit itemit säilytetään näkyvissä historiatiedoksi, mutta niitä ei enää priorisoida tai oteta sprintteihin.


## Epiikka
- Asiakaskäyttäytymisen ymmärtäminen ostoskärrydatan avulla


## Tekninen backlog-item: Perustietomallin määrittely – 2–3 SP [READY]

Kuten kehitystiimi
haluamme määritellä ja toteuttaa perustietomallin
(x, y, aikaleima, kärry_id),
jotta paikannusdata voidaan tallentaa ja käyttää analyyseissä.


## User Story: Kauppareissujen pituus – 3 SP [READY] 

Kuten kauppias
haluan analysoida asiakkaiden kauppareissujen keston
jotta voin ymmärtää asiakkaiden käyttäytymistä ja myymälän toimivuutta.
   
**Hyväksymiskriteerit:**
- Kauppareissun alku ja loppu tunnistetaan datasta
- Kesto voidaan laskea
- Tulokset esitetään tilastollisesti

## User Story: Asiakkaiden kulkureitit – 5 SP [READY] 

Kuten kauppias
haluan tutkia asiakkaiden käyttämiä kulkureittejä
jotta voin ymmärtää, miten asiakkaat liikkuvat myymälässä.

**Hyväksymiskriteerit:**
 - Reitit voidaan visualisoida kaupan pohjakuvan päällä
 - Visualisointi perustuu paikannusdataan
 - Useamman asiakkaan reittejä voidaan tarkastella

## Tekninen backlog-item: Datan suodatus ja rajaus – 3 SP [READY] 

Kuten kehitystiimi
haluamme suodattaa epäoleelliset ja virheelliset sijaintipisteet
jotta analyysit perustuvat luotettavaan aineistoon.
   
**Hyväksymiskriteerit:**
- Kaupan rajojen ulkopuoliset pisteet tunnistetaan
- Poistetut pisteet voidaan raportoida

## User Story: Kuumat alueet (heatmap) – 3 SP [TODO] 

Kuten kauppias
haluan nähdä myymälän kuumat alueet
jotta voin tunnistaa alueet, joissa asiakkaat viettävät eniten aikaa.
   
 **Hyväksymiskriteerit:**
 - Heatmap muodostetaan paikannusdatan perusteella
 - Aikaväli on rajattavissa

## User Story: Pysähdyspaikat ja pysähdysajat – 5 SP [TODO] 
Kuten kauppias  
haluan tunnistaa asiakkaiden pysähdyspaikat ja pysähdysajat  
jotta voin analysoida tuotteiden ja alueiden kiinnostavuutta.  
   
**Hyväksymiskriteerit:**
- Pysähdys määritellään liikkumattomuuden perusteella
- Pysähdykset voidaan visualisoida

## User Story: Paikannustarkkuuden analyysi – 8 SP [TODO] 

Kuten paikannusyrityksen edustaja
haluan analysoida paikallaan olevien laitteiden sijaintivaihtelua
jotta voin arvioida paikannusjärjestelmän tarkkuutta.

## User Story: Datan kohinan ja virhepisteiden analyysi – 8 SP [TODO]

Kuten paikannusyrityksen edustaja
haluan tunnistaa epäloogiset tai kaupan ulkopuolella olevat sijaintipisteet
jotta voin arvioida datan laatua ja käytettävyyttä.

## Jatkokehitysidea: Ulkoisten datalähteiden yhdistäminen [TODO]

# Projektin yhteenveto

# Koko ryhmän työaikayhteenveto


















# Projektiopinnot 1: Datan hallinta - ByteBuddies

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
- Scrum Master (SO)
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
- Toimiva tietokanta
- Jupyterlab -kontit ETL-prosessia varten
## Toiminnalliset kriteerit

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

## Epiikka

Asiakaskäyttäytymisen ymmärtäminen ostoskärrydatan avulla.



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
    * Kaksi kertaa projektin aikana
    * Näytetään valmis toimiva tuote
    * Saadaan palautetta

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

## Mittarit ja seuranta

* Velocity (vain valmiit työt)
* Burndown chart (edistyminen)
* Tehtävien jatkuva päivitys

## Artefaktit
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

## Sprintin Increment
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


## Daily scrum
Sprintin aikana pidetään päivittäinen Daily Scrum. Alla kirjaukset päivien edetessä.

### tiistai 24.3.2026  klo 20.00

## Sprint Review - ma 30.3.2026 klo 17.00

(Kirjataan sprintin päättyessä)

## Sprint Retro -  ma 30.3.2026  klo 18.00

(Kirjataan sprintin päättyessä)


--------
# Product Backlog (PBL)

* Lista tehtävistä
* Priorisoitu liiketoiminta-arvon mukaan
* Ylimmät tehtävät pieniä ja valmiita sprinttiin
* Tuoteomistaja vastaa


Järjestetty lista kaikesta, mitä tuotteessa saatetaan tarvita, sekä ainoa lähde tuotteeseen toteutettaville vaatimuksille ja muutoksille. Product Backlog elää projektin aikana ja sitä priorisoidaan uudelleen sprinttikatselmusten jälkeen saadun palautteen perusteella.


- [x] Epiikka
- [ ] Käyttäjätarinoiden pohtiminen (Kaikki) 1 h / hlö
- [ ] Tietokantarakenteen suunnittelu

## [Käyttäjätarinat](https://firmbee.fi/mita-kayttajatarinat-ovat)

Olen kauppias ja haluan tutkia asiakkaiden käyttämiä reittejä, koska..... 

Olen kauppias, ja haluan tutkia asiakasmääriä, koska....
Olen kauppias, ja haluan tutkia kauppareissujen pituutta, koska...

Olen kauppias, ja haluan tutkia asiakkaiden pysähtymispaikkoja ja -aikoja, koska...

Olen paikannusyrityksen edustaja, ja haluan käyttää ohjelmaa paikannustarkkuuden tutkimiseen paikallaan olevien laitteiden avulla (esim. paikan keskihajonta)

Olen paikannusyrityksen edustaja, ja haluan käyttää ohjelmaa hyvyyden/käytettävyyden tutkimiseen. (esim. kaupan ulkopuolle olevien pisteiden lkm. tai paikassa olevan “kohinan” määrä.)

# Projektin yhteenveto

# Koko ryhmän työaikayhteenveto

# Scrum-checklist

## 1. Ydinidea

Scrumissa tärkeintä on:

* Toimivan ohjelmiston toimitus usein (≤ 4 viikkoa)
* Liiketoiminnan kannalta tärkeimmän tekeminen
* Jatkuva parantaminen

## 2. Keskeiset roolit

### Product Owner (PO)



### Scrum Master (SM)


### Tiimi


## 3. Keskeiset artefaktit

### Product Backlog (PBL)



### Sprint Backlog

* Sprintin tehtävät
* Näkyvä ja päivitetään päivittäin
* Tiimin omistama

### Definition of Done (DoD)


---
Projektiopinnot 1: Datan hallinta - ByteBuddies

## Tehtävänanto
Projektin tavoitteena on analysoida ja visualisoida sisätiloissa tapahtuvaa ostoskärryjen liikkumista UWB‑paikannusdataa hyödyntäen. Projekti sisältää suurikokoisen CSV‑muotoisen raakadatamassan esikäsittelyn (ETL/ELT), tallentamisen tietokantaan sekä analyysin, jossa tarkastellaan kärryjen liikkeitä kaupan pohjakuvassa, läpimenoaikoja, kuumia alueita, nopeuksia ja käytön jakautumista eri ajankohtina. Tulokset esitetään tilastollisina analyyseina ja visuaalisina kuvaajina eri vuorokauden- ja viikonajoille, ja tavoitteena on tuottaa ymmärrettävää tietoa asiakasvirroista sekä ideoida mahdollisia lisäarvoa tuottavia jatkoanalyyseja, kuten ulkoisten datalähteiden yhdistämistä.

Projekti on toteutettava tiukasti Scrum‑menetelmää noudattaen, sisältäen selkeästi määritellyt sprintit, roolit, backlogit sekä säännölliset sprinttiseremoniat, ja työskentelyn eteneminen dokumentoidaan osana projektin lopputuloksia.

Projektin lopputulos muodostuu sprinttien aikana syntyvistä inkrementeistä, ja projektin etenemistä arvioidaan sprinttikohtaisesti Scrum-viitekehyksen mukaisesti.

## Yleistä

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

# Reittidatasta muodostettuja analyyseja

## Pohjatiedosto
Alkeelliset analyysit ovat muodostanut ..., `notebooks/01_03_data_exploration.ipynb` luomien erilaisten tilastojen ja lämpökarttojen pohjalta.

## Datan puhdistamiseen käytetyt asetukset
- Sessiokatkaisu: > 15.0 min signaalikatkos = uusi asiakas
- Paikallaanolo-detector: > 20 min ilman > 5m liikettä
- Reissun matkarajat: 30.0 - 8000.0 metriä
- Aikarajat: 3 - 240 minuuttia
- Spatial Spread (Jitter-suodatin): Reitin on levittäydyttävä > 15.0 m alueelle
- Filtteröidään koko kassa-alue ja lataustelakat pois
- Filtteröidään kaikki datapisteet kaupan aukioloaikojen ulkopuolelta pois
- Min sallittu keskinopeus 0.08 m/s
- Max sallittu reissun keskinopeus 1.5 m/s
- Max sallittu hyppy kahden pisteen välillä 3.0 m/s
- Oletus reitistä: Alkaa sisääntuloportista ja päättyy kassa-alueelle.
- Lopputulos: Lähes 11 miljoonaa riviä erinomaisen puhdasta reittidataa.

# Asiakasprofiilien Analyysi: Läpikävelijät ja Tutkiskelijat

## Segmentoinnin toteutus (K-Means Klusterointi)
Aikaisemmassa teoriointivaiheessa esitetty hypoteesi "kahdesta erilaisesta asiakaspersoonasta" vietiin testattavaksi koneoppimisen keinoin. Tavoitteena oli selvittää, jakaantuuko asiakaskunta luonnollisesti näihin kahteen ryhmään, ilman että datalle asetetaan etukäteen kovia, ihmisen keksimiä raja-arvoja (esim. olettamalla sokeasti, että yli 20 minuuttia kestävä reissu on aina tutkiskelua).

Tämän toteuttamiseksi raakadataa rikastettiin (Feature Engineering) ja siitä eristettiin reaalimaailman ostoskäyttäytymistä parhaiten kuvaavat tunnusluvut:
- **Kesto ja Matka:** Kaupassa vietetty aktiivinen aika sekä reitin kokonaispituus.
- **Viipymäaika (Dwell Time):** Aika sekunteina, jonka asiakas vietti käytännössä paikallaan (liike alle 0.15 metriä datapisteiden välillä).
- **Todelliset pysähdykset:** Yli 15 sekuntia kestäneet yhtäjaksoiset pysähdykset, jotka kuvaavat todellista hyllyn edessä seisomista satunnaisen hidastelun sijaan.

Datalle tehtiin lisäksi logaritminen muunnos (Log Transform), jotta poikkeukselliset ääriarvot (kuten pidemmät "maraton-reissut") eivät vääristäisi algoritmia. Tämän jälkeen K-Means-algoritmi jakoi asiakkaat onnistuneesti kahteen luonnolliseen klusteriin.

## Analyysin tulokset ja johtopäätökset
Klusteroinnin tuloksena syntynyt hajontakuvio vahvistaa alkuperäisen käyttäytymishypoteesin täydellisesti oikeaksi. Data jakautuu erittäin selkeästi ja realistisesti kahteen erilaiseen ostoskäyttäytymisen malliin:

### Läpikävelijät (Sininen klusteri)
- **Keskivertoluvut:** Kesto **9.2 min**, Matka **275 m**, Keskinopeus **32.0 m/min**.
- **Pysähdykset ja viipymä:** Keskimäärin vain **2 todellista pysähdystä** ja viipymäaika alle 3 minuuttia (168 s).
- **Johtopäätös:** Tämä ryhmä muodostaa visuaalisesti erittäin tiiviin keskittymän kuvaajan vasempaan alakulmaan. Luvut vastaavat täydellisesti tehokasta rutiiniostamista (esimerkiksi vain maitotölkin ja leivän noutamista). Reitit ovat nopeita, suoraviivaisia ja erittäin määrätietoisia. Asiakas tietää tarkalleen mitä hakee, eikä ylimääräistä aikaa kuluteta hyllyjen välissä kiertelyyn.

### Tutkiskelijat (Punainen klusteri)
- **Keskivertoluvut:** Kesto **26.7 min**, Matka **505 m**, Keskinopeus **20.0 m/min**.
- **Pysähdykset ja viipymä:** Keskimäärin **11 todellista pysähdystä** ja viipymäaika yli 12 minuuttia (765 s).
- **Johtopäätös:** Tämä ryhmä alkaa luonnollisesti siitä, mihin Läpikävelijät lopettavat. Matkat ja ajat ovat merkittävästi pidempiä, mutta erityisen huomionarvoista on hidastunut keskinopeus ja massiivisesti kasvanut viipymäaika. Tutkiskelija viettää lähes puolet kauppa-ajastaan seisten paikallaan tai erittäin hitaasti liikkuen. Nämä asiakkaat kiertelevät, vertailevat tuotteita ja altistuvat pitkäkestoisesti myymälän heräteostos- ja sesonkitarjonnalle.

!!! success "Datan jalostamisen tuoma lisäarvo"
    Yksinkertainen keston tai matkan tuijottaminen ei olisi riittänyt näin tarkan ja luotettavan profiilin luomiseen. Ottamalla huomioon **Dwell Time** -mittarin ja suodattamalla esiin vain aidot yli 15 sekunnin pysähdykset, algoritmi kykeni löytämään asiakkaiden todellisen motiivin. Esimerkiksi nopeakin kauppareissu on voitu luokitella tutkiskeluksi, jos asiakas on viettänyt suhteellisen suuren osan ajastaan pysähdyksissä tutkien tiettyä tuoteryhmää.

# Asiakasprofiilien Jakauma ja Spatiaalinen Vaikutus

## Jakauman muoto: Moodi vs. Mediaani
Aikaisemmissa teorioissa oletettiin, että massadatan jakauma on vinoutunut ja että Läpikävelijät muodostavat jakauman painopisteen. Visualisoimalla kokonaiskeston jakauman (Histogrammi), havaittiin selkeä bimodaalinen, eli kaksihuippuinen ilmiö.

- **Analyysin tulos (Histogrammi):** Jakauma ei ole normaali, vaan se koostuu kahdesta päällekkäisestä jakaumasta.
    - Koko datan **moodi** (yleisin kesto) asettuu Läpikävelijöiden piikkiin (n. 8–10 min). Tämä vahvistaa, että Läpikävelijät ovat asiakaskunnan suurin yksittäinen ryhmä.
    - Tutkiskelijoiden laajempi jakauma (moodi n. 25–30 min) vetää koko datan **mediaanin (18.6 min)** huomattavasti alkupään huipun yli.
- **Johtopäätös:** Teoria piti paikkansa. Jakauman muoto osoittaa suoraan asiakaskunnan kahtiajakoisuuden ja vahvistaa segmentoinnin tarpeellisuuden.

## Spatiaalinen Analyysi ja Myymälän Valtaväylät
Teorisoimme, että Läpikävelijät vaikuttavat massiivisesti myymälän lämpökarttoihin ja paljastavat myymälän "luonnollisen valtaväylän". Piirsimme lämpökartat (Mittauspisteiden tiheys) erikseen kummallekin profiilille, jotta näemme niiden todellisen spatiaalisen vaikutuksen myymälän pohjakartalle.

- **Analyysin tulos (Spatiaalinen lämpökartta):**
    - **Läpikävelijät (Luonnollinen Valtaväylä):** Kuvaaja paljastaa äärimmäisen selkeän ja terävän reittiverkoston. Tämä on se väylä, jota massat käyttävät suoriutuessaan tehokkaasti sisäänkäynniltä kassoille.
    - **Tutkiskelijat (Myymälän käyttö):** Kuvaaja leviää tasaisesti koko myymälän alueelle, paljastaen sesonkihyllyjen ja harvemmin vierailtujen alueiden käytön.
- **Johtopäätös:** Teoria piti täydellisesti paikkansa. Tutkiskelijat tuovat "lämmön" kylmiin alueisiin, kun taas Läpikävelijät kuluttavat valtaväylää. Tämä vahvistaa, että myymälän pohjapiirroksen optimoinnissa on huomioitava näiden kahden ryhmän erilaiset spatiaaliset tarpeet.

!!! warning "Ruuhka-aikojen nopeushypoteesin hylkääminen"
    Teorisoimme myös, että ruuhka-aikoina (arkipäivinä 16–17 ja viikonloppuina 12–14) asiakkaiden keskinopeus pienenisi ruuhkautumisen vuoksi. Vertaamalla aikasarjalämpökarttoja (Asiakasvolyymi vs. Keskinopeus tunti/viikonpäivä -akselilla), emme pystyneet vahvistamaan tätä hypoteesia. Vaikka volyymi kasvaa odotetusti, nopeus ei putoa vastaavassa suhteessa. Tämä saattaa johtua siitä, että kauppa on fyysisesti niin laaja, ettei ruuhkautuminen vaikuta koko reissun keskinopeuteen. Jätämme tämän hypoteesin raportista pois vahvistamattomana.

# Sesonkianalyysi: Arkirutiinit vs. Joulusesonki

## Vertailuasetelma ja Datapohja
Testataksemme teorioita sesongin vaikutuksesta ostoskäyttäytymiseen, jaoimme datan kahteen vertailukauteen. Sesonkiajaksi valittiin joulunalusaika (joulukuun 1.–23. päivä). Puhtaimmaksi arjen vertailukohdaksi (baseline) valikoitui syyskuu. Syyskuussa arki rullaa rutiinilla, lomat ovat ohi, eikä isoja juhlasesonkeja ole käynnissä.

## 1. Asiakasprofiilien suhteen muutos
Teorisoimme, että sesongin aikana nopeat rutiiniostajat (Läpikävelijät) muuttuvat juhlajärjestelyjen myötä enemmän aikaa viettäviksi Tutkiskelijoiksi. 

- **Analyysin tulos (Pylväsdiagrammi):** Syyskuussa Tutkiskelijoiden osuus oli 62.5 %. Joulukuussa tämä osuus kasvoi **70.1 prosenttiin**. Vastaavasti nopeiden Läpikävelijöiden osuus kutistui alle 30 prosenttiin.
- **Johtopäätös:** Hypoteesi vahvistettu. Myymälän asiakasvirran luonne muuttuu sesongin aikana mitattavasti hitaammaksi ja tutkiskelevammaksi. Asiakkaat tekevät selkeästi arjesta poikkeavia hankintoja.

## 2. Kestojen jakauman litistyminen
Teorisoimme matemaattisesti, että sesongin aikana kauppareissujen kestojen jakauman alkupään piikki madaltuu ja mediaaniviiva siirtyy oikealle.

- **Analyysin tulos (KDE-tiheyskuvaaja):** Visuaalinen kuvaaja osoittaa selkeästi, kuinka syyskuun vihreä "vuori" litistyy joulukuussa ja jakauman "häntä" paksunee. Kauppareissun mediaanikesto kasvoi syyskuun 17.6 minuutista joulukuun 20.4 minuuttiin. Keskimääräinen asiakas viettää siis sesonkina **2.8 minuuttia kauemmin** myymälässä.
- **Johtopäätös:** Hypoteesi vahvistettu. Ylimääräinen kolme minuuttia per asiakas tarkoittaa massatasolla valtavaa potentiaalia heräteostoksille, ja myymälän sesonkihyllyillä on poikkeuksellisen paljon silmäpareja.

## 3. Kassa-alueen jonoutumisilmiö
Koska varsinainen kassa-alue filtteröitiin pois raakadatasta, teorisoimme, että massiiviset sesonkiruuhkat näkyisivät datassa "jonon häntänä". Oletus oli, että asiakkaiden Dwell Time (paikallaanoloaika) reitin viimeisen 120 sekunnin aikana kasvaisi räjähdysmäisesti joulukuussa, kun kassajonot purkautuvat pääkäytävälle.

- **Analyysin tulos (Boxplot & Keskiarvot):** Datan perusteella paikallaanoloaika reitin lopussa ei juurikaan eronnut kausien välillä (Syyskuu 45.0 s vs. Joulukuu 46.6 s). Myös boxplot hajonta pysyi lähes identtisenä.
- **Johtopäätös:** Hypoteesi jonojen purkautumisesta myymälän puolelle **hylättiin**. 

!!! success "Liiketoiminnallinen huomio: Onnistunut resursointi"
    Vaikka teoria jonoutumisilmiöstä ei näkynyt datassa, tämä on toimeksiantajan kannalta erinomainen uutinen! Vaikka myymälässä on merkittävästi enemmän hitaita Tutkiskelijoita ja kesto on pidempi, reitin lopun jonotusaika ei kasva. Tämä viittaa vahvasti siihen, että myymälän kapasiteetin hallinta toimii: sesonkiaikoina kassoja on avattu riittävästi vastaamaan kasvaneeseen kysyntään, jolloin pullonkaulaa ei pääse syntymään itse ostosalueelle.
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
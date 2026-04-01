# Reittidatasta muodostettuja teorioita

## Pohjatiedosto
Alkeelliset teoriat ovat muodostanut Mitro, `notebooks/01_03_data_exploration.ipynb` luomien erilaisten tilastojen ja lämpökarttojen pohjalta.

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

## Käyttäytymishypoteesit
- Tutkaillessani yksittäisiä satunnaisreittejä olen todennut asiakaskunnan olevan pääsääntöisesti kahdenlaista sorttia.
    - **Läpikävelijä**
        - Tämä asiakastyyppi oletettavasti tietää jo etukäteen mitä on tullut kauppaan hakemaan sekä kaupan pohjapiirroksen, kävelee pitkälti pääkäytävää pitkin noutaen vain tarvittavat tuotteet.
        - Tämä asiakastyyppi on oletettavasti yksi isoimmista syistä siihen, miksi pääkäytävä näkyy lämpökartoissa *erittäin* selkeästi.
        - Tyypillisesti lyhyempi vierailu kaupassa
        - Oletettavasti vähemmän impulssiostoksia tai poikkeamia reitiltä.
        - **Jos** toimeksiantaja toimittaisi varmaa tietoa kaupan hyllyjen sisällöistä, voitaisiin toimeksiantajalle analysoida helposti, kuinka optimaalisesti tuotesijoittelu on toteutettu houkuttelemaan tätä asiakastyyppiä heräteostoksiin.
        - Oletettavasti reitin pituus ja kesto mediaanikäyrän alkupäässä.

    - **Tutkiskelija**
        - Tämä asiakastyyppi oikein nauttii shoppailusta. He viettävät mielellään pitkiäkin aikoja kaupassa. Heillä voi olla ostoslista olemassa, mutta tutkailevat mieluusti kaupan muitakin antimia visiitillään.
        - Nämä asiakkaat ovat oletettavasti hyvin vieteltävissä tekemään useita heräteostoksia.
        - Reitti on tyypillisesti hyvin satunnainen ja hitaanlainen, joissain tapauksissa jopa kiertävä. Matka sisältää useita pysähdyksiä.
        - Nämä asiakkaat tuovat eniten sitä "lämpöä" lämpökartan kylmiin, vähän vierailtuihin alueisiin, heitä voisi kutsua jopa seikkailijoiksi.
        - Vastaavasti oletettavasti reitin pituus ja kesto on mediaanikäyrän loppupäässä.

!!! warning "Huom"
    Yksi huomionarvoinen seikka on, että yksi asiakaspersoona voi toimia päivästä ja seurasta riippuen *läpikävelijänä* tai *tutkiskelijana*. Joten analyysit täytyy muodostaa siltä pohjalta, että yksi asiakas voi itseasiassa olla **"kaksi asiakasta"**.

- Ruuhka-aikoina eli aikasarja-analyysistä löytyvästä ruuhkakartasta voidaan teorisoida, että arkipäivinä 16-17 sekä viikonloppuina 12-14 liikenne on vilkasta. Tästä syystä voisi luoda olettamuksen, että asiakkaiden keskinopeus on näihin aikoihin pienempi ja reitit ovat hajaantuneempia, koska ihmiset joutuvat väistelemään toisiaan ja kiertämään tukkeutuneita pääkäytäviä.

- Koska jokainen reitti alkaa samasta portista ja päättyy samalle kassa-alueelle, voidaan olettaa massadatasta paljastuvan myymälän luonnollinen valtaväylä. Tämä on se väylä, jolla *Läpikävelijät* vaikuttavat hyvin vahvasti.

- Mediaaniviiva asettuu hieman huipun yli, kun moodi taas on käyrän ihan alkupäässä. Teoria tähän on, että kauppa on iso ja monipuolinen, joten keskivertoasiakas viettää mielellään hieman enemmänkin aikaa kaupassa ja kävelee tutkiessaan hieman pidemmän matkan. Mutta kuten aikaisemmin totesin jo satunnaisreiteistä, asiakaskuntaa tuntuu olevan kahdenlaista. Joten nämä *Läpikävelijät* osoittavat osuutensa piikkinä jakaumassa.

## Sesonkiajat
Sesonkiajat ovat loistavaa kaupusteluaikaa. Voimme siis olettaa, että:

- Asiakasprofiilien suhde muuttuu
    - Tyypillisen arkiviikon nopeat *Läpikävelijät* muuttuvat juhlapyhien alla *Tutkiskelijoiksi*. Ostoskoriin tarvitaan arkisesta poikkeavia tuotteita, joita ei noudeta ulkomuistista esim. juhlaruoat, sesonkiherkut, lahjat.
    - Matemaattisesti tämä tulisi näkymään niin, että kestojen jakauman alkuosan piikki (moodi) madaltuu ja mediaaniviiva siirtyy huomattavasti oikealle kaupassa vietetyn ajan kasvaessa.

- Sesonkihyllyjen "painovoima"
    - Normaalisti viileänä pysyvät myymälän erikoisemmat alueet muuttuvat lämpökartoilla huomattavaksi pisteiksi. Tähän väittämään tosin voi olla hankala kaivaa enemmän todisteita, sillä oletusarvona on, että sesonkihyllyt sijaitsevat heti porttien jälkeen kaupan alussa.
    - Asiakkaat poikkeavat luonnolliselta valtaväylältään näille alueille, mikä sitten luo uusia, tilapäisiä pääreittejä kaupan sisälle.

- Ruuhkautuminen pt. 2
    - Kun asiakasmäärä ja ostoskärryjen volyymi kasvavat merkittävästi, koko kaupan keskinopeus putoaa.
    - Analyysissä tämä luo mielenkiintoisen haasteen; on pyrittävä tunnistamaan, johtuuko hyllyn edessä seisominen aidosta kiinnostuksesta ja tuotteiden vertailusta, vai yksinkertaisesti siitä, että käytävä on fyysisesti tukossa.
    - Oletetaan, että edellämainitusta syystä pystytään tunnistamaan kiertoreitit ja niiden mahdollinen mielekkyys.

- Kassa-alueen jonoutumisilmiö
    - Vaikka varsinainen kassa-alue on filtteröity datasta pois, sesonkiaikojen valtava asiakasmassa voi aiheuttaa sen, että jonot pidentyvät pääkäytävälle asti. Tämä voi näkyä datassa pitkinä paikallaanoloaikoina aivan reittien loppupäässä, mitä ei tule sekoittaa tuotteiden tutkiskeluun.
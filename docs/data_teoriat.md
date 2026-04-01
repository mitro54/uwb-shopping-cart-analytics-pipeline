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
1. Tutkaillessani yksittäisiä satunnaisreittejä olen todennut asiakaskunnan olevan pääsääntöisesti kahdenlaista sorttia.
    - **Läpikävelijä**
        - Tämä asiakastyyppi oletettavasti tietää jo etukäteen mitä on tullut kauppaan hakemaan sekä kaupan pohjapiirroksen, kävelee pitkälti pääkäytävää pitkin noutaen vain tarvittavat tuotteet.
        - Tämä asiakastyyppi on oletettavasti yksi isoimmista syistä, miksi pääkäytävä näkyy lämpökartoissa *erittäin* selkeästi.
        - Tyypillisesti lyhyempi vierailu kaupassa
        - Oletettavasti vähemmän impulssiostoksia tai poikkeamia reitiltä.
        - **Jos** asiakas toimittaisi varmaa tietoa kaupan hyllyjen sisällöistä, voitaisiin asiakkaalle analysoida helposti, kuinka optimaalisesti tuotesijoittelu on toteutettu houkuttelemaan tätä asiakastyyppiä heräteostoksiin.
        - Oletettavasti reitin pituuden ja keston mediaanikäyrän alkupäässä.

    - **Tutkiskelija**
        - Tämä asiakastyyppi oikein nauttii shoppailusta. He viettävät mielellään pitkiäkin aikoja kaupassa. Heillä voi olla ostoslista olemassa, mutta tutkailevat mieluusti kaupan muita antimia visiitillään.
        - Nämä asiakkaat ovat oletettavasti hyvin vieteltävissä tekemään useita heräteostoksia.
        - Reitti on tyypillisesti hyvin satunnainen ja hitaanlainen, joissain tapauksissa jopa kiertävä. Useita pysähdyksiä.
        - Nämä asiakkaat tuovat eniten sitä "lämpöä" lämpökartan kylmiin alueisiin, voisi kutsua jopa seikkailijoiksi.
        - Vastaavasti oletettavasti reitin pituuden ja keston mediaanikäyrän loppupäässä.

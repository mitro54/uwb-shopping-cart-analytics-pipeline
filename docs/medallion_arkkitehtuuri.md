Medallion-arkkitehtuuri ostoskärryjen liikedatan käsittelyssä

Tässä projektissa hyödynnetään Medallion-arkkitehtuuria (Bronze-Silver-Gold), jonka tarkoituksena on jäsentää datan käsittely selkeisiin vaiheisiin. Arkkitehtuuri parantaa datan laatua, helpottaa analysointia sekä tekee kokonaisuudesta skaalautuvan ja ylläpidettävän.

Bronze-kerros (raakadata)

Bronze-kerros sisältää ostoskärryjen liikedatan sellaisena kuin se saadaan lähteestä, eli CSV-tiedostoista. Jokainen rivi kuvaa yksittäistä mittausta (ping), joka sisältää kärryn sijainnin (x, y, z), aikaleiman sekä laadun kuvaavan q-arvon.

Tässä kerroksessa dataan tehdään vain kevyitä teknisiä muokkauksia, kuten sarakkeiden nimeämistä ja tietotyyppien muuntamista. Lisäksi voidaan lisätä metatietoa, kuten lähdetiedoston nimi tai datan latausajankohta. Varsinaista liiketoimintalogiikkaa ei tässä vaiheessa sovelleta.

Bronze-kerroksen päätarkoitus on säilyttää alkuperäinen data muuttumattomana, jotta siihen voidaan tarvittaessa palata myöhemmin.

Silver-kerros (Puhdistettu ja rikastettu data)

Silver-kerroksessa dataa puhdistetaan ja rikastetaan analyysiä varten. Tässä vaiheessa poistetaan virheellisiä tai epäluotettavia havaintoja, kuten duplikaatteja, puuttuvia arvoja tai epärealistisia sijaintitietoja.

Lisäksi voidaan hyödyntää q-arvoa datan laadun arviointiin, esimerkiksi suodattamalla pois heikkolaatuiset mittaukset.

Silver-kerroksessa dataa rikastetaan laskemalla liikkeeseen liittyviä tunnuslukuja. Näitä ovat esimerkiksi:

- edellinen sijainti ja aikaleima
- aikaväli peräkkäisten mittausten välillä
- kuöjettu matka (x- ja y-koordinaattien perusteella)
- arvioitu liikkumisnopeus

Tämän vaiheen tuloksena syntyy luotettava ja yhtenäinen tapahtumatason datasetti, jota voidaan käyttää suoraan jatkoanalyysiin.

Gold-kerros(liiketoimintadata)

Gold-kerros sisältää valmiiksi jalostettua ja aggregoitua dataa, joka vastaa suoraan analyysikysymyksiin. Tässä kerroksessa data yhdistellään ja tiivistetään helposti hyödynnettävään muotoon.

Esimerkkejä Gold-kerroksen tuottamasta tiedosta ovat:

- kärryjen käyttömäärät eri ajankohtina
- kärryjen kulkema kokonaismatka
- aktiivisimmat käyttöajat
- ruuhkaisimmat alueet myymälässä (koordinaattien perusteella)

Gold-kerroksen data on suunniteltu käytettäväksi esimerkiksi visualisoinneissa, raporteissa tai jatkoanalyyseissä ilman, että käyttäjän tarvitsee käsitellä raakadataa.


Datan kulku

Datan käsittely etenee vaiheittain Bronze-, Silver- ja Gold-kerrosten läpi. Raakadata luetaan ensin Bronze-kerrokseen, jossa se säilytetään alkuperäisessä muodossaan. Tämän jälkeen data puhdistetaan ja rikastetaan Silver-kerroksessa. Lopuksi Gold-kerroksessa muodostetaan analyysivalmiit näkymät ja aggrekaatiot.


Yhteenveto
Medallion-arkkitehtuuri tarjoaa selkeän rakenteen datan käsittelyyn. Bronze-kerros säilyttää alkuperäisen datan, Silver-kerros varmistaa datan laadun ja rikastaa sitä, ja Gold-kerros tuottaa liiketoimintaa tukevan analyysidatan. Tässä projektissa erityisesti q-arvon hyödyntäminen datan laadun arvioinnissa on keskeinen osa Silver-kerroksen toimintaa.
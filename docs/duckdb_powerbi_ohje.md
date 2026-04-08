# Power BI & DuckDB Yhdistämisopas

Tässä projektissa analytiikan tietovarasto ("Data Warehouse") pyörii puhtaasti lokaalina DuckDB-tiedostona (`.duckdb`), jota dbt-putki päivittää. Koska Power BI ei tue DuckDB:tä täysin "out-of-the-box" ilman ajureita, liiketoimintataulujen (`f_kaynti`, `dim_osastot` ym.) tuonti kojelaudalle tapahtuu ODBC-yhteyden kautta.

## 1. ODBC-ajurin lataaminen ja asennus

1. Siirry DuckDB:n viralliselle [Releases-sivulle](https://github.com/duckdb/duckdb/releases).
2. Etsi listasta viimeisin vakaa julkaisu ja lataa tiedosto **`duckdb_odbc-windows-amd64.zip`**.
3. Pura zip-kansion sisältö valitsemaasi sijaintiin (esim. `C:\duckdb_odbc\`).
4. Suorita kansion sisällä oleva **`duckdb_odbc_install.exe`** asentaaksesi ajurin (vaatii järjestelmänvalvojan oikeudet).

## 2. Windowsin ODBC-asetusten määrittäminen

> [!WARNING]  
> Saatat vahingossa avata Windowsin 32-bittisen ODBC-hallinnan. Varmista aina, että kirjoitat hakukenttään ohjelman nimen oikein, muuten et pysty konfiguroimaan 64-bittistä DuckDB:tä!

1. Avaa Windowsin Käynnistä-valikko ja hae tarkalleen nimellä: **ODBC Data Sources (64-bit)** (suom. 64-bittiset ODBC-tietolähteet).
2. Avaa ohjelma ja siirry välilehdelle **System DSN** (tai User DSN).
3. Paina painiketta **Add...** (Lisää) ja valitse listalta asennettu **DuckDB Driver**.
4. Täytä asetukset seuraavasti:
    - **Data Source Name:** Keksi projektille selkeä nimi (esim. `Bytebuddies_DB`).
    - **Database:** Poista oletuksena oleva sana `:memory:` ja kopioi tähän **tarkka absoluuttinen polku** dbt-projektisi duckdb-tiedostoon.
      Esim: `C:\Users\tuija\code\2026\bytebuddies\data\warehouse\dev.duckdb`
5. Paina OK. Tietolähde on nyt rekisteröity käyttöjärjestelmään!

## 3. Power BI:n yhdistäminen

1. Avaa Power BI Desktop ja valitse **Hae tiedot (Get Data)** -> **Lisää... (More...)**.
2. Kirjoita avautuvaan hakukenttään sana `ODBC` ja valitse se.
3. Valitse avautuvasta alasvetovalikosta äsken nimeämäsi tietolähde (esim. `Bytebuddies_DB`).
4. Paina OK.

> [!IMPORTANT]  
> Power BI kysyy sinulta ensimmäisellä kerralla kirjautumistietoja tähän tietokantaan. Koska DuckDB on puhdas paikallinen tiedosto, **siinä ei ole käyttäjätunnuksia**. 
> Valitse vasemmasta reunasta asetus **Default or Custom** (Oletus) ja jätä itse kentät aivan tyhjiksi. Paina vain ylpeästi Yhdistä (Connect)!

## 4. Datan Mallinnus / Analyysi
Kuittaamisen jälkeen ruudulle aukeaa Power BI Navigator. Löydät `main` -kansion alta kaikki dbt:n luomat valmiit Gold-tason mittaristot:
* `f_kaynti`
* `f_osastokaynti`
* `dim_karry`
* `dim_osastot`

Kaikki Silver-tason raskas siivoustyö on tehty jo aiemmin dbt-putken sisällä, joten Power BI:ssä riittää, että klikkailet haluamasi kaaviot kohdilleen! Ruksaa nuo taulut ja paina Lataa (Load).

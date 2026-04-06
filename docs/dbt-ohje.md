# dbt-käyttöohje (bytebuddies_dbt)

Tämä ohje auttaa dbt-ingestiojärjestelmän käytössä.  
Tällä ohjeella viet CSV-tiedostot DuckDB-tietokantaan.

## 1. Valmistelu
Varmista, että olet projektin juurikansiossa (`bytebuddies`) ja että olet asentanut riippuvuudet komennolla:
```bash
uv sync
```

## 2. dbt-projektin ajaminen
Kaikki dbt-komennot tulee suorittaa `bytebuddies_dbt`-kansiossa.

**Siirry dbt-kansioon:**
```bash
cd bytebuddies_dbt
```

**Aja kaikki mallit (lataa data CSV-tiedostoista):**
```bash
uv run dbt run
```
Tämä komento:
1. Lukee kaikki tiedostot polusta `data/raw/*.csv`.
2. Luo DuckDB-tietokantaan taulun nimeltä `stg_csv_data`.
3. Muuntaa sarakkeet oikeisiin tietotyyppeihin (VARCHAR, INT, TIMESTAMPTZ) ja lisää `latausajankohta`-metatiedon.

## 3. Datan ja mallien testaus
Voit varmistaa datan laadun ja eheyden ajamalla dbt-testit:
```bash
uv run dbt test
```

## 4. Dokumentaatio
dbt luo automaattisesti dokumentaation, josta näet taulujen rakenteet ja riippuvuudet:
```bash
uv run dbt docs generate
uv run dbt docs serve
```
*Tämä avaa selaimeen näkymän, jossa voit tutkia tietokannan rakennetta.*

## 5. Missä data on?
Datan käsittelyn jälkeen löydät sen DuckDB-tietokannasta:
- **Tiedostopolku:** `data/warehouse/dev.duckdb`
- **Päätaulu:** `stg_csv_data`

Voit tarkastella dataa millä tahansa DuckDB-yhteensopivalla työkalulla tai suoraan Pythonilla/Pandasilla käyttämällä kyseistä tiedostopolkua.

## 6. Huomioita kehitykseen
- **Uudet CSV-tiedostot:** Jos lisäät uusia `.csv`-tiedostoja `data/raw/`-kansioon, ne tulevat mukaan seuraavalla `uv run dbt run` -ajolla.
- **Mallien muokkaus:** Jos haluat muuttaa datan käsittelyä, muokkaa tiedostoa: `models/staging/stg_csv_data.sql`.
- **Profiilit:** dbt käyttää `profiles.yml`-tiedostoa, joka on tallennettu suoraan `bytebuddies_dbt`-kansioon helppoa käyttöä varten.

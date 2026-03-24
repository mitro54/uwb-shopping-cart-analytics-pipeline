# Teknologiat ja perustelut (ADR)

## Tiivistelmä

| Työkalu / kirjasto | Käyttö projektissa | Miksi valittiin |
|---|---|---|
| Python | Projektin yleinen ohjelmointikieli | Sopii hyvin datankäsittelyyn, visualisointiin ja automaatioon |
| uv | Riippuvuuksien ja virtuaaliympäristön hallinta | Nopea ja yksinkertainen tapa pitää tiimillä yhtenäinen ympäristö |
| DuckDB | Paikallinen analytiikkatietokanta | Kevyt, nopea ja toimii hyvin suoraan CSV-datan kanssa |
| dbt-core | Datan transformointi SQL-malleilla | Mallien hallinta, testaus, dokumentointi ja riippuvuuksien ohjaus |
| dbt-duckdb | dbt-adapteri DuckDB:lle | Mahdollistaa dbt-putken ajamisen suoraan DuckDB:tä vasten |
| pandas / polars | Mahdollinen esikäsittely ja datan tutkiminen | Kätevä raakadatassa havaittuihin tarkistuksiin ja kokeiluihin |
| matplotlib / plotly | Visualisoinnit | Soveltuu lämpökarttoihin, aikasarjoihin ja käyttöjakaumiin |
| MkDocs + Material for MkDocs | Projektidokumentaatio | Markdown-pohjainen, helppo julkaista GitLab Pagesiin |
| Jupyter Notebook | Tutkiva analyysi ja prototypointi | Hyvä datan alustavaan tarkasteluun ja visualisointikokeiluihin |


## Työkalut

**Python:**
Projektiin sopiva koodikieli, joka taipuu sujuvasti kaikkiin toimiin. Laajin kirjastovalikoima data-analytiikkaan; toimii saumattomasti dbt:n, DuckDB:n ja Jupyterin kanssa

**uv:**
Korvaa pip + venv yhdellä työkalulla, luo täysin toistettavan ympäristön uv.lock-tiedoston avulla. Toimii identtisesti Windowsilla, macOS:llä ja Linuxilla. Vältytään Dockerin käytöltä ainakin projektin alkupuolella vaikka tiimiläiset toimivat eri OS ympäristöissä.

**DuckDB:**
Saraketallennus ja vektorisoitu suoritus tekevät sadoista miljoonista riveistä hallittavia paikallisella koneella ilman erillistä palvelinta; lukee CSV-tiedostot suoraan `read_csv_auto` -funktiolla ilman erillistä latausta, ja sen CSV-lukija on nopeutunut lähes 3× viime versioiden aikana.

**dbt-core:**
dbt (Data Build Tool) hallinnoi SQL-mallit, niiden väliset riippuvuudet, automaattiset testit ja dokumentaation yhtenä kokonaisuutena. Mallit kirjoitetaan `.sql`-tiedostoihin ja dbt huolehtii oikeasta ajojärjestyksestä. Kaikki on versionhallinnassa ja tiimi voi tehdä muutoksia turvallisesti.

**dbt-duckdb:**
DuckDB-adapteri dbt:lle. Ilman adapteria dbt ei tiedä miten ottaa yhteyttä tietokantaan tai miten ajaa mallit sitä vasten. dbt-duckdb mahdollistaa koko putken ajamisen paikallisesti ilman pilveä tai erillistä palvelinta.

**pandas & polars:**
Pandas datan käsittelyn treenaamiseen. Sopiva työkalu aloittelijoille.

Polars on nopea DataFrame-kirjasto datankäsittelyyn. Pandas on tutumpi, mutta polars on merkittävästi nopeampi isoilla aineistoilla, koska se käyttää sarakepohjaista muistinkäsittelyä ja Rust-pohjaista toteutusta. Sopii hyvin tähän projektiin, joissa CSV-dataa tarvitsee tarkastella tai esikäsitellä ennen dbt-putken ajamista.

**matplotlib / seaborn / plotly:**
Matplotlib visualisointiin, sopii staattisiin PNG-exportteihin, Seaborn hienompiin kuvaajiin ja Plotly interaktiivisiin kuvaajiin notebookeissa

**MkDocs + Material:**
Markdown-pohjainen, ei vaadi erillistä rakennusjärjestelmää, julkaistaan automaattisesti GitLab CI/CD -pipelinella

**JupyterLab:**
Mahdollistaa nopean datantarkastelun suoraan DuckDB:stä SQL-kyselyillä ennen kuin koodi siirretään varsinaisiin Python-moduuleihin
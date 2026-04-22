# Projektisuunnitelma: ByteBuddies Dataputki ja BI-raportointi

## 1. Perustiedot ja tavoitteet
**Projektin nimi:** ByteBuddies Dataputki ja BI-raportointi
**Tausta:** Käsin tehty datan käsittely ja raportointi vie aikaa ja altistaa virheille. Jotta  kärryjen jatkuvaa dataa voitaisiin hyödyntää tehokkaasti liiketoiminnan ohjaamisessa, tarvitaan luotettava, automatisoitu dataputki.
**Tavoitteet:** 
- Rakentaa dataputki DuckDB:n ja dbt:n ympärille.
- Automatisoida datan siivous.
- Luoda toimivat näkymät (Dashboardit) päivittäisten, viikoittaisten ja kuukausittaisten mittareiden (KPI) seurantaan.
- Mahdollistaa tekoälyagenttien suora luku- ja kirjoitusyhteys kantaan kootun datan hyödyntämiseksi.

## 2. Rajaus (Scope)
**Mitä projektiin kuuluu:**
- Datan lataaminen raakadatana kantaan (Bronze).
- Datan puhdistaminen, normalisointi ja dimensiotaulujen rakennus (Silver).
- Datan jalostaminen liiketoiminnan tarpeisiin ja feature engineering -ominaisuuksien tekeminen (Gold).
- Raportoinnin ja BI-mittariston suunnittelu ja rakentaminen.
- Koodin versionhallinta, dokumentaatio (MkDocs) ja automaattiset dbt-testit.
- Tekoälyagenttien integroiminen DuckDB-tietokantaan

**Mitä projektiin EI kuulu:**
- Mobiilisovelluksen koodaaminen puhtaalta pöydältä.

## 3. Aikataulu ja virstanpylväät
Projekti on pilkottu kuuteen ydin-sprinttiin:

**Vaiheet:**
- **Sprint 1 (Alustus ja EDA):** Datan tutkiminen, projektin pystytys (Git, tiedostorakenteet) ja ensikatsaus aineistoon.
- **Sprint 2 (Bronze):** Dataputken suunnittelu, Bronze-taulut sekä jatkuvan integraation testien alustus.
- **Sprint 3 (Silver):** Normalisoidut taulut yhdisteltyinä Bronze-datasta, dbt-testaus aktivoituna.
- **Sprint 4 (Gold):** Liiketoimintalogiikat, aikapiirteet ja testatut valmiit Gold-taulut analytiikkaan.
- **Sprint 5 (BI & Agentit):** Mittariston (KPI) suunnittelu ja agenttien luku-/kirjoitusintegraatio.
- **Sprint 6 (Dashboard):** Dashboardit tuotantoon
- **Sprint 7 (Viimeistely):** Projektin viimeistely ja viimeiset viilaukset tuotantoon

**Deadline:** Kokonaisuus on oltava valmiina ja demottavissa Sprint 7:n päätteeksi.

## 4. Resurssit ja työnjako, joka vaihtuu joka viikko
**Tiimi ja roolit:**
- **Tuoteomistaja:** Tuoteomistaja vastaa tuotteesta ja on yhteyksissä tilaajaan.
- **Scrum master:** Scrum master pitää huolen, että ryhmällä ei ole stoppereita ja pitää huolen että ketterää kehitystä seurataan
- **Devaajat:** He hoitavat kunkin viikon koodaustehtävät.

**Työkalut:**
- **Infrastruktuuri ja kanta:** DuckDB, GitLab
- **Transformaatiot:** dbt (core), SQL, Python
- **Raportointi ja AI:** Tuettavat BI-työkalut, Python skriptit
- **Dokumentaatio:** MkDocs, Markdown

## 5. Riskienhallinta
**Riski 1: Lähdedatan laatu odotettua heikompi.**
- *Varasuunnitelma:* Nostetaan löydetyt virheet esiin heti EDA-vaiheessa (Sprint 1). Panostetaan ylimääräistä aikaa Silver-tason puhdistuslogiikkaan ja tingitään tarvittaessa Gold-tason hienoimmista feature-ominaisuuksista.

**Riski 3: Aikataulun venyminen dbt-kehityksessä**
- *Varasuunnitelma:* Priorisoidaan dbt-putken ydin. Kehitetään aluksi vain kaikista oleellisimmat KPI:t ja tiputetaan raskaampia testejä backlogille julkaisun jälkeiseen jatkokehitykseen.

## 6. Viestintä ja seuranta
**Palaverit:**
- **Sprint-suunnittelu:** Jokaisen sprintin alussa kokoontuminen, jossa sovitaan tarkat tasotehtävät ja hyväksymiskriteerit (DoD).
- **Viikkopalaverit / Dailyt:** Lyhyet palaverit, joissa katsotaan missä mennään.
- **Katselmointi (Demo):** Sprint 4:n ja 7:n päätteeksi pidetään demo toimivasta datan virtauksesta
**Dokumentointi:**
- Projektin suunnitelmat, ohjeet ohjelman eri osien käytösse **MkDocs**-sivustolla (`/docs`).
- Koodaamisen dokumentaatio tapahtuu GitLabissa.
- Projektisuunnitelma GitLab -kansiossa (`docs/project_plan.md`).

## 7. Asiakkaan toimeksianto ja projektin MVP (End Game)

Tässä osiossa määritellään projektin lopullinen toimitus eli MVP (Minimum Viable Product). Asiakas ei osta pelkkiä tietokantamalleja tai skriptejä, vaan ymmärrystä datasta ja työkaluja jatkoa varten. Toimitus nojaa kahteen tukijalkaan:

1. **Tulosten raportointi (BI/Dashboardit)**: Vastaa kauppiaan ja paikannusyrityksen kysymyksiin visuaalisesti ja ymmärrettävästi.
2. **Toimiva & dokumentoitu koodipohja (Data Pipeline)**: Yritys voi ajaa rakentamamme putken uudelleen myöhemmin omalla datallaan.

### 7.1 Selvitettävät asiat ja Dashboardit
Toteutamme raportoinnin rakentamalla **kaksi erillistä dashboardia**, jotka on kohdennettu kahden eri sidosryhmän tarpeisiin. Näiden avulla viestitään asiakkaalle työn tuottama lisäarvo.

**1. Kauppiaan Dashboard (Liiketoimintanäkökulma)**
Kauppias haluaa ymmärtää asiakkaiden käyttäytymistä myymälässä. Dashboardilla vastataan seuraaviin kysymyksiin:
- **Kuumat alueet (Heatmap):** Missä päin kauppaa asiakkaat viettävät eniten aikaa?
- **Pysähdyspaikat ja -ajat (Dwell-time):** Mihin asiakkaat pysähtyvät ja kuinka pitkäksi aikaa?
- **Kauppareissujen pituus:** Kuinka kauan keskimääräinen ostoskierros kestää (alku- ja loppuaika per asiakas)?
- **Aikasudatus:** Dashboardilta on löydyttävä aikarajaus (esim. aamupäivä vs. ruuhka-aika).

**2. Paikannusyrityksen Dashboard (Tekninen näkökulma)**
Paikannusyritys haluaa arvioida datan laatua ja paikannuslaitteiston toimivuutta. Dashboardilla vastataan seuraaviin kysymyksiin:
- **Paikannustarkkuus:** Kuinka tarkka paikannus on paikallaan olevien laitteiden osalta (esim. sijainnin keskihajonta)?
- **Kohinan ja virhepisteiden määrä:** Kuinka paljon aineistossa on häiriöitä (esim. myymälän ulkopuolelle lentävät virhepisteet, jotka on suodatettu pois datasta)?

### 7.2 Lopullinen "Definition of Done" (DoD) - Tarkistuslista
Projekti on tiimin osalta 100% valmis, kun seuraavat kriteerit täyttyvät:

**1. Ohjelmiston ja Datan Putki ("Working Code")**
- [ ] Datan suoritusputki (Raw -> Bronze -> Silver -> Gold) menee läpi alusta loppuun saumattomasti.
- [ ] Gold-kerroksessa ei ole ns. "haamudataa" (esim. virhepisteet tai kassojen kohina) estämässä analytiikkaa.
- [ ] Koodipohja `main`-haarassa on siivottu (ei merkityksettömiä testi- tai kokeilutiedostoja).
- [ ] Riippuvuudet (esim. DuckDB, dbt) on kirjattu ylös, jotta seuraava devaaja saa ohjelman pystyyn.

**2. Raportointi ja Visualisointi ("Reporting of Results")**
- [ ] Käytössä on selkeät BI-näkymät: toinen Kauppiaalle ja toinen Paikannusyritykselle.
- [ ] Käyttäjä voi suodattaa dataa ajan mukaan.
- [ ] Mittaristoista näkee yhdellä silmäyksellä vaaditut asiat (Heatmap, reissujen pituudet, tarkkuus, kohina).

**3. Dokumentaatio ("Documented Code")**
- [ ] MkDocs on ajan tasalla: Sieltä löytyy projektin arkkitehtuuri (Medallion) ja ohjeet lokaaliin pystytykseen.
- [ ] dbt docs on generoitu ja kertoo lyhyesti mallien (Silver/Gold) sisällöt.
- [ ] Koodin sisällä ei ole häiritseviä TODO-kommentteja, elleivät ne viittaa kirjattuihin jatkokehitysideoihin.
- [ ] Tämä A4-mittainen suunnitelma/kuvaus asiakkaalle selvitettävistä asioista on kirjoitettu MkDocsiin.
- [ ] Opettajille on laitettu pingaus Discordissa, kertoen että A4 on luettavissa.


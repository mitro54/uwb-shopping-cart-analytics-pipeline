# Tuotantotason Datan Siivousasetukset (Cleaning Config)

Tähän tiedostoon on tiivistetty kokeellisessa datan louhinnassa (EDA / Jupyter) hyviksi havaitut siivoussäännöt. Nämä rajoitteet ajetaan läpi dbt-dataputkessa, ja ne takaavat mallinnetun analytiikkadatan luotettavuuden ("Garbage in, garbage out" -ilmiön minimointi).

## Puhdistusasetukset

### 1. Peruslaatu ja Ominaisuudet
- **Q-arvon kynnys:** > 0.0 (Vaaditaan hyväksyttävä laatu signaalille)
- **Mittakaava:** 1 yksikkö = 1 cm (Muunnos metreiksi kaavalla `x / 100.0`).

### 2. Aukioloajat
Näiden ulkopuolella saapuvat mittaukset (kuten öiset huoltotyöt ja kärryjen kasaus) karsitaan:
- **Ma - La:** klo 08:00 - 21:00
- **Su:** klo 10:00 - 20:00

### 3. Geofencing ja Rajoitetut alueet
- **Kaupan rajat:** x: 0 - 10406, y: 0 - 5220
- **Sisääntulovaatimus:** Reitin _ensimmäisen_ pisteen on osuttava Entry Zone -alueelle (x: 0-1200, y: 0-5220).
- **Poissuljetut ongelma-alueet:**
  - Turvaportit latauspisteellä: Säde 400cm, sijainti (100, 2500)
  - Liukuportaat latauspisteellä: Säde 600cm, sijainti (900, 3600)

### 4. Liiketoimintalogiikka ja Sessioiden Pilkkominen
- **Signaalikatkonen raja (Session Gap):** 900 sekuntia (15 minuuttia). Mikäli sama kärry on ollut paikoillaan / vailla signaalia yli 15 minuuttia, ja se jatkaa uudelleen liikettä, se rekisteröidään uudeksi asioinniksi.

### 5. Jitter-suodattimet ja Fysiologiset Rajat
Yksittäisten "haamupisteiden" puhdistus:
- **Max sallittu yksittäinen hyppy:** 3.0 m/s. Estää signaalien vääristymät seinien läpi.

Reissutason hyväksymisrajat (karsitaan hylätyt kärryt, "ei-aidot" asiakkaat ja testit):
- **Otoksen määrä:** Min 30 mittauspistettä per sessio
- **Matka:** 30.0 metriä - 8000.0 metriä
- **Aika:** 3 minuuttia (180 s) - 4 tuntia (14400 s)
- **Spatiaalinen hajonta (Säde):** Reitin on levittäydyttävä vähintään 15.0 metrin säteelle, mikä estää sen, että reissu hyväksytään kun kärryä on "nitkitetty" paikoillaan 10 minuuttia.
- **Keskinopeus:** Välillä 0.08 m/s - 1.5 m/s. Ylinopeudet (esim. juokseminen ulos) tai lähes paikallaan seisominen hylätään analytiikasta kokonaan.

# ByteBuddies CLI: Käyttöohje

Tämä ohje selittää, miten agenttijärjestelmää käytetään komentoriviltä. Kaikki komennot ajetaan projektin juurikansiosta käyttäen `uv run` -komentoa.

## Peruskomento
```bash
uv run python -m agents.main [KOMENTO] [ARGUMENTIT]
```

---

## 1. Tietokantarakenteen hallinta (`schema`)
Tämä komento näyttää agentin ymmärtämän kuvan tietokannasta (taulut ja sarakkeet).

*   **Näytä nykyinen rakenne:**
    ```bash
    uv run python -m agents.main schema
    ```
*   **Päivitä rakenne (jos tietokanta on muuttunut):**
    ```bash
    uv run python -m agents.main schema --refresh
    ```

## 2. Kertaluonteiset kysymykset (`ask`)
Käytä tätä, kun haluat nopean vastauksen tiettyyn kysymykseen. Orkestraattori koordinoi vastauksen.

*   **Esimerkki:**
    ```bash
    uv run python -m agents.main ask "Mitkä ovat 5 nopeinta liikenneasemaa?"
    ```
*   **Käytä säiettä (muistaa aiemman keskustelun tässä säikeessä):**
    ```bash
    uv run python -m agents.main ask "Piirrä niistä graafi" --thread "liikenne_analyysi"
    ```

## 3. Interaktiivinen keskustelu (`chat`)
Käynnistää jatkuvan keskustelun agentin kanssa. Tämä on paras tapa tehdä syvällistä tutkimusta.

*   **Käynnistä chat:**
    ```bash
    uv run python -m agents.main chat
    ```
*   **Lopettaminen:** Kirjoita `quit`, `exit` tai `q`.

## 4. Agenttien muistin hallinta (`memory`)
Tarkastele, kuinka paljon agentti on kerännyt palautetta ja oppinut.

*   **Näytä tilastot:**
    ```bash
    uv run python -m agents.main memory stats
    ```
    *(Näyttää hyvien/huonojen palautteiden määrän ja tallennetut vuorovaikutukset)*

---

## Palautteen antaminen (Feedback Loop)
Aina kun käytät `ask` tai `chat` komentoja, järjestelmä kysyy vastausta jälkeen palautetta:
`Feedback [g=good / b=bad / Enter=skip]:`

*   **`g` (Good):** Tallentaa vastauksen onnistuneena esimerkkinä. Agentti yrittää matkia tätä tyyliä jatkossa.
*   **`b` (Bad):** Tallentaa vastauksen varoituksena. Agentti yrittää välttää vastaavia virheitä jatkossa.
*   **`Enter` (Skip):** Ei tallenna palautetta.

---

## Vinkkejä
1.  **Ole tarkka:** Jos haluat visualisoinnin, sano se suoraan: *"Piirrä heatmap..."*.
2.  **Säikeet:** Käytä `--thread` -argumenttia, jos haluat palata samaan aiheeseen myöhemmin (esim. `--thread "sprint_1_analyysi"`).
3.  **Kieli:** Agentti vastaa suomeksi, mutta ymmärtää myös englantia.

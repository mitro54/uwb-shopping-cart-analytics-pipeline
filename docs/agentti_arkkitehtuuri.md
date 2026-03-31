# ByteBuddies: Agenttipohjainen analytiikkajärjestelmä

Tämä dokumentti esittelee ByteBuddies-projektin älykkään agenttiarkkitehtuurin, sen toimintaperiaatteet ja syyt valittuun tekniseen toteutukseen.

## 1. Arkkitehtuurin yleiskuva
Järjestelmä perustuu **moniagenttimalliin (Multi-Agent System)**, jossa yksi "orkestraattori" ohjaa erikoistuneita agentteja. Toisin kuin perinteinen hakubotti, tämä järjestelmä kykenee itsenäiseen päättelyyn, työkalujen käyttöön ja virheistään oppimiseen (human-in-the-loop).

### Agenttien roolit:
1.  **Orkestraattori:** Järjestelmän aivot. Se ottaa vastaan käyttäjän luonnollisen kielen pyynnön, analysoi tavoitteen ja delegoi tehtävät oikeille asiantuntija-agenteille. Se pitää huolen keskustelun punaisesta langasta.
2.  **Schema-agentti:** Tämä agentti tuntee DuckDB-tietokannan rakenteen (taulut, sarakkeet ja suhteet). Se tarjoaa muille agenteille tarvittavan kontekstin, jotta ne tietävät, mistä dataa pitää hakea.
3.  **Analytiikka-agentti:** Suorittava porras. Se osaa kirjoittaa SQL-kyselyitä, analysoida saatuja lukuja ja luoda visualisointeja (kuten lämpökarttoja ja graafeja).

---

## 2. Miksi agenttipohjainen järjestelmä?

Olemme päätyneet tähän arkkitehtuuriin kolmesta kriittisestä syystä:

### A. Joustavuus ja datariippumattomuus (Data Agnosticism)
Suoritimme onnistuneen testin käyttäen järjestelmän ulkopuolista liikennedataa sisältävää DuckDB-tiedostoa. Agentit kykenivät:
*   Tunnistamaan automaattisesti taulut, joita ne eivät olleet koskaan nähneet.
*   Päättelemään sarakkeiden merkityksen (esim. nopeus ja asemat).
*   Tuottamaan oikeita tuloksia (esim. valtatie 4:n nopeusmittaukset).
Tämä todistaa, että **järjestelmä on robusti**: kun siirrymme varsinaiseen UWB-ostoskärrydataan, agentit osaavat sopeutua siihen välittömästi ilman koodimuutoksia.

### B. Inhimillinen palaute ja oppiminen (Feedback Loop)
Järjestelmässä on sisäänrakennettu **pitkäkestoinen muisti**.
*   Kun käyttäjä antaa palautetta vastauksesta (Hyvä/Huono), agentti tallentaa suorituksen vektori-tietokantaan.
*   **Onnistumiset** toimivat tulevaisuudessa esimerkkeinä (Few-shot prompting).
*   **Epäonnistumiset** muuttuvat "Lessons Learned" -varoituksiksi. Jos agentti on hallusinoinut tai tehnyt virheen aiemmin, se saa siitä varoituksen ennen uuden vastauksen luomista.

### C. Työkalujen käyttö (Tool Calling)
Agentit eivät vain arvaa vastauksia, vaan ne käyttävät **todellisia työkaluja**:
*   **DuckDB-työkalut:** Suorittavat oikeita SQL-kyselyitä tietokantaan.
*   **Visualisointityökalut:** Luovat Pythonin (Matplotlib/Seaborn) avulla heatmap- ja tilastokuvia suoraan datasta.

---

## 3. Miten se toimii käytännössä? (Esimerkki)

1.  **Kysymys:** "Missä kärryt liikkuivat eniten eilen klo 12-14?"
2.  **Orkestraattori:** Pyytää Schema-agentilta UWB-sijaintitaulun rakenteen.
3.  **Schema-agentti:** Kertoo, että `positions`-taulussa on `x`, `y` ja `timestamp`.
4.  **Analytiikka-agentti:**
    *   Suorittaa SQL-haun rajatulla aikavälillä.
    *   Huomaa saaneensa koordinaatteja.
    *   Kutsuu `plot_heatmap` -työkalua.
    *   Palauttaa vastauksen ja linkin kuvaan.
5.  **Käyttäjä:** Antaa palautteen "Hyvä!".
6.  **Muisti:** Järjestelmä muistaa tämän onnistuneen analyysipolun tulevaisuutta varten.

---

## 4. Käytetyt teknologiat
*   **LLM:** Qwen 3.5 (Lokaalisti Ollaman kautta) – optimoitu työkalujen kutsumiseen.
*   **Framework:** LangGraph – mahdollistaa agenttien välisen monimutkaisen logiikan ja tilanhallinnan.
*   **Database:** DuckDB – nopea analyyttinen tietokanta.
*   **Embedding:** Sentence-Transformers – mahdollistaa älykkään muistinhallinnan ja palautteen haun.

---

Tämä järjestelmä tarjoaa ByteBuddies-projektille skaalautuvan ja älykkään tavan muuttaa raaka UWB-data ymmärrettäväksi liiketoimintatiedoksi.

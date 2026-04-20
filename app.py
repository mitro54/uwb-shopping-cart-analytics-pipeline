"""
ByteBuddies UWB Dashboard analytiikka sovellus.

Tämä moduuli tarjoaa Streamlit-käyttöliittymän sisätilojen ostoskärryjen 
liikkeiden analysointiin moniagenttijärjestelmän avulla. Se käsittelee 
käyttäjän syötteet, näyttää visualisoinnit ja hakee tietokannasta dataa.

[TODO]: Tähän moduuliin tullaan lisäämään kaikki projektin tuottama informaatio käyttäjälle helposti saataville.

Kirjoittaja: Toni Kiuru
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from dataclasses import replace
import os
import json
import re
import requests
import plotly.io as pio
import dotenv

import agents.shared.config as config_module
from agents.orchestrator.agent import OrchestratorAgent
from agents.schema.agent import SchemaAgent
from agents.analytics.agent import AnalyticsAgent
from agents.shared.config import CONFIG

# --- Sivun asetukset ---
st.set_page_config(
    page_title="ByteBuddies UWB Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Teeman oletustila ---
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "🌙 Tumma"

# --- Premium CSS-tyylittely ---
def load_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if st.session_state.ui_theme == "☀️ Vaalea":
    load_css("light_style.css")
else:
    load_css("dark_style.css")

# --- Ollama-mallien haku ---
@st.cache_data(ttl=120, show_spinner=False)
def fetch_ollama_models():
    """Hakee saatavilla olevat mallit Ollama API:sta."""
    try:
        resp = requests.get(f"{CONFIG.ollama_base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return sorted([m["name"] for m in models])
    except Exception:
        return []

available_models = fetch_ollama_models()

# Callback: kun käyttäjä vaihtaa mallia alasvetovalikossa
def _apply_model_selection(ss_key: str, widget_key: str):
    """Päivittää session state -mallinvalinnan ja pakottaa agentit uudelleenluontiin."""
    new_value = st.session_state[widget_key]
    if new_value and new_value != st.session_state.get(ss_key):
        st.session_state[ss_key] = new_value

# --- Session State alustus ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit_session"

# Mallivalintojen oletusarvot CONFIG:sta
MODEL_ROLES = [
    ("model_orchestrator", "orchestrator_model", "🎯 Orkestraattori"),
    ("model_analytics", "analytics_model", "📊 Analytiikka"),
    ("model_plotter", "plotter_model", "🎨 Visualisointi"),
    ("model_schema", "schema_model", "🗄️ Skeema"),
    ("model_embedding", "embedding_model", "📎 Embedding"),
]
for ss_key, config_attr, _ in MODEL_ROLES:
    if ss_key not in st.session_state:
        if not available_models:
            st.session_state[ss_key] = "gemini-2.5-flash"
        else:
            st.session_state[ss_key] = getattr(CONFIG, config_attr)

# Päivitetään globaali CONFIG session state -valinnoilla (mutatoimalla)
config_module.CONFIG.orchestrator_model = st.session_state.model_orchestrator
config_module.CONFIG.analytics_model = st.session_state.model_analytics
config_module.CONFIG.plotter_model = st.session_state.model_plotter
config_module.CONFIG.schema_model = st.session_state.model_schema
config_module.CONFIG.embedding_model = st.session_state.model_embedding

# --- Agentit (avain = mallivalinnat → uudelleenluonti kun mallit vaihtuvat) ---
@st.cache_resource
def get_agents(_model_key: str):
    return OrchestratorAgent(), SchemaAgent(), AnalyticsAgent()

_model_cache_key = "|".join(
    st.session_state[ss_key] for ss_key, _, _ in MODEL_ROLES
)
orch, schema_agent, analytics_agent = get_agents(_model_cache_key)

# --- Agenttidata (lukee efektiivisestä configista) ---
AGENT_INFO = [
    {
        "icon": "🎯",
        "name": "Orkestraattori",
        "role": "Koordinoi muiden agenttien työtä",
        "model": config_module.CONFIG.orchestrator_model,
    },
    {
        "icon": "📊",
        "name": "Analytiikka",
        "role": "SQL-kyselyt ja data-analyysi",
        "model": config_module.CONFIG.analytics_model,
    },
    {
        "icon": "🎨",
        "name": "Visualisointi",
        "role": "Kaaviot, heatmapit ja plotit",
        "model": config_module.CONFIG.plotter_model,
    },
    {
        "icon": "🗄️",
        "name": "Skeema",
        "role": "Tietokannan rakenteen hallinta",
        "model": config_module.CONFIG.schema_model,
    },
    {
        "icon": "📎",
        "name": "Embedding",
        "role": "Semanttinen haku ja muisti",
        "model": config_module.CONFIG.embedding_model,
    },
]

# --- Sivupalkki ---
st.sidebar.markdown("""
<div style="text-align:center; padding: 1rem 0 0.5rem 0;">
    <span style="font-size: 2.2rem;">🛒</span>
    <div style="font-size: 1.3rem; font-weight: 700; letter-spacing: -0.02em; margin-top: 0.3rem;">ByteBuddies</div>
    <div style="font-size: 0.75rem; color: #64748B; font-weight: 500;">UWB Analytiikka</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.radio(
    "Teema",
    ["🌙 Tumma", "☀️ Vaalea"],
    key="ui_theme",
    horizontal=True,
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigointi",
    ["🏠 Etusivu", "🔑 API-avain", "💬 Agenttichat", "📊 Datatutkimus", "🖼️ Visualisoinnit"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown('<div class="section-header">📊 Dashboardit</div>', unsafe_allow_html=True)

dashboard_page = st.sidebar.radio(
    "Dashboard",
    ["—", "📈 Liiketoiminta"],
    label_visibility="collapsed",
)

# Jos dashboard valittu, se ohittaa päänavigaation
if dashboard_page != "—":
    page = dashboard_page

st.sidebar.markdown("---")

# --- Mallivalikot sivupalkissa ---
st.sidebar.markdown('<div class="section-header">🤖 LLM-mallit</div>', unsafe_allow_html=True)

st.sidebar.markdown("HUOM! Agentteja suositellaan ajamaan lokaalisti Ollamaa hyödyntäen. Mikäli se ei ole mahdollista, gemini API-avaimen voi syöttää sivupalkin API-avain osiossa.")

if available_models:
    for ss_key, config_attr, label in MODEL_ROLES:
        current_val = st.session_state[ss_key]
        # Varmistetaan että nykyinen valinta on listassa
        options = list(available_models)
        if current_val not in options:
            options.insert(0, current_val)
        idx = options.index(current_val)

        st.sidebar.selectbox(
            label,
            options=options,
            index=idx,
            key=f"_sel_{ss_key}",
            on_change=_apply_model_selection,
            args=(ss_key, f"_sel_{ss_key}"),
        )
else:
    # Fallback: teksti-input jos Ollama ei ole saatavilla
    st.sidebar.warning("⚠️ Lokaalia Ollamaa ei havaittu — käytetään pilvipalvelua (Gemini).")
    for ss_key, config_attr, label in MODEL_ROLES:
        st.sidebar.text_input(
            label,
            value=st.session_state[ss_key],
            key=f"_txt_{ss_key}",
            on_change=_apply_model_selection,
            args=(ss_key, f"_txt_{ss_key}"),
        )




# ═══════════════════════════════════════════════════════════════
# 1. ETUSIVU
# ═══════════════════════════════════════════════════════════════
if page == "🏠 Etusivu":

    # Hero-osio
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">ByteBuddies: UWB-Analytiikka</div>
        <div class="hero-subtitle">
            Moniagenttijärjestelmä sisätilojen ostoskärryliikkeen analysointiin —
            kysy datasta luonnollisella kielellä !
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Kaupan pohjapiirros
    st.markdown("### 🗺️ Kaupan pohjapiirros")
    st.markdown(
        '<div class="floorplan-container">',
        unsafe_allow_html=True,
    )
    st.image("image/kauppa.png", width='stretch')
    st.markdown(
        '<div class="floorplan-caption">Myymälän pohjapiirros — agentit voivat luoda heatmap-visualisointeja '
        'ostoskärryjen liikkeestä valitsemillesi ajanjaksoille</div></div>',
        unsafe_allow_html=True,
    )

    # Ominaisuuskortit
    st.markdown("### ✨ Järjestelmän kyvyt")
    feat_cols = st.columns(4)
    features = [
        ("💬", "Älykäs keskustelu", "Kysy mitä tahansa UWB-datasta luonnollisella kielellä."),
        ("⚡", "Automaattinen SQL", "Agentit kirjoittavat ja ajavat SQL-kyselyt puolestasi."),
        ("📈", "Visualisoinnit", "Heatmapit, aikasar­jat ja tilastot suoraan chattiin."),
        ("🧠", "Oppiva muisti", "Järjestelmä muistaa palautteesi ja parantaa vastauksiaan."),
    ]
    for col, (icon, title, desc) in zip(feat_cols, features):
        col.markdown(
            f'<div class="feature-card">'
            f'<div class="feature-icon">{icon}</div>'
            f'<div class="feature-title">{title}</div>'
            f'<div class="feature-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Agentit
    st.markdown("### 🤖 Järjestelmän agentit")
    agent_cols = st.columns(len(AGENT_INFO))
    for col, agent in zip(agent_cols, AGENT_INFO):
        col.markdown(
            f'<div class="agent-card">'
            f'<div class="agent-icon">{agent["icon"]}</div>'
            f'<div class="agent-name">{agent["name"]}</div>'
            f'<div class="agent-role">{agent["role"]}</div>'
            f'<span class="model-tag">{agent["model"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )



    # Tilastot
    st.markdown("### 📊 Tietokannan tila")
    try:
        stats = analytics_agent.feedback_store.stats()
        s1, s2, s3 = st.columns(3)
        s1.markdown(
            f'<div class="stat-card stat-total">'
            f'<div class="stat-value">{stats["total"]}</div>'
            f'<div class="stat-label">Vuorovaikutukset</div></div>',
            unsafe_allow_html=True,
        )
        s2.markdown(
            f'<div class="stat-card stat-good">'
            f'<div class="stat-value">{stats["good"]}</div>'
            f'<div class="stat-label">Hyvät vastaukset</div></div>',
            unsafe_allow_html=True,
        )
        s3.markdown(
            f'<div class="stat-card stat-bad">'
            f'<div class="stat-value">{stats["bad"]}</div>'
            f'<div class="stat-label">Huonot vastaukset</div></div>',
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.error(f"Virhe tilastojen haussa: {e}")


# ═══════════════════════════════════════════════════════════════
# 1.5. API-AVAIN
# ═══════════════════════════════════════════════════════════════
elif page == "🔑 API-avain":
    st.markdown("## 🔑 Varajärjestelmän API-avain")
    st.markdown("Gemini API avain vaaditaan vain siinä tapauksessa, mikäli lokaali ympäristö ei ole saavutettavissa.")
    st.markdown("Gemini API avaimen voi generoida itselleen osoitteesta: https://ai.google.dev/gemini-api/docs/api-key")
    
    if not available_models:
        st.warning("Lokaalia Ollama-järjestelmää ei havaittu. Vaihto Gemini 2.5 Flash -pilvimalliin suoritettu automaattisesti. Tarvitset API-avaimen käyttääksesi sovellusta.")
    
    current_api_key = os.getenv("GEMINI_API_KEY", "")
    
    with st.form("gemini_api_form"):
        st.markdown("Syötä Google Gemini API -avain jatkaaksesi agenttien käyttöä.")
        api_key_input = st.text_input("Gemini API -avain", value=current_api_key, type="password")
        submit_btn = st.form_submit_button("💾 Tallenna avain (.env)")
        
        if submit_btn:
            if api_key_input:
                dotenv_path = Path(".env")
                dotenv_path.touch(exist_ok=True) # Varmistaa että tiedosto luodaan jos puuttuu
                dotenv.set_key(dotenv_path, "GEMINI_API_KEY", api_key_input)
                os.environ["GEMINI_API_KEY"] = api_key_input
                import agents.shared.config as config_module
                config_module.CONFIG.gemini_api_key = api_key_input
                get_agents.clear() # Pakota agentit uudelleenrakentumaan (poistaa feikkiavaimen)
                st.success("API-avain tallennettu onnistuneesti! Voit nyt siirtyä lukemaan dataa tai keskustelemaan agentin kanssa.")
            else:
                st.error("API-avain ei voi olla tyhjä.")


# ═══════════════════════════════════════════════════════════════
# 2. AGENTTICHAT
# ═══════════════════════════════════════════════════════════════
elif page == "💬 Agenttichat":
    st.markdown("## 💬 Keskustele Agentin kanssa")

    # --- Pikavalinnat (kiinteä yläpalkki) ---
    st.markdown('<div class="quick-actions-label">💡 Pikavalinnat</div>', unsafe_allow_html=True)
    
    # Rivi 1
    qa_col1 = st.columns(4)
    button_query = None

    if qa_col1[0].button("📊 Mitä dataa on?", key="qa_data", width='stretch'):
        button_query = "Tutki mitä tauluja ja dataa tietokannassa on saatavilla ja esittele ne lyhyesti."
    
    if qa_col1[1].button("🗺️ Kärryliike (Heatmap)", key="qa_vis", width='stretch'):
        button_query = "Visualisoi ostoskärryjen liikkeet kaupan pohjapiirrokselle  heatmappina 2019-12-24 päivän osalta."
    
    if qa_col1[2].button("🎻 Viipymäjakauma", key="qa_violin", width='stretch'):
        button_query = "Piirrä violin plot osastojen viipymäajoista taulusta. Näytä tilastolaatikot."

    if qa_col1[3].button("📈 Aikasarja-analyysi", key="qa_grouped", width='stretch'):
        button_query = "Piirrä ryhmitelty pylväskaavio osastojen vietetystä ajasta kuukausittain."

    # Rivi 2
    qa_col2 = st.columns(4)
    
    if qa_col2[0].button("📋 Osastovertailu", key="qa_bar", width='stretch'):
        button_query = "Vertaile osastoja niiden kokonaiskäyntimäärien perusteella pylväskaaviolla."

    if qa_col2[1].button("📈 Yleinen yhteenveto", key="qa_analysis", width='stretch'):
        button_query = "Tee lyhyt yhteenveto datan sisällöstä: rivimäärät, aikaväli ja tärkeimmät havainnot."

    if qa_col2[2].button("🌀 Päivitä muisti", key="qa_refresh", width='stretch'):
        button_query = "Päivitä tietokannan muistisi, tarkista uudet taulut."

    if qa_col2[3].button("🗑️ Nollaa chat", key="qa_reset", width='stretch'):
        st.session_state.messages = []
        import uuid
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.caption(f"Aktiivinen keskustelu: `{st.session_state.thread_id[:12]}…`")

    # --- Apufunktio: visualisointien näyttö viestin sisällöstä ---
    def _render_inline_visuals(content: str):
        """Etsii tiedostopolut vastauksesta ja näyttää kuvat/plotit suoraan chatissa."""
        # Etsii Windows-polut (C:\...) ja Unix-polut (/...) ja suhteelliset polut (data/...)
        potential_paths = re.findall(
            r'([A-Za-z]:[\\\/][^\s\)\]\!\,\"\'>]+|'     # C:\path\to\file tai C:/path/to/file
            r'(?<![<\(])\/[^\s\)\]\!\,\"\'>]+|'           # /absolute/path
            r'data[\\\/]processed[\\\/]plots[\\\/][^\s\)\]\!\,\"\'>]+)',  # suhteellinen polku
            content,
        )
        shown = set()
        for p in potential_paths:
            # Siivoa välimerkit lopusta
            p_clean = p.rstrip(".,;:!?\"'`)]}>")
            # Normalisoi polku
            p_norm = p_clean.replace("/", os.sep).replace("\\", os.sep)

            if p_norm in shown:
                continue

            if os.path.exists(p_norm):
                shown.add(p_norm)
                if p_norm.lower().endswith(".png"):
                    st.image(p_norm, caption="Agentin luoma visualisointi", width='stretch')
                elif p_norm.lower().endswith((".jpg", ".jpeg")):
                    st.image(p_norm, caption="Agentin luoma visualisointi", width='stretch')
                elif p_norm.lower().endswith(".json"):
                    try:
                        with open(p_norm, "r") as f:
                            fig_json = json.load(f)
                            st.plotly_chart(fig_json, width='stretch')
                    except Exception as e:
                        st.error(f"Virhe Plotly-kuvaajan latauksessa: {e}")

    # --- Chat-viestit (natiivi st.chat_message) ---
    for i, msg in enumerate(st.session_state.messages):
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])
            if msg["role"] != "user":
                _render_inline_visuals(msg["content"])

    # --- Käyttäjän syöte (st.chat_input) ---
    user_input = st.chat_input("Kirjoita kysymys tästä...")
    final_input = user_input or button_query

    if final_input:
        # Lisätään käyttäjän viesti ja näytetään se heti
        st.session_state.messages.append({"role": "user", "content": final_input})
        with st.chat_message("user"):
            st.markdown(final_input)

        # Haetaan vastaus agentilta — visuaalinen pipeline-seuranta
        with st.chat_message("assistant"):
            # Agentti-ikonit ja nimet pipelinen otsikkoon
            AGENT_ICONS = {
                "orchestrator": ("🎯", "Orkestraattori", CONFIG.orchestrator_model),
                "schema": ("🗄️", "Skeema-agentti", CONFIG.schema_model),
                "analytics": ("📊", "Analytiikka-agentti", CONFIG.analytics_model),
                "plotter": ("🎨", "Visualisointiagentti", CONFIG.plotter_model),
            }

            with st.status("🎯 Agentti-pipeline käynnistyy...", expanded=True) as status:
                try:
                    step_counter = [0]

                    def update_status(event_type, agent_name, detail):
                        step_counter[0] += 1
                        step_count = step_counter[0]

                        icon, name, model = AGENT_ICONS.get(
                            agent_name, ("🔧", agent_name or "Järjestelmä", "")
                        )

                        if event_type == "agent_start":
                            status.update(label=f"{icon} {name} työskentelee...")
                            status.write(
                                f"**Vaihe {step_count}** · {detail}"
                            )
                        elif event_type == "thinking":
                            status.write(f"&nbsp;&nbsp;&nbsp;&nbsp;🤔 {detail}")
                        elif event_type == "tool_call":
                            status.write(f"&nbsp;&nbsp;&nbsp;&nbsp;{detail}")
                        elif event_type == "tool_result":
                            status.write(f"&nbsp;&nbsp;&nbsp;&nbsp;{detail}")
                        elif event_type == "agent_delegated":
                            d_icon, d_name, d_model = AGENT_ICONS.get(
                                agent_name, ("🔧", agent_name, "")
                            )
                            status.update(label=f"{d_icon} {d_name} työskentelee...")
                            status.write(
                                f"**Vaihe {step_count}** · {detail}"
                            )
                        elif event_type == "complete":
                            status.update(
                                label="✅ Vastaus valmis!",
                                state="complete",
                                expanded=False,
                            )

                    answer, interaction_id = orch.process_request(
                        final_input,
                        thread_id=st.session_state.thread_id,
                        status_callback=update_status,
                    )

                except Exception as e:
                    answer = f"⚠️ Agentti kohtasi virheen: {e}"
                    interaction_id = None
                    status.update(label="❌ Virhe prosessoinnissa", state="error")

            st.markdown(answer)
            _render_inline_visuals(answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "id": interaction_id}
        )
        st.rerun()

    # --- Palaute viimeisimpään viestiin ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        last_bot_msg = st.session_state.messages[-1]
        if last_bot_msg.get("id"):
            st.markdown("---")
            fb_cols = st.columns([0.5, 0.5, 0.5, 4])
            fb_cols[0].markdown(
                '<span style="font-size:0.82rem; color:#64748B; line-height:2.4rem;">Oliko vastaus hyödyllinen?</span>',
                unsafe_allow_html=True,
            )
            if fb_cols[1].button("👍", key="fb_good"):
                analytics_agent.save_feedback(last_bot_msg["id"], "good")
                st.toast("✅ Palaute tallennettu — kiitos!", icon="👍")
            if fb_cols[2].button("👎", key="fb_bad"):
                analytics_agent.save_feedback(last_bot_msg["id"], "bad")
                st.toast("📝 Palaute tallennettu — parannetaan!", icon="👎")


# ═══════════════════════════════════════════════════════════════
# 3. DATATUTKIMUS
# ═══════════════════════════════════════════════════════════════
elif page == "📊 Datatutkimus":
    st.markdown("## 📊 Tietokannan rakenne ja selaus")

    try:
        schema_text = schema_agent.summary(refresh=False)
        with st.expander("🗄️ Tietokannan skeema", expanded=True):
            st.code(schema_text, language="sql")

        st.markdown("### 🔍 Selaa taulujen sisältöä")
        import duckdb
        conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
        tables = conn.execute(
            "SELECT table_schema || '.' || table_name "
            "FROM information_schema.tables "
            "WHERE table_schema NOT IN ('information_schema', 'pg_catalog')"
        ).fetchall()
        tables = [t[0] for t in tables]
        conn.close()

        selected_table = st.selectbox("Valitse taulu", tables)
        if selected_table:
            conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
            df = conn.execute(f"SELECT * FROM {selected_table} LIMIT 100").fetchdf()
            conn.close()

            row_label = f"Näytetään **{len(df)}** ensimmäistä riviä taulusta `{selected_table}`"
            st.caption(row_label)
            st.dataframe(df, width='stretch')
    except Exception as e:
        st.error(f"Virhe datan selaamisessa: {e}")

    st.markdown("---")
    st.markdown("### ✍️ Suorita oma SQL-kysely")
    
    with st.expander("💡 Esimerkkikyselyjä (kopioi tästä)"):
        st.markdown("""
        **1. Datan perushaku (10 ensimmäistä riviä)**
        ```sql
        SELECT * FROM main.bronze_csv_data LIMIT 10;
        ```
        **2. Datarivien määrä ja aikaväli**
        ```sql
        SELECT 
            COUNT(*) as havaintojen_maara, 
            MIN(timestamp) as ensimmainen, 
            MAX(timestamp) as viimeisin 
        FROM main.bronze_csv_data;
        ```
        **3. Havaintojen määrä per ostoskärry (node_id)**
        ```sql
        SELECT node_id, count(*) as havaintoja 
        FROM main.bronze_csv_data
        GROUP BY node_id 
        ORDER BY havaintoja DESC;
        ```
        """)

    # SQL Input
    user_query = st.text_area("SQL-kysely", height=150, placeholder="Kirjoita SQL-kyselysi tähän ja paina 'Suorita'...")
    
    # Rivirajoitin asetus
    use_limit = st.checkbox("Käytä automaattista rivirajoitinta (LIMIT 10000)", value=True, help="Estää selaimen kaatumisen liian suurien tulosten latautuessa. Ota pois päältä jos todella tarvitset yli 10 000 riviä alas.")

    if st.button("▶️ Suorita kysely", type="primary"):
        if not user_query.strip():
            st.warning("Syötä ensin kysely tekstikenttään.")
        else:
            final_query = user_query.strip()
            # Jos valintaruutu on ruksattu ja kysely ei sisällä jo validia LIMIT sanaa
            if use_limit and not re.search(r'\blimit\s+\d+', final_query, re.IGNORECASE):
                final_query = final_query.rstrip(";") + " LIMIT 10000;"

            try:
                import duckdb
                # read_only on äärimmäisen tärkeä käyttäjien vapaissa hauissa
                conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
                res_df = conn.execute(final_query).fetchdf()
                conn.close()
                
                if res_df.empty:
                    st.info("Kysely suoritettiin onnistuneesti, mutta se ei palauttanut rivejä.")
                else:
                    st.success(f"Kysely valmis! Palautettiin {len(res_df)} riviä.")
                    st.dataframe(res_df, width='stretch')
                    
            except Exception as e:
                st.error(f"Virhe kyselyn suorituksessa:\\n\\n{e}")


# ═══════════════════════════════════════════════════════════════
# 4. VISUALISOINNIT
# ═══════════════════════════════════════════════════════════════
elif page == "🖼️ Visualisoinnit":
    st.markdown("## 🖼️ Generoidut visualisoinnit")

    plot_dir = Path("data/processed/plots")
    if plot_dir.exists():
        files = sorted(list(plot_dir.glob("*.*")), key=os.path.getmtime, reverse=True)
        image_files = [f for f in files if f.suffix in (".png", ".json")]

        if not image_files:
            st.info("Ei vielä visualisointeja. Pyydä agentilta luomaan visualisointi chattisivulla!")
        else:
            st.caption(f"{len(image_files)} visualisointia löydetty")

            # Näytetään 2 sarakkeessa
            col_a, col_b = st.columns(2)
            for idx, f in enumerate(image_files):
                target_col = col_a if idx % 2 == 0 else col_b
                with target_col:
                    st.markdown('<div class="vis-card">', unsafe_allow_html=True)
                    if f.suffix == ".png":
                        st.image(str(f), caption=f.name, width='stretch')
                    elif f.suffix == ".json":
                        try:
                            with open(f, "r") as json_f:
                                fig_json = json.load(json_f)
                                st.plotly_chart(fig_json, width='stretch')
                                st.caption(f.name)
                        except Exception:
                            st.warning(f"Ei voitu ladata: {f.name}")
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📁 Visualisointikansiota (`data/processed/plots/`) ei vielä löydy.")


# ═══════════════════════════════════════════════════════════════
# 5. DASHBOARDIT
# ═══════════════════════════════════════════════════════════════
elif page == "📈 Liiketoiminta":
    from dashboards.liiketoiminta import render as render_liiketoiminta
    render_liiketoiminta()

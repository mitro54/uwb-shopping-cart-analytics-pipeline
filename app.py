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

# --- Premium CSS-tyylittely ---
def load_css(file_name):
    with open(file_name, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")


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

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigointi",
    ["🏠 Etusivu", "💬 Agenttichat", "📊 Tietokantakyselyt", "🖼️ Generoidut kuvaajat", "📈 Liiketoiminta Dashboard", "🗺️ Myymäläanalytiikka"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

st.sidebar.markdown("---")


# --- Myymäläanalytiikan asetukset (jos sivu valittu) ---
if page == "🗺️ Myymäläanalytiikka":
    import duckdb
    with st.sidebar:
        st.markdown('<div class="section-header">⚙️ Visualisointiasetukset</div>', unsafe_allow_html=True)
        
        st.session_state.vis_mode = st.selectbox(
            "Analyysityyppi",
            ["🔥 Lämpökartta (Heatmap)", "📍 Pysähdyspaikat (Dwell)", "➿ Asiakasreitti (Route)"],
            key="vis_mode_select"
        )

        st.session_state.show_zones = st.checkbox("Näytä osastot", value=True, key="show_zones_check")
        
        st.session_state.selected_date = st.date_input("Valitse päivämäärä", value=pd.to_datetime("2019-12-24"), key="date_input")
        date_str = st.session_state.selected_date.strftime("%Y-%m-%d")

        st.session_state.sql_query = ""
        st.session_state.plot_type = "heatmap"
        st.session_state.title = f"Visualisointi - {date_str}"

        if st.session_state.vis_mode == "🔥 Lämpökartta (Heatmap)":
            st.session_state.plot_type = "heatmap"
            st.session_state.sql_query = f"SELECT x, y FROM main.silver_positions WHERE CAST(aika AS DATE) = '{date_str}'"
            st.session_state.title = f"Asiakasvirrat - {date_str}"

        elif st.session_state.vis_mode == "📍 Pysähdyspaikat (Dwell)":
            st.session_state.plot_type = "dwell"
            st.session_state.sql_query = f"SELECT grid_x as x, grid_y as y, kokonaisviipyma_s as dwell_time FROM main.gold_koordinaatit WHERE kokonaisviipyma_s > 10"
            st.session_state.title = f"Pysähdykset ja viipymä"

        elif st.session_state.vis_mode == "➿ Asiakasreitti (Route)":
            st.session_state.plot_type = "route"
            conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
            nodes = conn.execute(f"SELECT DISTINCT node_id FROM main.silver_positions WHERE CAST(aika AS DATE) = '{date_str}'").df()
            if not nodes.empty:
                st.session_state.selected_node = st.selectbox("Valitse ostoskärry (node_id)", nodes["node_id"].tolist(), key="node_select")
                sessions = conn.execute(f"SELECT DISTINCT full_session_id FROM main.silver_positions WHERE node_id = '{st.session_state.selected_node}' AND CAST(aika AS DATE) = '{date_str}'").df()
                if not sessions.empty:
                    st.session_state.selected_session = st.selectbox("Valitse sessio", sessions["full_session_id"].tolist(), key="session_select")
                    st.session_state.sql_query = f"SELECT x, y FROM main.silver_positions WHERE node_id = '{st.session_state.selected_node}' AND full_session_id = '{st.session_state.selected_session}' ORDER BY aika"
                    st.session_state.title = f"Reitti: Kärry {st.session_state.selected_node} (Sessio {st.session_state.selected_session[:8]}...)"
                else:
                    st.sidebar.warning("Ei sessioita valittuna päivänä.")
            else:
                st.sidebar.warning("Ei dataa valittuna päivänä.")
            conn.close()

        st.session_state.alpha = st.slider("Peittävyys (Alpha)", 0.1, 1.0, 0.6, key="alpha_slider")
        st.session_state.generate_btn = st.button("🚀 Generoi visualisointi", type="primary", key="gen_btn")
        st.sidebar.markdown("---")


# --- Mallivalikot sivupalkissa ---
st.sidebar.markdown('<div class="section-header">🤖 LLM-mallit</div>', unsafe_allow_html=True)

st.sidebar.markdown("HUOM! Agentteja suositellaan ajamaan lokaalisti Ollamaa hyödyntäen. Mallivalinnat vaikuttavat agenttien toimintaan välittömästi.")

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


# --- Agentchatti ---
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
# 3. TIETOKANTAKYSELYT
# ═══════════════════════════════════════════════════════════════
elif page == "📊 Tietokantakyselyt":
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
# 4. GENEROIDUT KUVAAJAT
# ═══════════════════════════════════════════════════════════════
elif page == "🖼️ Generoidut kuvaajat":
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
# 4.5. MYYMÄLÄANALYTIIKKA
# ═══════════════════════════════════════════════════════════════
elif page == "🗺️ Myymäläanalytiikka":
    st.markdown("## 🗺️ Myymälän tilallinen analytiikka")
    st.markdown("Tällä sivulla voit luoda mukautettuja visualisointeja myymälän pohjapiirroksen päälle.")

    from agents.shared.tools.floorplan_tools import plot_on_floorplan

    # Visualisoinnin generointi (käyttää session_staten arvoja jotka asetettiin sivupalkissa)
    if st.session_state.get("generate_btn"):
        sql_query = st.session_state.get("sql_query")
        if sql_query:
            with st.spinner("Luodaan visualisointia..."):
                try:
                    result_msg = plot_on_floorplan.invoke({
                        "sql": sql_query,
                        "title": st.session_state.get("title", "Visualisointi"),
                        "plot_type": st.session_state.get("plot_type", "heatmap"),
                        "alpha": st.session_state.get("alpha", 0.6),
                        "show_zones": st.session_state.get("show_zones_check", True)
                    })
                    
                    if "luotu:" in result_msg:
                        path_part = result_msg.split("luotu:")[1].strip()
                        if os.path.exists(path_part):
                            st.success("Visualisointi valmis!")
                            st.image(path_part, use_column_width=True)
                            
                            with open(path_part, "rb") as file:
                                st.download_button(
                                    label="📥 Lataa kuva",
                                    data=file,
                                    file_name=os.path.basename(path_part),
                                    mime="image/png"
                                )
                        else:
                            st.error(f"Tiedostoa ei löytynyt: {path_part}")
                    else:
                        st.warning(result_msg)
                except Exception as e:
                    st.error(f"Virhe generoinnissa: {e}")
        else:
            st.error("SQL-kyselyä ei voitu muodostaa. Tarkista suodattimet sivupalkista.")
    else:
        st.info("Valitse asetukset sivupalkista ja paina 'Generoi visualisointi' nähdäksesi tulokset.")


# ═══════════════════════════════════════════════════════════════
# 5. DASHBOARDIT
# ═══════════════════════════════════════════════════════════════
elif page == "📈 Liiketoiminta Dashboard":
    from dashboards.liiketoiminta import render as render_liiketoiminta
    render_liiketoiminta()

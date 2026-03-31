import streamlit as st
import pandas as pd
from pathlib import Path
from dataclasses import replace
import os
import json
import re
import requests
import plotly.io as pio

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
st.markdown("""
<style>
/* ===== Google Fonts ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ===== Yleiset ===== */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* ===== Sivupalkki ===== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] div {
    color: #E2E8F0 !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    color: #38BDF8 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(148, 163, 184, 0.2);
}

/* ===== Hero-osio ===== */
.hero-container {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0D9488 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
    color: white;
    position: relative;
    overflow: hidden;
}
.hero-container::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(56, 189, 248, 0.15) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 0.5rem;
    color: white !important;
}
.hero-subtitle {
    font-size: 1.15rem;
    font-weight: 300;
    color: #94A3B8;
    margin-bottom: 0;
}

/* ===== Agentti-kortit ===== */
.agent-card {
    background: rgba(30, 41, 59, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 12px;
    padding: 1.2rem 1rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    height: 100%;
}
.agent-card:hover {
    border-color: rgba(56, 189, 248, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}
.agent-card .agent-icon {
    font-size: 1.6rem;
    margin-bottom: 0.4rem;
}
.agent-card .agent-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: #F1F5F9;
    margin-bottom: 0.2rem;
}
.agent-card .agent-role {
    font-size: 0.78rem;
    color: #94A3B8;
    margin-bottom: 0.6rem;
    line-height: 1.3;
}
.agent-card .model-tag {
    display: inline-block;
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(13, 148, 136, 0.2));
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38BDF8;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-family: 'Inter', monospace;
    letter-spacing: 0.02em;
}

/* ===== Stat-kortit ===== */
.stat-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
}
.stat-card .stat-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #F1F5F9;
    letter-spacing: -0.02em;
}
.stat-card .stat-label {
    font-size: 0.82rem;
    color: #94A3B8;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.stat-card.stat-good { border-left: 3px solid #10B981; }
.stat-card.stat-bad { border-left: 3px solid #F59E0B; }
.stat-card.stat-total { border-left: 3px solid #38BDF8; }

/* ===== Ominaisuuskortit ===== */
.feature-card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 12px;
    padding: 1.3rem;
    transition: all 0.25s ease;
}
.feature-card:hover {
    background: rgba(30, 41, 59, 0.7);
    border-color: rgba(56, 189, 248, 0.3);
}
.feature-card .feature-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
}
.feature-card .feature-title {
    font-weight: 600;
    font-size: 0.95rem;
    color: #F1F5F9;
    margin-bottom: 0.3rem;
}
.feature-card .feature-desc {
    font-size: 0.82rem;
    color: #94A3B8;
    line-height: 1.4;
}

/* ===== Pikavalinnat ===== */
.quick-actions-bar {
    background: rgba(30, 41, 59, 0.5);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin-bottom: 1rem;
}
.quick-actions-label {
    font-size: 0.75rem;
    color: #64748B;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.3rem;
}

/* Pienemmät pikavalinnapainikkeet */
.quick-actions-bar .stButton > button {
    font-size: 0.8rem !important;
    padding: 0.3rem 0.8rem !important;
    border-radius: 20px !important;
    background: rgba(56, 189, 248, 0.1) !important;
    border: 1px solid rgba(56, 189, 248, 0.25) !important;
    color: #38BDF8 !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.quick-actions-bar .stButton > button:hover {
    background: rgba(56, 189, 248, 0.2) !important;
    border-color: rgba(56, 189, 248, 0.5) !important;
    transform: translateY(-1px) !important;
}

/* ===== Chat-bubblat ===== */
.stChatMessage {
    border-radius: 12px !important;
    margin-bottom: 0.5rem;
}

/* ===== Section header ===== */
.section-header {
    font-size: 0.82rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(148, 163, 184, 0.15);
}

/* ===== Sidebar model tags ===== */
.sidebar-model-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.3rem 0;
    font-size: 0.82rem;
}
.sidebar-model-name {
    color: #94A3B8;
    font-weight: 400;
}
.sidebar-model-value {
    color: #38BDF8;
    font-weight: 600;
    font-size: 0.78rem;
    background: rgba(56, 189, 248, 0.1);
    padding: 0.15rem 0.5rem;
    border-radius: 12px;
}

/* ===== Palaute-painikkeet ===== */
.feedback-section {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0;
}

/* ===== Pohjapiirros hero-kuva ===== */
.floorplan-container {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.15);
    margin-top: 1rem;
}
.floorplan-container img {
    width: 100%;
    display: block;
}
.floorplan-caption {
    text-align: center;
    padding: 0.5rem;
    background: rgba(30, 41, 59, 0.6);
    font-size: 0.78rem;
    color: #94A3B8;
}

/* ===== Vis gallery ===== */
.vis-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    transition: all 0.25s ease;
}
.vis-card:hover {
    border-color: rgba(56, 189, 248, 0.3);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

/* Piilota Streamlitin yläosa */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

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
        st.session_state[ss_key] = getattr(CONFIG, config_attr)

# Päivitetään globaali CONFIG session state -valinnoilla
_effective_config = replace(
    CONFIG,
    orchestrator_model=st.session_state.model_orchestrator,
    analytics_model=st.session_state.model_analytics,
    plotter_model=st.session_state.model_plotter,
    schema_model=st.session_state.model_schema,
    embedding_model=st.session_state.model_embedding,
)
config_module.CONFIG = _effective_config

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
        "model": _effective_config.orchestrator_model,
    },
    {
        "icon": "📊",
        "name": "Analytiikka",
        "role": "SQL-kyselyt ja data-analyysi",
        "model": _effective_config.analytics_model,
    },
    {
        "icon": "🎨",
        "name": "Visualisointi",
        "role": "Kaaviot, heatmapit ja plotit",
        "model": _effective_config.plotter_model,
    },
    {
        "icon": "🗄️",
        "name": "Skeema",
        "role": "Tietokannan rakenteen hallinta",
        "model": _effective_config.schema_model,
    },
    {
        "icon": "📎",
        "name": "Embedding",
        "role": "Semanttinen haku ja muisti",
        "model": _effective_config.embedding_model,
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
    ["🏠 Etusivu", "💬 Agenttichat", "📊 Datatutkimus", "🖼️ Visualisoinnit"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# --- Mallivalikot sivupalkissa ---
st.sidebar.markdown('<div class="section-header">🤖 LLM-mallit</div>', unsafe_allow_html=True)

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
    st.sidebar.warning("⚠️ Ollama API ei vastaa — kirjoita mallin nimi manuaalisesti.")
    for ss_key, config_attr, label in MODEL_ROLES:
        st.sidebar.text_input(
            label,
            value=st.session_state[ss_key],
            key=f"_txt_{ss_key}",
            on_change=_apply_model_selection,
            args=(ss_key, f"_txt_{ss_key}"),
        )

st.sidebar.markdown("---")

if st.sidebar.button("🗑️ Nollaa keskustelu", use_container_width=True):
    st.session_state.messages = []
    import uuid
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Thread: `{st.session_state.thread_id[:12]}…`")


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
    st.image("image/kauppa.png", use_container_width=True)
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
# 2. AGENTTICHAT
# ═══════════════════════════════════════════════════════════════
elif page == "💬 Agenttichat":
    st.markdown("## 💬 Keskustele Agentin kanssa")

    # --- Pikavalinnat (kiinteä yläpalkki) ---
    st.markdown('<div class="quick-actions-label">💡 Pikavalinnat</div>', unsafe_allow_html=True)
    qa1, qa2, qa3 = st.columns(3)

    button_query = None
    if qa1.button("📊 Mitä dataa on?", key="qa_data", use_container_width=True):
        button_query = (
            "Tutki mitä tauluja ja dataa tietokannassa on saatavilla "
            "ja esittele ne lyhyesti. Kerro myös, mitä analyyseja voisit tehdä tällä datalla."
        )
    if qa2.button("🗺️ Kärryliike kartalla", key="qa_vis", use_container_width=True):
        button_query = (
            "Visualisoi ostoskärryjen liikkeet kaupan pohjapiirrokselle heatmappina. "
            "Valitse mielenkiintoinen ajanjakso datasta ja käytä plot_on_floorplan-työkalua. "
            "Lisää SQL-kyselyyn sopiva aikarajaus ja LIMIT 500000."
        )
    if qa3.button("📈 Data-analyysi", key="qa_analysis", use_container_width=True):
        button_query = (
            "Tee lyhyt yhteenveto datan sisällöstä: kuinka paljon rivejä on, "
            "miltä ajanjaksolta data on, kuinka monta eri ostoskärryä (node_id) "
            "ja mitä ovat tärkeimmät havainnot."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Chat-viestit (natiivi st.chat_message) ---
    for i, msg in enumerate(st.session_state.messages):
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

            # Visualisointien haku viestin sisällöstä
            if msg["role"] != "user":
                content = msg["content"]
                potential_paths = re.findall(
                    r'([a-zA-Z]:\\[^\s\)\!]+|/[^\s\)\!]+|data/processed/plots/[^\s\)\!]+)',
                    content,
                )
                for p in potential_paths:
                    p_clean = p.strip("()[]!")
                    if os.path.exists(p_clean):
                        if p_clean.endswith(".png"):
                            st.image(p_clean, caption="Agentin luoma visualisointi")
                        elif p_clean.endswith(".json"):
                            try:
                                with open(p_clean, "r") as f:
                                    fig_json = json.load(f)
                                    st.plotly_chart(fig_json, use_container_width=True)
                            except Exception as e:
                                st.error(f"Virhe Plotly-kuvaajan latauksessa ({p_clean}): {e}")

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

        st.markdown("### 🔍 Selaa taulun sisältöä")
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
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Virhe datan selaamisessa: {e}")


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
                        st.image(str(f), caption=f.name, use_container_width=True)
                    elif f.suffix == ".json":
                        try:
                            with open(f, "r") as json_f:
                                fig_json = json.load(json_f)
                                st.plotly_chart(fig_json, use_container_width=True)
                                st.caption(f.name)
                        except Exception:
                            st.warning(f"Ei voitu ladata: {f.name}")
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📁 Visualisointikansiota (`data/processed/plots/`) ei vielä löydy.")

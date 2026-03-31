import streamlit as st
from streamlit_chat import message
import pandas as pd
from pathlib import Path
import os
import json
import re
import plotly.io as pio

from agents.orchestrator.agent import OrchestratorAgent
from agents.schema.agent import SchemaAgent
from agents.analytics.agent import AnalyticsAgent
from agents.shared.config import CONFIG

# --- Sivun asetukset ---
st.set_page_config(
    page_title="ByteBuddies UWB Dashboard",
    page_icon="🛒",
    layout="wide"
)

# --- Tyylittely ---
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State alustus ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit_session"

# --- Agentit ---
@st.cache_resource
def get_agents():
    return OrchestratorAgent(), SchemaAgent(), AnalyticsAgent()

orch, schema_agent, analytics_agent = get_agents()

# --- Sivupalkki (Navigaatio) ---
st.sidebar.title("🛒 ByteBuddies")
page = st.sidebar.radio("Navigointi", ["🏠 Etusivu", "💬 Agenttichat", "📊 Datatutkimus", "🖼️ Visualisoinnit"])

if st.sidebar.button("🗑️ Nollaa keskustelu"):
    st.session_state.messages = []
    import uuid
    st.session_state.thread_id = str(uuid.uuid4())
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(f"**Thread ID:** {st.session_state.thread_id}\n\n**Malli (Orkestraattori):** {CONFIG.orchestrator_model}\n\n**Malli (Analytiikka):** {CONFIG.analytics_model}")

# --- 1. ETUSIVU ---
if page == "🏠 Etusivu":
    st.markdown('<h1 class="main-header">ByteBuddies: UWB-Analytiikka</h1>', unsafe_allow_html=True)
    st.write("""
    Tervetuloa ByteBuddies-projektin ohjausnäkymään. Tämä järjestelmä hyödyntää **moniagenttiarkkitehtuuria** 
    sisätilojen ostoskärryliikkeen analysointiin.
    
    ### Järjestelmän kyvyt:
    - **Älykäs keskustelu:** Kysy mitä tahansa UWB-datasta luonnollisella kielellä.
    - **Automaattinen SQL:** Agentit kirjoittavat ja ajavat SQL-kyselyt puolestasi.
    - **Visualisoinnit:** Saat heatmapit ja tilastot suoraan chattiin.
    - **Oppiva muisti:** Järjestelmä muistaa palautteesi ja parantaa vastaustaan.
    """)
    
    # Näytetään jotain nopeita tilastoja DuckDB:stä
    st.subheader("Tietokannan tila")
    try:
        stats = analytics_agent.feedback_store.stats()
        col1, col2, col3 = st.columns(3)
        col1.metric("Vuorovaikutukset", stats['total'])
        col2.metric("Hyvät vastaukset (g)", stats['good'])
        col3.metric("Huonot vastaukset (b)", stats['bad'])
    except Exception as e:
        st.error(f"Virhe tilastojen haussa: {e}")

# --- 2. AGENTTICHAT ---
elif page == "💬 Agenttichat":
    st.header("💬 Keskustele Agentin kanssa")
    
    # Chat-kontti historialle
    chat_container = st.container()

    with chat_container:
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                message(msg["content"], is_user=True, key=f"user_{i}")
            else:
                message(msg["content"], is_user=False, key=f"bot_{i}")
                
                # Etsitään kaikki mahdolliset polut viestistä (tukee Windows- ja Linux-polkuja)
                # Etsitään .png ja .json päätteisiä merkkijonoja
                content = msg["content"]
                potential_paths = re.findall(r'([a-zA-Z]:\\[^\s\)\!]+|/[^\s\)\!]+|data/processed/plots/[^\s\)\!]+)', content)
                
                for p in potential_paths:
                    # Siivotaan polku mahdollisista markdown-merkeistä
                    p_clean = p.strip("()[]!")
                    if os.path.exists(p_clean):
                        if p_clean.endswith(".png"):
                            st.image(p_clean, caption="Agentin luoma visualisointi")
                        elif p_clean.endswith(".json"):
                            try:
                                with open(p_clean, "r") as f:
                                    fig_json = json.load(f)
                                    st.plotly_chart(fig_json, width='stretch')
                            except Exception as e:
                                st.error(f"Virhe Plotly-kuvaajan latauksessa ({p_clean}): {e}")

    # Käyttäjän syöte
    st.write("---")
    st.write("💡 **Pikavalinnat:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    
    button_query = None
    if q_col1.button("📊 Mitä dataa on?", use_container_width=True):
        button_query = "Tervehdys! Tutki mitä tauluja ja dataa tietokannassa on saatavilla ja esittele ne lyhyesti. Kerro myös, mitä analyyseja voisit tehdä tällä datalla."
    if q_col2.button("🔥 Visualisoi jotain", use_container_width=True):
        button_query = "Valitse mielenkiintoinen näkökulma saatavilla olevaan dataan ja luo siitä sopiva visualisointi (esim. heatmap tai aikasarja)."
    if q_col3.button("📈 Data-analyysi", use_container_width=True):
        button_query = "Tee lyhyt yhteenveto datan sisällöstä: kuinka paljon rivejä on, miltä ajanjaksolta data on ja mitä ovat tärkeimmät havainnot."

    user_input = st.chat_input("Kirjoita kysymys tästä...")
    
    final_input = user_input or button_query

    if final_input:
        # Lisätään käyttäjän viesti
        st.session_state.messages.append({"role": "user", "content": final_input})
        
        # Haetaan vastaus agentilta
        with st.status("Agentti valmistautuu...", expanded=True) as status:
            try:
                # 1. Tarkistetaan mallin lataus (Ollama voi olla hidas tässä)
                status.write(f"Ladataan malleja ({CONFIG.orchestrator_model} & {CONFIG.analytics_model})...")
                
                def update_status(text):
                    status.write(f"🔄 {text}")

                # 2. Käsitellään pyyntö
                answer, interaction_id = orch.process_request(
                    final_input, 
                    thread_id=st.session_state.thread_id,
                    status_callback=update_status
                )
                
                status.update(label="Vastaus valmis!", state="complete", expanded=False)
                st.session_state.messages.append({"role": "bot", "content": answer, "id": interaction_id})
                st.rerun()
            except Exception as e:
                status.update(label="Virhe prosessoinnissa", state="error")
                st.error(f"Agentti kohtasi virheen: {e}")

    # Palaute viimeisimpään viestiin (jos se on botilta)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "bot":
        last_bot_msg = st.session_state.messages[-1]
        st.write("Oliko vastaus hyödyllinen?")
        col1, col2, _ = st.columns([1, 1, 5])
        if col1.button("👍 Hyvä", key="good_btn"):
            analytics_agent.save_feedback(last_bot_msg["id"], "good")
            st.success("Palaute tallennettu!")
        if col2.button("👎 Huono", key="bad_btn"):
            feedback_comment = st.text_input("Mitä voisimme parantaa?", key="bad_comment")
            if st.button("Lähetä palaute", key="send_bad"):
                analytics_agent.save_feedback(last_bot_msg["id"], "bad", feedback_comment)
                st.warning("Kiitos, parannamme toimintaamme.")

# --- 3. DATATUTKIMUS ---
elif page == "📊 Datatutkimus":
    st.header("📊 Tietokannan rakenne ja selaus")
    
    try:
        schema_text = schema_agent.summary(refresh=False)
        st.code(schema_text, language="sql")
        
        st.subheader("Selaa taulun sisältöä")
        import duckdb
        conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
        tables = conn.execute("SELECT table_schema || '.' || table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'pg_catalog')").fetchall()
        tables = [t[0] for t in tables]
        conn.close()
        
        selected_table = st.selectbox("Valitse taulu", tables)
        if selected_table:
            conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
            df = conn.execute(f"SELECT * FROM {selected_table} LIMIT 100").fetchdf()
            conn.close()
            st.dataframe(df, width='stretch')
    except Exception as e:
        st.error(f"Virhe datan selaamisessa: {e}")

# --- 4. VISUALISOINNIT ---
elif page == "🖼️ Visualisoinnit":
    st.header("🖼️ Generoidut visualisoinnit")
    plot_dir = Path("data/processed/plots")
    if plot_dir.exists():
        files = sorted(list(plot_dir.glob("*.*")), key=os.path.getmtime, reverse=True)
        # Näytetään sekä .png että .json galleriassa
        for f in files:
            if f.suffix == ".png":
                st.image(str(f), caption=f.name)
                st.markdown("---")
            elif f.suffix == ".json":
                try:
                    with open(f, "r") as json_f:
                        fig_json = json.load(json_f)
                        st.plotly_chart(fig_json, width='stretch')
                        st.caption(f.name)
                        st.markdown("---")
                except:
                    pass
    else:
        st.write("Visualisointikansiota ei vielä löydy.")

import streamlit as st
import requests
from agents.shared.config import CONFIG
import agents.shared.config as config_module

MODEL_ROLES = [
    ("model_orchestrator", "orchestrator_model", "🎯 Orkestraattori"),
    ("model_analytics", "analytics_model", "📊 Analytiikka"),
    ("model_plotter", "plotter_model", "🎨 Visualisointi"),
    ("model_schema", "schema_model", "🗄️ Skeema"),
    ("model_embedding", "embedding_model", "📎 Embedding"),
]

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

def apply_model_selection(ss_key: str, widget_key: str):
    """Päivittää session state -mallinvalinnan ja pakottaa agentit uudelleenluontiin."""
    new_value = st.session_state[widget_key]
    if new_value and new_value != st.session_state.get(ss_key):
        st.session_state[ss_key] = new_value
        # Päivitetään myös globaali CONFIG dynaamisesti
        role_map = {r[0]: r[1] for r in MODEL_ROLES}
        if ss_key in role_map:
            setattr(config_module.CONFIG, role_map[ss_key], new_value)

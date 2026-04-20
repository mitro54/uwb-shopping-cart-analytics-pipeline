"""
UWB-järjestelmän analysointityökalu – ByteBuddies
==================================================
Multipage Streamlit app for UWB system quality analysis.

Run from the project root:
    streamlit run notebooks/overnight_explorer_gold.py
"""

import streamlit as st

st.set_page_config(
    page_title="UWB-analytiikka – ByteBuddies",
    page_icon="📡",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px; padding: 2.5rem 3rem; margin-bottom: 2rem; color: white;
}
.hero h1 { font-size: 2.4rem; font-weight: 700; margin: 0 0 0.5rem 0; }
.hero p  { font-size: 1.1rem; color: #a5b4fc; margin: 0; }
.nav-card {
    background: #1e1b4b; border: 1px solid #3730a3; border-radius: 14px;
    padding: 1.5rem 1.8rem; color: white; margin-bottom: 1rem;
}
.nav-card h3 { font-size: 1.2rem; font-weight: 600; color: #818cf8; margin: 0 0 0.4rem 0; }
.nav-card p  { font-size: 0.9rem; color: #94a3b8; margin: 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>📡 UWB-järjestelmän analytiikka</h1>
    <p>Paikannustarkkuuden ja verkon laadun seuranta – ByteBuddies / UWB-toimittajan näkymä</p>
</div>
""", unsafe_allow_html=True)

st.markdown("Valitse analyysi vasemmalta sivupalkista:")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="nav-card">
        <h3>🎯 Paikannustarkkuus</h3>
        <p>Yöaikaiset tarkkuusmittarit paikallaan olleille laitteille.
        CEP50/68/95, drift, jitter ja sijaintipilvi pohjapiirustuksessa.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="nav-card">
        <h3>📶 Verkon laatu</h3>
        <p>UWB-verkon kattavuus ja signaalin laatu 1×1 m ruudukolla.
        Kattavuusaukkojen tunnistus ja häiriöalueiden kartoitus.</p>
    </div>
    """, unsafe_allow_html=True)

"""
Iiwari UWB – Paikannusyrityksen dashboard
==========================================
Erillinen Streamlit-sovellus paikannustarkkuuden ja verkkolaadun
analysointiin. Käynnistys: streamlit run iiwari.py

Kirjoittaja: ByteBuddies
"""

import streamlit as st

st.set_page_config(
    page_title="Iiwari UWB – Paikannusanalyysi",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.markdown("""
<div style="text-align:center; padding: 1rem 0 0.5rem 0;">
    <span style="font-size: 2.2rem;">📡</span>
    <div style="font-size: 1.3rem; font-weight: 700; letter-spacing: -0.02em; margin-top: 0.3rem;">Iiwari UWB</div>
    <div style="font-size: 0.75rem; color: #64748B; font-weight: 500;">Paikannusanalyysi</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigointi",
    ["🎯 Paikannustarkkuus", "📡 Verkkolaatu"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption("ByteBuddies · Iiwari UWB")

if page == "🎯 Paikannustarkkuus":
    from dashboards.iiwari.paikannustarkkuus import render
    render()

elif page == "📡 Verkkolaatu":
    from dashboards.iiwari.verkkolaatu import render
    render()

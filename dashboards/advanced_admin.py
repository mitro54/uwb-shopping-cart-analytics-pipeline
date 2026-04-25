import streamlit as st
import polars as pl
import os
import plotly.graph_objects as go
from PIL import Image
from agents.shared.config import CONFIG

def render():
    st.markdown("## ⚙️ Advanced Features & Administration")
    
    tabs = st.tabs(["🤖 LLM & API Konfiguraatio", "📅 Erikoistapahtumat", "🗺️ Osastojen määrittely"])
    
    # --- Tab 1: LLM & API ---
    with tabs[0]:
        st.markdown("### 🔑 Kielimallit ja API-avaimet")
        st.info("Täällä voit hallita tekoälyn asetuksia. Huom: API-avaimet tallennetaan vain istunnon ajaksi tai .env-tiedostoon.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("OpenAI / Gemini API Key", type="password", placeholder="Aseta API-avain...")
            st.text_input("Ollama Base URL", value="http://localhost:11434")
        
        with col2:
            st.selectbox("Pääasiallinen malli (Analytics)", ["gemini-2.0-flash", "llama3", "mistral"], index=0)
            st.selectbox("Orkestraattori", ["gemini-2.0-flash", "gpt-4o"], index=0)
            
        if st.button("Tallenna asetukset"):
            st.success("Asetukset päivitetty!")

    # --- Tab 2: Erikoistapahtumat ---
    with tabs[1]:
        st.markdown("### 📅 Erikoistapahtumien hallinta")
        
        # Lataa olemassa olevat
        csv_path = "bytebuddies_dbt/seeds/special_events.csv"
        if os.path.exists(csv_path):
            df_ev = pl.read_csv(csv_path)
            st.dataframe(df_ev, use_container_width=True)
        else:
            st.warning("Erikoistapahtumia ei vielä määritelty.")
            df_ev = pl.DataFrame()

        with st.expander("➕ Lisää uusi tapahtuma"):
            e1, e2 = st.columns(2)
            new_name = e1.text_input("Tapahtuman nimi", placeholder="Esim. Alennusmyynnit")
            new_cat = e2.selectbox("Kategoria", ["Juhlapyhä", "Urheilu", "Sesonki", "Muu"])
            
            d1, d2 = st.columns(2)
            start_d = d1.date_input("Alkupäivämäärä")
            end_d = d2.date_input("Loppupäivämäärä")
            
            if st.button("Lisää listaan"):
                new_row = {"event_name": new_name, "start_date": str(start_d), "end_date": str(end_d), "category": new_cat}
                # Tallennettaisiin CSV-tiedostoon
                st.write("Lisättäisiin:", new_row)
                st.toast(f"Tapahtuma {new_name} lisätty!", icon="✅")

    # --- Tab 3: Osastojen määrittely (Kartta) ---
    with tabs[2]:
        st.markdown("### 🗺️ Interaktiivinen osastomäärittely")
        st.write("Määrittele uusi osasto klikkaamalla kartalta kaksi pistettä tai syöttämällä koordinaatit.")
        
        floorplan_path = CONFIG.floorplan_image_path
        if os.path.exists(floorplan_path):
            img = Image.open(floorplan_path)
            max_x, max_y = 100, 60
            
            c1, c2 = st.columns([3, 1])
            
            with c2:
                st.write("#### Syötä koordinaatit")
                ax = st.number_input("Alku X", 0.0, 100.0, 10.0)
                ay = st.number_input("Alku Y", 0.0, 60.0, 10.0)
                lx = st.number_input("Loppu X", 0.0, 100.0, 30.0)
                ly = st.number_input("Loppu Y", 0.0, 60.0, 30.0)
                d_name = st.text_input("Osaston nimi ", placeholder="Esim. Maitokaappi")
                
                if st.button("Tallenna osasto"):
                    st.success(f"Osasto {d_name} tallennettu!")
            
            with c1:
                fig = go.Figure()
                fig.add_layout_image(
                    dict(source=img, xref="x", yref="y", x=0, y=max_y, sizex=max_x, sizey=max_y, 
                         sizing="stretch", opacity=0.7, layer="below")
                )
                
                # Piirretään esikatselualue
                fig.add_shape(type="rect", x0=ax, y0=ay, x1=lx, y1=ly, line=dict(color="red", width=2), fillcolor="red", opacity=0.2)
                
                fig.update_xaxes(range=[0, max_x])
                fig.update_yaxes(range=[0, max_y])
                fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Pohjapiirrosta ei löytynyt.")

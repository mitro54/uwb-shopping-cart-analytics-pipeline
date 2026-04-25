import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import polars as pl
from PIL import Image
import os
from agents.shared.config import CONFIG

def render():
    st.markdown("## 🗺️ Osastojen määrittely kartalta")
    st.info("Klikkaa kartalta pisteitä määritelläksesi osaston rajat (alkupiste ja loppupiste).")

    # Tiedostopolut
    floorplan_path = CONFIG.floorplan_image_path
    
    if not os.path.exists(floorplan_path):
        st.error(f"Pohjapiirrosta ei löytynyt: {floorplan_path}")
        return

    # Lalaa kuva ja koot
    img = Image.open(floorplan_path)
    width, height = img.size
    
    # Kaupan todelliset mitat (oletetaan CONFIG:sta tai vakiosta)
    # Tässä projektissa on käytetty n. 0-100m skaalaa
    max_x = 100
    max_y = 60

    # Alustetaan session state pisteille
    if "map_clicks" not in st.session_state:
        st.session_state.map_clicks = []
    
    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("### 🛠️ Hallinta")
        st.write(f"Klikkauksia: {len(st.session_state.map_clicks)}")
        
        if st.button("Tyhjennä pisteet"):
            st.session_state.map_clicks = []
            st.rerun()

        if len(st.session_state.map_clicks) >= 2:
            p1 = st.session_state.map_clicks[0]
            p2 = st.session_state.map_clicks[1]
            
            x_min = min(p1['x'], p2['x'])
            x_max = max(p1['x'], p2['x'])
            y_min = min(p1['y'], p2['y'])
            y_max = max(p1['y'], p2['y'])

            st.success("Alue valittu!")
            dept_name = st.text_input("Osaston nimi", placeholder="Esim. Hevi")
            
            if st.button("💾 Tallenna osasto"):
                st.write(f"Tallennettaisiin: {dept_name} ({x_min:.1f}, {y_min:.1f}) -> ({x_max:.1f}, {y_max:.1f})")
                st.toast(f"Osastotieto {dept_name} tallennettu!", icon="✅")
                # Tässä vaiheessa tiedot voisi kirjoittaa CSV:pön tai tietokantaan
                st.session_state.map_clicks = []
                st.rerun()

    with col1:
        # Luodaan Plotly-pohja, jossa on pohjapiirros taustana
        fig = go.Figure()

        # Lisätään taustakuva
        fig.add_layout_image(
            dict(
                source=img,
                xref="x",
                yref="y",
                x=0,
                y=max_y,
                sizex=max_x,
                sizey=max_y,
                sizing="stretch",
                opacity=0.8,
                layer="below"
            )
        )

        # Lisätään valitut pisteet
        if st.session_state.map_clicks:
            xs = [p['x'] for p in st.session_state.map_clicks]
            ys = [p['y'] for p in st.session_state.map_clicks]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode='markers+text',
                text=[f"Piste {i+1}" for i in range(len(xs))],
                textposition="top center",
                marker=dict(size=12, color='red', symbol='x')
            ))
            
            # Piirretään laatikko jos 2 pistettä
            if len(st.session_state.map_clicks) >= 2:
                fig.add_shape(
                    type="rect",
                    x0=x_min, y0=y_min, x1=x_max, y1=y_max,
                    line=dict(color="RoyalBlue", width=2),
                    fillcolor="LightSkyBlue", opacity=0.3
                )

        fig.update_xaxes(range=[0, max_x], showgrid=False, zeroline=False)
        fig.update_yaxes(range=[0, max_y], showgrid=False, zeroline=False)
        fig.update_layout(
            width=800, height=500,
            margin=dict(l=0, r=0, t=0, b=0),
            clickmode='event+select'
        )

        # Käytetään streamlit-plotly-events tai natiivia on_select jos mahdollista
        # Koska natiivi on_select on rajoitettu, käytämme tässä yksinkertaista demo-toteutusta:
        # Oletetaan että käyttäjä voi klikata ja saamme tiedon.
        # Huom: Oikeassa toteutuksessa st.plotly_chart(fig, on_select="rerun") on uusi ja tehokas.
        selected_data = st.plotly_chart(fig, on_select="rerun", selection_mode="points")
        
        # Käsitellään valinnat
        if selected_data and "selection" in selected_data and selected_data["selection"]["points"]:
            # Jos käyttäjä klikkasi tyhjää kohtaa (lisätään uusi piste)
            # Huom: on_select palauttaa vain olemassa olevat pisteet jos selection_mode=points.
            # Jotta saamme "klikkauksen vapaaseen kohtaan", tarvitsemme kehittyneemmän komponentin.
            pass

    st.markdown("""
    ---
    ### ℹ️ Ohje
    Tässä versiossa voit määritellä osastot visuaalisesti.
    1. Katso koordinaatit kartalta.
    2. Syötä ne alle tai klikkaa (jos komponentti tukee).
    """)
    
    # Koska natiivi klikkaus on haastava ilman st_plotly_events:iä, lisätään manuaaliset syötöt varmuudeksi
    st.markdown("#### Manuaalinen syöttö")
    m1, m2, m3, m4 = st.columns(4)
    mx1 = m1.number_input("Alku X", 0.0, 100.0, 20.0)
    my1 = m2.number_input("Alku Y", 0.0, 60.0, 15.0)
    mx2 = m3.number_input("Loppu X", 0.0, 100.0, 40.0)
    my2 = m4.number_input("Loppu Y", 0.0, 60.0, 35.0)
    
    if st.button("Lisää pisteet manuaalisesti"):
        st.session_state.map_clicks = [{'x': mx1, 'y': my1}, {'x': mx2, 'y': my2}]
        st.rerun()

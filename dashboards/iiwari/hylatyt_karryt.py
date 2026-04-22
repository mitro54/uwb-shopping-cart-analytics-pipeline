"""
Hylätyt kärryt – kauppaan jätetyt kärryt aukioloaikoina
========================================================
Tunnistaa kärryt jotka ovat olleet paikallaan yli 2h päiväaikaan
kaupan sisällä (latausasemat ja sisäänkäyntialue poissuljettu).

Kutsutaan iiwari.py:stä: dashboards.iiwari.hylatyt_karryt.render()
"""

import math
from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH  = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"
IMAGE_PATH   = PROJECT_ROOT / "image" / "kauppa2.png"
MAP_MAX_X, MAP_MAX_Y = 10406, 5220

# Eksluusioalueet
ENTRANCE_EXCL = "NOT (keski_x >= 0 AND keski_x <= 700 AND keski_y >= 800 AND keski_y <= 1600)"

_CSS = """
<style>
.hk-hero {
    background: linear-gradient(135deg, #1a0a00, #3d1a00, #5c2800);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.hk-hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hk-hero p  { font-size: 1rem; color: #fbbf24; margin: 0; }
.hk-metric {
    background: linear-gradient(135deg, #1c0a00, #2d1500);
    border: 1px solid #92400e; border-radius: 14px;
    padding: 1.2rem 1.4rem; text-align: center; color: white;
    transition: transform 0.2s ease;
}
.hk-metric:hover { transform: translateY(-2px); }
.hk-metric .val { font-size: 2.2rem; font-weight: 700; color: #fb923c; }
.hk-metric .lbl { font-size: 0.78rem; color: #94a3b8; margin-top: 0.3rem; font-weight: 500; }
.hk-metric .sub { font-size: 0.7rem; color: #64748b; margin-top: 0.15rem; }
.hk-section {
    font-size: 1.1rem; font-weight: 600; color: var(--text-color, #e2e8f0);
    margin: 1.5rem 0 0.6rem 0; border-left: 4px solid #f97316; padding-left: 0.6rem;
}
</style>
"""

HYLATTY_QUERY = """
WITH per_tunti AS (
    SELECT node_id, CAST(aika AS DATE) AS paiva,
        DATE_TRUNC('hour', aika) AS tunti,
        MEDIAN(x) AS med_x, MEDIAN(y) AS med_y, COUNT(*) AS pings
    FROM silver_positions
    GROUP BY node_id, paiva, tunti
    HAVING COUNT(*) >= 10
),
ikkunat AS (
    SELECT a.node_id, a.paiva, a.tunti AS tunti_alku,
        MAX(SQRT(POWER(b.med_x-a.med_x,2)+POWER(b.med_y-a.med_y,2))) AS spread_cm,
        AVG(b.med_x) AS keski_x,
        AVG(b.med_y) AS keski_y
    FROM per_tunti a
    JOIN per_tunti b ON a.node_id=b.node_id AND a.paiva=b.paiva
        AND b.tunti >= a.tunti AND b.tunti <= a.tunti + INTERVAL 2 HOUR
    GROUP BY a.node_id, a.paiva, a.tunti
    HAVING COUNT(DISTINCT b.tunti) >= 3
       AND MAX(SQRT(POWER(b.med_x-a.med_x,2)+POWER(b.med_y-a.med_y,2))) < 500
),
uniikki AS (
    SELECT *,
        LAG(tunti_alku) OVER (PARTITION BY node_id, paiva ORDER BY tunti_alku) AS prev_t
    FROM ikkunat
    WHERE NOT (keski_x >= 0 AND keski_x <= 700 AND keski_y >= 800 AND keski_y <= 1600)
)
SELECT
    node_id,
    paiva,
    tunti_alku,
    ROUND(keski_x, 0) AS x,
    ROUND(keski_y, 0) AS y,
    ROUND(spread_cm, 0) AS spread_cm
FROM uniikki
WHERE prev_t IS NULL OR tunti_alku > prev_t + INTERVAL 2 HOUR
ORDER BY paiva, tunti_alku
"""


@st.cache_resource(show_spinner=False)
def _get_conn():
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb ei löydy. Aja ensin `dbt run`.")
    st.stop()


@st.cache_data(show_spinner="🛒 Haetaan hylättyjen kärryjen data…", ttl=300)
def _load() -> pl.DataFrame:
    return _get_conn().execute(HYLATTY_QUERY).pl()


@st.cache_resource(show_spinner=False)
def _load_image(path: Path) -> Image.Image:
    return Image.open(path)


def _kpi(col, val, label, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="hk-metric">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="hk-hero">
        <h1>🛒 Hylätyt kärryt</h1>
        <p>Kärryt jotka ovat olleet paikallaan yli 2h aukioloaikoina — latausasemat ja sisäänkäyntialue poissuljettu</p>
    </div>
    """, unsafe_allow_html=True)

    df = _load()
    if df.is_empty():
        st.warning("Ei dataa.")
        st.stop()

    # --- Sidebar filters ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Suodattimet")

    all_nodes = sorted(df["node_id"].unique().to_list())
    sel_node  = st.sidebar.selectbox("📡 Laite (node_id)", ["— Kaikki —"] + all_nodes)

    dt_min = df["paiva"].min()
    dt_max = df["paiva"].max()
    date_range = st.sidebar.date_input(
        "📅 Päivämääräväli", value=(dt_min, dt_max),
        min_value=dt_min, max_value=dt_max,
    )
    if len(date_range) != 2:
        st.info("Valitse alku- ja loppupäivä.")
        st.stop()
    d0, d1 = date_range

    df_f = df.filter((pl.col("paiva") >= d0) & (pl.col("paiva") <= d1))
    if sel_node != "— Kaikki —":
        df_f = df_f.filter(pl.col("node_id") == sel_node)

    if df_f.is_empty():
        st.warning("Ei tapauksia valituilla suodattimilla.")
        st.stop()

    # --- KPIs ---
    st.markdown('<div class="hk-section">📊 Yhteenveto</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, str(len(df_f)), "Tapauksia yhteensä", "≥2h paikallaan")
    _kpi(c2, str(df_f["node_id"].n_unique()), "Laitetta")
    _kpi(c3, str(df_f["paiva"].n_unique()), "Päivää")
    _kpi(c4, f"{df_f['spread_cm'].mean():.0f} cm", "Keskim. spread")

    # --- Floor plan scatter ---
    st.markdown('<div class="hk-section">🗺️ Sijainnit pohjapiirustuksessa</div>', unsafe_allow_html=True)

    fp_fig = go.Figure()
    if IMAGE_PATH.exists():
        fp_fig.add_layout_image(dict(
            source=_load_image(IMAGE_PATH),
            xref="x", yref="y", x=0, y=0,
            sizex=MAP_MAX_X, sizey=MAP_MAX_Y,
            sizing="stretch", opacity=1.0, layer="below",
            xanchor="left", yanchor="top",
        ))

    nodes_in_view = df_f["node_id"].unique().sort().to_list()
    colors = [
        "#f97316","#ef4444","#a855f7","#3b82f6","#10b981",
        "#eab308","#ec4899","#06b6d4","#84cc16","#f43f5e",
    ]
    for i, node in enumerate(nodes_in_view):
        nd = df_f.filter(pl.col("node_id") == node)
        fp_fig.add_trace(go.Scatter(
            x=nd["x"].to_list(),
            y=nd["y"].to_list(),
            mode="markers",
            name=str(node),
            marker=dict(
                size=12, color=colors[i % len(colors)],
                symbol="x", line=dict(width=2),
            ),
            hovertemplate=(
                f"<b>Laite {node}</b><br>"
                "x=%{x:.0f} cm, y=%{y:.0f} cm<br>"
                "<extra></extra>"
            ),
        ))

    fp_fig.update_xaxes(range=[0, MAP_MAX_X], showgrid=False, showticklabels=False)
    fp_fig.update_yaxes(range=[MAP_MAX_Y, 0], showgrid=False, showticklabels=False,
                        scaleanchor="x", scaleratio=1)
    fp_fig.update_layout(
        height=500, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="top", y=-0.02, font=dict(size=11)),
    )
    st.plotly_chart(fp_fig, use_container_width=True)

    # --- Timeline ---
    st.markdown('<div class="hk-section">📅 Tapaukset ajan yli</div>', unsafe_allow_html=True)

    daily = (
        df_f.group_by("paiva")
        .agg(pl.len().alias("n"))
        .sort("paiva")
    )
    fig_time = go.Figure(go.Bar(
        x=daily["paiva"].cast(pl.Utf8).to_list(),
        y=daily["n"].to_list(),
        marker_color="#f97316",
        hovertemplate="<b>%{x}</b><br>Tapauksia: %{y}<extra></extra>",
    ))
    fig_time.update_layout(
        height=260, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Päivämäärä"), yaxis=dict(title="Tapauksia"),
        showlegend=False,
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # --- Per-device bar ---
    st.markdown('<div class="hk-section">📦 Tapaukset laitteittain</div>', unsafe_allow_html=True)

    per_dev = (
        df_f.group_by("node_id")
        .agg(pl.len().alias("n"))
        .sort("n", descending=True)
    )
    fig_dev = go.Figure(go.Bar(
        x=per_dev["node_id"].cast(pl.Utf8).to_list(),
        y=per_dev["n"].to_list(),
        marker_color="#fb923c",
        text=per_dev["n"].to_list(),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Tapauksia: %{y}<extra></extra>",
    ))
    fig_dev.update_layout(
        height=300, margin=dict(l=50, r=20, t=10, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Laite (node_id)", type="category"),
        yaxis=dict(title="Tapauksia"),
        showlegend=False,
    )
    st.plotly_chart(fig_dev, use_container_width=True)

    # --- Hour of day distribution ---
    st.markdown('<div class="hk-section">🕐 Mihin kellonaikaan kärryt hylätään?</div>', unsafe_allow_html=True)

    df_f2 = df_f.with_columns(
        pl.col("tunti_alku").dt.hour().alias("tunti")
    )
    by_hour = (
        df_f2.group_by("tunti")
        .agg(pl.len().alias("n"))
        .sort("tunti")
    )
    fig_h = go.Figure(go.Bar(
        x=[f"{h}:00" for h in by_hour["tunti"].to_list()],
        y=by_hour["n"].to_list(),
        marker_color="#fbbf24",
        hovertemplate="<b>%{x}</b><br>Tapauksia: %{y}<extra></extra>",
    ))
    fig_h.update_layout(
        height=260, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Kellonaika"), yaxis=dict(title="Tapauksia"),
        showlegend=False,
    )
    st.plotly_chart(fig_h, use_container_width=True)

    # --- Raw table ---
    with st.expander("📋 Kaikki tapaukset taulukossa"):
        st.dataframe(
            df_f.sort("paiva", "tunti_alku").to_pandas(),
            use_container_width=True,
            hide_index=True,
        )

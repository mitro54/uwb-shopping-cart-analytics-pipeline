"""
Overnight Cart Activity Explorer
=================================
Standalone Streamlit script for analysing overnight (is_night_time = 1) UWB
cart activity overlaid on the kauppa2.png floor plan.

Charging-station exclusion zones are filtered out so we only see
carts that moved OUTSIDE of the docking areas.

Run from the project root:
    streamlit run scripts/overnight_explorer.py

Author: Antigravity / ByteBuddies
"""

import math
import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Paths – resolve relative to project root (parent of /scripts)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"
IMAGE_PATH = PROJECT_ROOT / "image" / "kauppa2.png"

# ---------------------------------------------------------------------------
# Config constants
# ---------------------------------------------------------------------------
# Coordinate system limits (cm) from silver_device_diagnostics.sql
MAP_MAX_X = 10406
MAP_MAX_Y = 5220

# Charging-station exclusion zones – ignored for overnight activity analysis
CHARGING_STATIONS = [
    {"name": "Latauspiste 1 (Turvaportit)", "x": 100,  "y": 2500, "radius": 400},
    {"name": "Latauspiste 2 (Liukuportaat)", "x": 900, "y": 3600, "radius": 600},
]

# Night-time definition mirrors the dbt SQL:
#   hour < 7  OR  hour > 22  → is_night_time = 1
SHOP_OPEN  = 7
SHOP_CLOSE = 22

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Yöajan aktiivisuus – ByteBuddies",
    page_icon="🌙",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }

.hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    color: white;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hero p  { font-size: 1rem; color: #a5b4fc; margin: 0; }

.metric-card {
    background: #1e1b4b;
    border: 1px solid #3730a3;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    text-align: center;
    color: white;
}
.metric-card .val { font-size: 2rem; font-weight: 700; color: #818cf8; }
.metric-card .lbl { font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem; }

.section-title {
    font-size: 1.1rem; font-weight: 600;
    color: #312e81; margin: 1.2rem 0 0.6rem 0;
    border-left: 4px solid #6366f1; padding-left: 0.6rem;
}

.station-badge {
    display: inline-block;
    background: #fef3c7; color: #92400e;
    border-radius: 8px; padding: 0.15rem 0.6rem;
    font-size: 0.75rem; font-weight: 600; margin: 0.15rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>🌙 Yöajan kärryaktiivisuus</h1>
    <p>Liikkeet kaupan aukioloaikojen ulkopuolella – latausasemien alueet suodatettu pois</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_image(path: Path) -> Image.Image:
    return Image.open(path)


@st.cache_data(show_spinner="🔗 Haetaan dataa DuckDB:stä…")
def fetch_night_data() -> pd.DataFrame:
    """Load all overnight pings from silver_device_diagnostics."""
    if not DUCKDB_PATH.exists():
        st.error(f"DuckDB-tietokantaa ei löydy: {DUCKDB_PATH}\n\nAja ensin `dbt run`.")
        st.stop()

    conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        df = conn.execute("""
            SELECT
                node_id,
                aika,
                CAST(aika AS DATE)           AS paiva,
                EXTRACT('hour' FROM aika)    AS tunti,
                x,
                y,
                q,
                speed_mps,
                is_low_quality,
                is_jitter
            FROM silver_device_diagnostics
            WHERE is_night_time = 1
              AND x IS NOT NULL
              AND y IS NOT NULL
            ORDER BY node_id, aika
        """).fetchdf()
    finally:
        conn.close()

    return df


def is_in_charging_zone(x: float, y: float) -> bool:
    """Return True if the coordinate falls inside any charging station circle."""
    for st_cfg in CHARGING_STATIONS:
        dist = math.sqrt((x - st_cfg["x"]) ** 2 + (y - st_cfg["y"]) ** 2)
        if dist <= st_cfg["radius"]:
            return True
    return False


def filter_outside_stations(df: pd.DataFrame) -> pd.DataFrame:
    """Remove pings that are inside charging-station exclusion zones."""
    mask = ~df.apply(lambda r: is_in_charging_zone(r["x"], r["y"]), axis=1)
    return df[mask].copy()


def build_figure(
    df: pd.DataFrame,
    img: Image.Image,
    color_mode: str = "Ajan mukaan",
    point_size: int = 6,
    point_opacity: float = 0.75,
) -> go.Figure:
    """Overlay scatter points on the floor-plan image using Plotly."""

    img_w, img_h = img.size  # pixel dimensions → aspect ratio

    # We map data coords [0, MAP_MAX_X] × [0, MAP_MAX_Y] to the image.
    # Plotly yref="y" grows upward; image origin is top-left → flip y.
    df = df.copy()
    df["y_plot"] = MAP_MAX_Y - df["y"]   # flip so top of image = y=0 in data

    fig = go.Figure()

    # ── Background image ────────────────────────────────────────────────────
    fig.add_layout_image(
        dict(
            source=img,
            xref="x", yref="y",
            x=0, y=MAP_MAX_Y,
            sizex=MAP_MAX_X, sizey=MAP_MAX_Y,
            sizing="stretch",
            opacity=1.0,
            layer="below",
        )
    )

    # ── Charging station exclusion circles (for reference) ──────────────────
    for cs in CHARGING_STATIONS:
        theta = [i * (360 / 72) for i in range(73)]
        cx, cy = cs["x"], MAP_MAX_Y - cs["y"]
        r = cs["radius"]
        circle_x = [cx + r * math.cos(math.radians(t)) for t in theta]
        circle_y = [cy + r * math.sin(math.radians(t)) for t in theta]
        fig.add_trace(go.Scatter(
            x=circle_x, y=circle_y,
            mode="lines",
            line=dict(color="rgba(251,191,36,0.6)", width=2, dash="dot"),
            fill="toself",
            fillcolor="rgba(251,191,36,0.08)",
            name=cs["name"],
            hoverinfo="name",
            showlegend=True,
        ))

    # ── Scatter: colour coding ───────────────────────────────────────────────
    if color_mode == "Ajan mukaan":
        # Encode time as numeric (minutes from midnight) for continuous colour
        df["color_val"] = df["tunti"]
        color_title = "Tunti (0-23)"
        colorscale = "Viridis"
        marker_color = df["color_val"]
        colorbar = dict(title=color_title, thickness=14, len=0.6)
    elif color_mode == "Kärry (node_id)":
        # Categorical – assign integer index per node_id
        cats = df["node_id"].astype("category")
        df["color_val"] = cats.cat.codes
        colorscale = "Turbo"
        marker_color = df["color_val"]
        colorbar = dict(title="Kärry-indeksi", thickness=14, len=0.6)
    elif color_mode == "Signaalin laatu (q)":
        df["color_val"] = df["q"]
        colorscale = "RdYlGn"
        marker_color = df["color_val"]
        colorbar = dict(title="Q-arvo", thickness=14, len=0.6)
    else:  # Nopeus
        df["color_val"] = df["speed_mps"].clip(0, 3)
        colorscale = "Plasma"
        marker_color = df["color_val"]
        colorbar = dict(title="Nopeus (m/s)", thickness=14, len=0.6)

    hover_text = (
        "Kärry: " + df["node_id"].astype(str) + "<br>"
        + "Aika: " + df["aika"].astype(str) + "<br>"
        + "x=" + df["x"].round(0).astype(int).astype(str)
        + " y=" + df["y"].round(0).astype(int).astype(str) + "<br>"
        + "Q=" + df["q"].astype(str)
        + "  v=" + df["speed_mps"].round(2).astype(str) + " m/s"
    )

    fig.add_trace(go.Scatter(
        x=df["x"],
        y=df["y_plot"],
        mode="markers",
        marker=dict(
            size=point_size,
            color=marker_color,
            colorscale=colorscale,
            opacity=point_opacity,
            colorbar=colorbar,
            line=dict(width=0),
        ),
        text=hover_text,
        hoverinfo="text",
        name="Yöhavainnot",
        showlegend=True,
    ))

    # ── Layout ───────────────────────────────────────────────────────────────
    aspect = MAP_MAX_Y / MAP_MAX_X          # height / width ratio
    plot_h = max(500, int(900 * aspect))

    fig.update_xaxes(
        range=[0, MAP_MAX_X], showgrid=False,
        zeroline=False, showticklabels=False,
    )
    fig.update_yaxes(
        range=[0, MAP_MAX_Y], showgrid=False,
        zeroline=False, showticklabels=False,
        scaleanchor="x", scaleratio=1,
    )
    fig.update_layout(
        height=plot_h,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.02,
            xanchor="left", x=0,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#e2e8f0",
            borderwidth=1,
            font=dict(size=11),
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
raw_df = fetch_night_data()

if raw_df.empty:
    st.warning("🌙 Yöaikaisia havaintoja ei löytynyt tietokannasta. Tarkista että dbt-malli on ajettu.")
    st.stop()

# Exclude charging stations
df_outside = filter_outside_stations(raw_df)

# Parse dates
df_outside["paiva"] = pd.to_datetime(df_outside["paiva"]).dt.date

# ---------------------------------------------------------------------------
# Sidebar – filters
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔍 Suodattimet")

# ── Date picker ─────────────────────────────────────────────────────────────
available_dates = sorted(df_outside["paiva"].unique())
if not available_dates:
    st.sidebar.warning("Ei päiviä saatavilla latausasemien suodatuksen jälkeen.")
    st.stop()

selected_date = st.sidebar.selectbox(
    "📅 Valitse yö (päivämäärä)",
    options=available_dates,
    format_func=lambda d: str(d),
    index=len(available_dates) - 1,
)

# ── Cart picker ─────────────────────────────────────────────────────────────
carts_on_date = sorted(
    df_outside[df_outside["paiva"] == selected_date]["node_id"].unique()
)
all_option = "— Kaikki kärryt —"

selected_cart = st.sidebar.selectbox(
    "🛒 Valitse kärry",
    options=[all_option] + list(carts_on_date),
)

# ── Visual controls ──────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("## 🎨 Visuaalit")

color_mode = st.sidebar.radio(
    "Värikoodaus",
    ["Ajan mukaan", "Kärry (node_id)", "Signaalin laatu (q)", "Nopeus (m/s)"],
    index=0,
)

point_size = st.sidebar.slider("Pisteiden koko", min_value=2, max_value=16, value=6)
point_opacity = st.sidebar.slider("Läpinäkyvyys", min_value=0.1, max_value=1.0, value=0.75, step=0.05)

# ── Info box ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Suodatetut alueet")
for cs in CHARGING_STATIONS:
    st.sidebar.markdown(
        f'<span class="station-badge">🔌 {cs["name"]}</span>',
        unsafe_allow_html=True,
    )
st.sidebar.markdown(
    "<div style='font-size:0.75rem;color:#64748b;margin-top:0.5rem;'>"
    "Latausasemien säde-alueet poistettu analyysista.</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Filter data by selections
# ---------------------------------------------------------------------------
df_filtered = df_outside[df_outside["paiva"] == selected_date].copy()
if selected_cart != all_option:
    df_filtered = df_filtered[df_filtered["node_id"] == selected_cart]

# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f'<div class="metric-card"><div class="val">{len(df_filtered):,}</div>'
        f'<div class="lbl">Havaintoja</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    n_carts = df_filtered["node_id"].nunique()
    st.markdown(
        f'<div class="metric-card"><div class="val">{n_carts}</div>'
        f'<div class="lbl">Kärryjä aktiivisia</div></div>',
        unsafe_allow_html=True,
    )
with col3:
    hour_range = (
        f"{int(df_filtered['tunti'].min())}–{int(df_filtered['tunti'].max())} h"
        if not df_filtered.empty else "–"
    )
    st.markdown(
        f'<div class="metric-card"><div class="val">{hour_range}</div>'
        f'<div class="lbl">Aktiiviset tunnit</div></div>',
        unsafe_allow_html=True,
    )
with col4:
    avg_q = f"{df_filtered['q'].mean():.1f}" if not df_filtered.empty else "–"
    st.markdown(
        f'<div class="metric-card"><div class="val">{avg_q}</div>'
        f'<div class="lbl">Keskimääräinen Q</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Floor-plan map
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">🗺️ Pohjapiirros – yöaktiivisuus</div>', unsafe_allow_html=True)

if df_filtered.empty:
    st.info("💤 Ei havaintoja valituilla suodattimilla.")
else:
    img = load_image(IMAGE_PATH)
    fig = build_figure(df_filtered, img, color_mode, point_size, point_opacity)
    st.plotly_chart(fig, use_container_width=True)

    # ── Hour histogram ───────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⏱️ Aktiivisuus tunneittain</div>', unsafe_allow_html=True)

    hour_counts = (
        df_filtered.groupby("tunti").size().reset_index(name="havaintoja")
    )
    hour_fig = go.Figure(go.Bar(
        x=hour_counts["tunti"],
        y=hour_counts["havaintoja"],
        marker_color="#6366f1",
        text=hour_counts["havaintoja"],
        textposition="outside",
    ))
    hour_fig.update_layout(
        xaxis=dict(title="Tunti (0–23)", tickmode="linear", dtick=1),
        yaxis=dict(title="Havaintojen määrä"),
        height=280,
        margin=dict(l=40, r=20, t=10, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
    )
    # Shade store-open hours for reference
    hour_fig.add_vrect(
        x0=SHOP_OPEN - 0.5, x1=SHOP_CLOSE + 0.5,
        fillcolor="rgba(99,102,241,0.08)",
        layer="below", line_width=0,
        annotation_text="Aukiolo", annotation_position="top left",
        annotation_font_size=11,
    )
    st.plotly_chart(hour_fig, use_container_width=True)

    # ── Data table ───────────────────────────────────────────────────────────
    with st.expander("📋 Raakadata (näkyvillä olevat havainnot)"):
        show_cols = ["node_id", "aika", "tunti", "x", "y", "q", "speed_mps",
                     "is_low_quality", "is_jitter"]
        st.dataframe(
            df_filtered[show_cols].sort_values(["node_id", "aika"]).reset_index(drop=True),
            use_container_width=True,
            height=300,
        )

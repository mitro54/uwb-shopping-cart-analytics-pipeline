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

Memory-optimised version: uses Polars + SQL-side filtering to stay well
within 16 GB RAM.
"""

import math
from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Paths – resolve relative to project root (parent of /scripts)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"
SILVER_PARQUET = PROJECT_ROOT / "data" / "pbi_prototypes" / "silver_device_diagnostics.parquet"
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
# Build SQL WHERE clause fragment that excludes charging-station circles.
# Doing this in SQL avoids loading millions of rows then filtering in Python.
# ---------------------------------------------------------------------------
def _charging_zone_exclusion_sql() -> str:
    """Return a SQL AND clause that excludes all charging station circles."""
    parts = []
    for cs in CHARGING_STATIONS:
        # (x - cx)^2 + (y - cy)^2 > r^2  ← point is OUTSIDE the circle
        r_sq = cs["radius"] ** 2
        parts.append(
            f"(POWER(x - {cs['x']}, 2) + POWER(y - {cs['y']}, 2) > {r_sq})"
        )
    return " AND ".join(parts)


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


@st.cache_resource(show_spinner=False)
def _get_connection():
    """Return a DuckDB connection with silver_device_diagnostics registered from parquet."""
    if SILVER_PARQUET.exists():
        conn = duckdb.connect()
        conn.execute(
            f"CREATE VIEW silver_device_diagnostics AS "
            f"SELECT * FROM read_parquet('{SILVER_PARQUET}')"
        )
        return conn
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("silver_device_diagnostics.parquet eikä dev.duckdb löydy. Aja ensin dbt run.")
    st.stop()


@st.cache_data(show_spinner="📅 Haetaan saatavilla olevat yöt…", ttl=300)
def fetch_available_dates() -> list[str]:
    """Fetch distinct night-start dates (22:00–06:00 Helsinki) outside charging stations."""
    conn = _get_connection()
    exclusion = _charging_zone_exclusion_sql()
    rows = conn.execute(f"""
        WITH tz AS (
            SELECT timezone('Europe/Helsinki', aika::TIMESTAMPTZ) AS aika_hki, x, y
            FROM silver_device_diagnostics
            WHERE is_night_time = 1
              AND x IS NOT NULL AND y IS NOT NULL
              AND x >= 780
              AND {exclusion}
        )
        SELECT
            CAST(
                CASE
                    WHEN EXTRACT('hour' FROM aika_hki) < 7
                    THEN CAST(aika_hki AS DATE) - INTERVAL '1 day'
                    ELSE CAST(aika_hki AS DATE)
                END
            AS DATE) AS night_date
        FROM tz
        GROUP BY night_date
        HAVING COUNT(*) > 500
        ORDER BY night_date
    """).fetchall()
    return [str(r[0])[:10] for r in rows]


@st.cache_data(show_spinner="🔗 Haetaan valitun yön dataa…", ttl=300)
def fetch_night_data_for_date(date_str: str) -> pl.DataFrame:
    """Load one full night (22:00–06:00 Helsinki) for date_str as the night-start date.

    Returns a Polars DataFrame with down-cast dtypes to save memory.
    """
    conn = _get_connection()
    exclusion = _charging_zone_exclusion_sql()

    from datetime import date as _date, timedelta
    next_date_str = str(_date.fromisoformat(str(date_str)[:10]) + timedelta(days=1))

    arrow_table = conn.execute(f"""
        WITH tz AS (
            SELECT
                node_id,
                timezone('Europe/Helsinki', aika::TIMESTAMPTZ) AS aika_hki,
                x, y, q, speed_mps, is_low_quality, is_jitter
            FROM silver_device_diagnostics
            WHERE x IS NOT NULL AND y IS NOT NULL
              AND x >= 500
              AND {exclusion}
        )
        SELECT
            node_id,
            aika_hki                                 AS aika,
            EXTRACT('hour' FROM aika_hki)::INT       AS tunti,
            x, y, q, speed_mps, is_low_quality, is_jitter
        FROM tz
        WHERE
            (CAST(aika_hki AS DATE) = CAST('{date_str}' AS DATE)
             AND EXTRACT('hour' FROM aika_hki) >= 22)
            OR
            (CAST(aika_hki AS DATE) = CAST('{next_date_str}' AS DATE)
             AND EXTRACT('hour' FROM aika_hki) < 7)
        ORDER BY node_id, aika_hki
    """).to_arrow_table()

    # Arrow → Polars (zero-copy) then downcast for minimum footprint
    df = pl.from_arrow(arrow_table)

    # Downcast numeric columns to reduce memory
    df = df.cast({
        "node_id": pl.Int32,
        "tunti": pl.Int16,
        "q": pl.Int16,
        "is_low_quality": pl.Int8,
        "is_jitter": pl.Int8,
        "x": pl.Float32,
        "y": pl.Float32,
        "speed_mps": pl.Float32,
    })

    return df


def build_figure(
    df: pl.DataFrame,
    img: Image.Image,
    color_mode: str = "Ajan mukaan",
    point_size: int = 6,
    point_opacity: float = 0.75,
) -> go.Figure:
    """Overlay scatter points on the floor-plan image using Plotly.

    Converts only the needed columns to Python lists for Plotly –
    avoids materialising a full pandas copy.
    """

    img_w, img_h = img.size  # pixel dimensions → aspect ratio

    # We map data coords [0, MAP_MAX_X] × [0, MAP_MAX_Y] to the image.
    # Plotly yref="y" grows upward; image origin is top-left → flip y.
    x_vals = df["x"].to_list()
    y_vals = (MAP_MAX_Y - df["y"]).to_list()  # flipped

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
        marker_color = df["tunti"].to_list()
        color_title = "Tunti (0-23)"
        colorscale = "Viridis"
    elif color_mode == "Kärry (node_id)":
        # Use native Polars categorical encoding instead of Python lambda (much faster)
        marker_color = df["node_id"].cast(pl.String).cast(pl.Categorical).to_physical().to_list()
        color_title = "Kärry-indeksi"
        colorscale = "Turbo"
    elif color_mode == "Signaalin laatu (q)":
        marker_color = df["q"].to_list()
        color_title = "Q-arvo"
        colorscale = "RdYlGn"
    else:  # Nopeus
        marker_color = df["speed_mps"].clip(0, 3).to_list()
        color_title = "Nopeus (m/s)"
        colorscale = "Plasma"

    colorbar = dict(title=color_title, thickness=14, len=0.6)

    # ── Hover: use customdata instead of pre-building giant string arrays ──
    # customdata columns: [node_id, aika, x, y, q, speed_mps]
    customdata_cols = df.select(
        "node_id",
        pl.col("aika").cast(pl.String).alias("aika_str"),
        pl.col("x").round(0).cast(pl.Int32),
        pl.col("y").round(0).cast(pl.Int32),
        "q",
        pl.col("speed_mps").round(2),
    )
    customdata = customdata_cols.to_numpy()

    hovertemplate = (
        "Kärry: %{customdata[0]}<br>"
        "Aika: %{customdata[1]}<br>"
        "x=%{customdata[2]} y=%{customdata[3]}<br>"
        "Q=%{customdata[4]}  v=%{customdata[5]} m/s"
        "<extra></extra>"
    )

    fig.add_trace(go.Scattergl(
        x=x_vals,
        y=y_vals,
        mode="markers",
        marker=dict(
            size=point_size,
            color=marker_color,
            colorscale=colorscale,
            opacity=point_opacity,
            colorbar=colorbar,
            line=dict(width=0),
        ),
        customdata=customdata,
        hovertemplate=hovertemplate,
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
# Data loading – only fetch the lightweight date list first
# ---------------------------------------------------------------------------
available_dates = fetch_available_dates()

if not available_dates:
    st.warning("🌙 Yöaikaisia havaintoja ei löytynyt tietokannasta. Tarkista että dbt-malli on ajettu.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar – filters
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔍 Suodattimet")

# ── Date picker ─────────────────────────────────────────────────────────────
selected_date = st.sidebar.selectbox(
    "📅 Valitse yö",
    options=available_dates,
    index=len(available_dates) - 1,
)

# ── Load data for the selected date only ────────────────────────────────────
df_day = fetch_night_data_for_date(selected_date)

if df_day.is_empty():
    st.sidebar.warning("Ei havaintoja valitulle yölle.")
    st.stop()

# ── Cart picker – only nodes with >1000 pings this night ────────────────────
cart_counts = df_day.group_by("node_id").len()
carts_on_date = sorted(
    cart_counts.filter(pl.col("len") > 1000)["node_id"].to_list()
)
all_option = "— Kaikki kärryt —"

selected_cart = st.sidebar.selectbox(
    "🛒 Valitse kärry",
    options=[all_option] + list(carts_on_date),
    index=0,
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

# ---------------------------------------------------------------------------
# Filter data by selections
# ---------------------------------------------------------------------------
df_filtered = df_day
if selected_cart != all_option:
    df_filtered = df_filtered.filter(pl.col("node_id") == selected_cart)

# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

n_rows = len(df_filtered)
with col1:
    st.markdown(
        f'<div class="metric-card"><div class="val">{n_rows:,}</div>'
        f'<div class="lbl">Havaintoja</div></div>',
        unsafe_allow_html=True,
    )
with col2:
    n_carts = df_filtered["node_id"].n_unique()
    st.markdown(
        f'<div class="metric-card"><div class="val">{n_carts}</div>'
        f'<div class="lbl">Kärryjä aktiivisia</div></div>',
        unsafe_allow_html=True,
    )
with col3:
    if n_rows > 0:
        h_min = df_filtered["tunti"].min()
        h_max = df_filtered["tunti"].max()
        hour_range = f"{h_min}–{h_max} h"
    else:
        hour_range = "–"
    st.markdown(
        f'<div class="metric-card"><div class="val">{hour_range}</div>'
        f'<div class="lbl">Aktiiviset tunnit</div></div>',
        unsafe_allow_html=True,
    )
with col4:
    avg_q = f"{df_filtered['q'].mean():.1f}" if n_rows > 0 else "–"
    st.markdown(
        f'<div class="metric-card"><div class="val">{avg_q}</div>'
        f'<div class="lbl">Keskimääräinen Q</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Floor-plan map
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">🗺️ Pohjapiirros – yöaktiivisuus</div>', unsafe_allow_html=True)

if df_filtered.is_empty():
    st.info("💤 Ei havaintoja valituilla suodattimilla.")
else:
    img = load_image(IMAGE_PATH)
    fig = build_figure(df_filtered, img, color_mode, point_size, point_opacity)
    st.plotly_chart(fig, use_container_width=True)

    # ── Hour histogram ───────────────────────────────────────────────────────
    st.markdown('<div class="section-title">⏱️ Aktiivisuus tunneittain</div>', unsafe_allow_html=True)

    hour_counts = (
        df_filtered
        .group_by("tunti")
        .len()
        .rename({"len": "havaintoja"})
        .with_columns(
            pl.when(pl.col("tunti") >= 22)
            .then(pl.col("tunti") - 24)
            .otherwise(pl.col("tunti"))
            .alias("_sort")
        )
        .sort("_sort")
    )

    hour_fig = go.Figure(go.Bar(
        x=hour_counts["tunti"].to_list(),
        y=hour_counts["havaintoja"].to_list(),
        marker_color="#6366f1",
        text=hour_counts["havaintoja"].to_list(),
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
            df_filtered.select(show_cols)
            .sort(["node_id", "aika"])
            .to_arrow(),        # Zero-copy transfer to Streamlit
            use_container_width=True,
            height=300,
        )

# ---------------------------------------------------------------------------
# Positioning accuracy analysis (visible only when a single cart is selected)
# ---------------------------------------------------------------------------
if selected_cart != all_option and not df_filtered.is_empty():
    st.markdown(
        '<div class="section-title">🎯 Paikannustarkkuusanalyysi</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.85rem;color:#64748b;margin-bottom:1rem;'>"
        "Laite oli paikallaan koko yön – sijaintijakauma kuvaa paikannusjärjestelmän tarkkuutta.</div>",
        unsafe_allow_html=True,
    )

    x_arr = df_filtered["x"].to_numpy().astype(float)
    y_arr = df_filtered["y"].to_numpy().astype(float)

    cx = float(np.mean(x_arr))
    cy = float(np.mean(y_arr))
    std_x = float(np.std(x_arr))
    std_y = float(np.std(y_arr))
    rmse_2d = float(np.sqrt(std_x**2 + std_y**2))

    dists = np.sqrt((x_arr - cx) ** 2 + (y_arr - cy) ** 2)
    cep50 = float(np.percentile(dists, 50))
    cep68 = float(np.percentile(dists, 68))
    cep95 = float(np.percentile(dists, 95))

    # Step jitter: consecutive sample-to-sample distance
    step_jitter = np.sqrt(np.diff(x_arr)**2 + np.diff(y_arr)**2)
    mean_jitter = float(np.mean(step_jitter))
    p95_jitter  = float(np.percentile(step_jitter, 95))

    # Drift: linear regression slope on index → cm/1000 samples, then to cm/h
    n = len(x_arr)
    t_idx = np.arange(n, dtype=float)
    # samples per hour estimate from actual timestamps
    aika_series = df_filtered["aika"].cast(pl.Int64).to_numpy().astype(float)
    duration_h = (aika_series[-1] - aika_series[0]) / 3_600_000_000 if n > 1 else 1.0
    samples_per_h = n / max(duration_h, 1e-6)
    drift_x_cmh = float(np.polyfit(t_idx, x_arr - cx, 1)[0] * samples_per_h)
    drift_y_cmh = float(np.polyfit(t_idx, y_arr - cy, 1)[0] * samples_per_h)

    outlier_rate = float(np.mean(dists > 2 * rmse_2d) * 100)
    lq_rate = float(df_filtered["is_low_quality"].mean() * 100) if "is_low_quality" in df_filtered.columns else float("nan")

    # ── Accuracy metrics row ─────────────────────────────────────────────────
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    for col, label, val, unit in [
        (m1, "RMSE 2D",     rmse_2d,     "cm"),
        (m2, "CEP50",       cep50,       "cm"),
        (m3, "CEP95",       cep95,       "cm"),
        (m4, "Jitter (ka)", mean_jitter, "cm/step"),
        (m5, "Drift X",     drift_x_cmh, "cm/h"),
        (m6, "Outlierit",   outlier_rate,"%"),
    ]:
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="val">{val:.1f}</div>'
            f'<div class="lbl">{label} ({unit})</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Two-column layout: deviation scatter + radial error histogram ────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            "<div style='font-size:0.85rem;font-weight:600;color:#312e81;"
            "margin:0.8rem 0 0.4rem;'>Sijaintipilvi suhteessa keskipisteeseen</div>",
            unsafe_allow_html=True,
        )
        dx = (x_arr - cx).tolist()
        dy = (y_arr - cy).tolist()

        scatter_fig = go.Figure()
        scatter_fig.add_trace(go.Scattergl(
            x=dx, y=dy,
            mode="markers",
            marker=dict(
                size=3,
                color=df_filtered["tunti"].to_list(),
                colorscale="Viridis",
                opacity=0.45,
                colorbar=dict(title="Tunti", thickness=10, len=0.6),
                line=dict(width=0),
            ),
            name="Havainnot",
        ))

        # CEP circles
        angles = np.linspace(0, 2 * math.pi, 361)
        cos_a, sin_a = np.cos(angles).tolist(), np.sin(angles).tolist()
        for radius, color, label in [
            (cep50, "#22c55e", f"CEP50 {cep50:.0f} cm"),
            (cep68, "#f59e0b", f"CEP68 {cep68:.0f} cm"),
            (cep95, "#ef4444", f"CEP95 {cep95:.0f} cm"),
        ]:
            scatter_fig.add_trace(go.Scatter(
                x=[radius * c for c in cos_a],
                y=[radius * s for s in sin_a],
                mode="lines",
                line=dict(color=color, width=2),
                name=label,
            ))

        scatter_fig.update_layout(
            xaxis=dict(title="ΔX (cm)", zeroline=True, zerolinewidth=1,
                       zerolinecolor="#cbd5e1", showgrid=True),
            yaxis=dict(title="ΔY (cm)", zeroline=True, zerolinewidth=1,
                       zerolinecolor="#cbd5e1", showgrid=True,
                       scaleanchor="x", scaleratio=1),
            height=420,
            margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,250,252,1)",
            legend=dict(font=dict(size=11)),
        )
        st.plotly_chart(scatter_fig, use_container_width=True)

    with right:
        st.markdown(
            "<div style='font-size:0.85rem;font-weight:600;color:#312e81;"
            "margin:0.8rem 0 0.4rem;'>Säteisvirheen jakauma</div>",
            unsafe_allow_html=True,
        )
        hist_vals, bin_edges = np.histogram(dists, bins=50)
        bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()

        err_fig = go.Figure()
        err_fig.add_trace(go.Bar(
            x=bin_centers,
            y=hist_vals.tolist(),
            marker_color="#6366f1",
            opacity=0.8,
            name="Havainnot",
        ))
        for radius, color, label in [
            (cep50, "#22c55e", f"CEP50"),
            (cep95, "#ef4444", f"CEP95"),
        ]:
            err_fig.add_vline(
                x=radius, line_color=color, line_width=2, line_dash="dash",
                annotation_text=label, annotation_position="top right",
                annotation_font_size=11,
            )
        err_fig.update_layout(
            xaxis=dict(title="Säteisvirhe (cm)"),
            yaxis=dict(title="Havaintojen määrä"),
            height=420,
            margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(248,250,252,1)",
            showlegend=False,
        )
        st.plotly_chart(err_fig, use_container_width=True)

    # ── Drift: position deviation over time with trend lines ─────────────────
    st.markdown(
        "<div style='font-size:0.85rem;font-weight:600;color:#312e81;"
        "margin:0.8rem 0 0.4rem;'>Drift – systemaattinen sijaintimuutos yön yli</div>",
        unsafe_allow_html=True,
    )
    times = df_filtered["aika"].cast(pl.String).to_list()
    trend_x = np.polyval(np.polyfit(t_idx, x_arr - cx, 1), t_idx).tolist()
    trend_y = np.polyval(np.polyfit(t_idx, y_arr - cy, 1), t_idx).tolist()

    drift_fig = go.Figure()
    drift_fig.add_trace(go.Scattergl(
        x=times, y=(x_arr - cx).tolist(),
        mode="markers", marker=dict(size=2, color="#6366f1", opacity=0.3),
        name="ΔX",
    ))
    drift_fig.add_trace(go.Scattergl(
        x=times, y=(y_arr - cy).tolist(),
        mode="markers", marker=dict(size=2, color="#ec4899", opacity=0.3),
        name="ΔY",
    ))
    drift_fig.add_trace(go.Scatter(
        x=times, y=trend_x,
        mode="lines", line=dict(color="#6366f1", width=2),
        name=f"Trendi X ({drift_x_cmh:+.1f} cm/h)",
    ))
    drift_fig.add_trace(go.Scatter(
        x=times, y=trend_y,
        mode="lines", line=dict(color="#ec4899", width=2),
        name=f"Trendi Y ({drift_y_cmh:+.1f} cm/h)",
    ))
    drift_fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
    drift_fig.update_layout(
        xaxis=dict(title="Aika (Helsinki)"),
        yaxis=dict(title="Poikkeama keskipisteestä (cm)"),
        height=280,
        margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        legend=dict(orientation="h", y=1.1, font=dict(size=11)),
    )
    st.plotly_chart(drift_fig, use_container_width=True)

    # ── Step jitter over time ────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.85rem;font-weight:600;color:#312e81;"
        "margin:0.8rem 0 0.4rem;'>Jitter – peräkkäisten mittausten välinen hyppäys</div>",
        unsafe_allow_html=True,
    )
    jitter_fig = go.Figure()
    jitter_fig.add_trace(go.Scattergl(
        x=times[1:], y=step_jitter.tolist(),
        mode="markers", marker=dict(size=2, color="#0ea5e9", opacity=0.4),
        name="Askelvirhe",
    ))
    jitter_fig.add_hline(
        y=mean_jitter, line_color="#22c55e", line_width=2, line_dash="dash",
        annotation_text=f"ka {mean_jitter:.1f} cm", annotation_position="top left",
    )
    jitter_fig.add_hline(
        y=p95_jitter, line_color="#ef4444", line_width=2, line_dash="dash",
        annotation_text=f"p95 {p95_jitter:.1f} cm", annotation_position="top left",
    )
    jitter_fig.update_layout(
        xaxis=dict(title="Aika (Helsinki)"),
        yaxis=dict(title="Hyppäys (cm)", type="log"),
        height=260,
        margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        showlegend=False,
    )
    st.plotly_chart(jitter_fig, use_container_width=True)

    # ── Summary table ────────────────────────────────────────────────────────
    with st.expander("📊 Tarkkuustaulukko"):
        summary = pl.DataFrame({
            "Mittari": [
                "Keskipiste X (cm)", "Keskipiste Y (cm)",
                "σ X (cm)", "σ Y (cm)", "RMSE 2D (cm)",
                "CEP50 (cm)", "CEP68 (cm)", "CEP95 (cm)",
                "Jitter ka (cm/step)", "Jitter p95 (cm/step)",
                "Drift X (cm/h)", "Drift Y (cm/h)",
                "Outlieriaste (>2σ, %)", "Heikko signaali (%)",
                "Havaintoja",
            ],
            "Arvo": [
                f"{cx:.1f}", f"{cy:.1f}",
                f"{std_x:.1f}", f"{std_y:.1f}", f"{rmse_2d:.1f}",
                f"{cep50:.1f}", f"{cep68:.1f}", f"{cep95:.1f}",
                f"{mean_jitter:.1f}", f"{p95_jitter:.1f}",
                f"{drift_x_cmh:+.2f}", f"{drift_y_cmh:+.2f}",
                f"{outlier_rate:.1f}",
                f"{lq_rate:.1f}" if not math.isnan(lq_rate) else "–",
                str(len(df_filtered)),
            ],
        })
        st.dataframe(summary, use_container_width=True, hide_index=True)

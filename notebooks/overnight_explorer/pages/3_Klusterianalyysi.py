"""
Aktiivisuusvyöhykkeiden automaattinen tunnistus – KMeans-klusterointi
======================================================================
Tunnistaa automaattisesti missä kärryt viettävät aikaa ilman manuaalisesti
määriteltyjä osastoja. Paino asetetaan pingimäärän mukaan, joten usein
vieraillut ruudut ohjaavat klusterin muodostumista.
"""

from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from PIL import Image
from sklearn.cluster import KMeans

st.set_page_config(page_title="Klusterianalyysi", page_icon="🗂️", layout="wide")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parents[3]
DUCKDB_PATH    = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"
SILVER_PARQUET = PROJECT_ROOT / "data" / "pbi_prototypes" / "silver_device_diagnostics.parquet"
IMAGE_PATH     = PROJECT_ROOT / "image" / "kauppa2.png"
MAP_MAX_X, MAP_MAX_Y = 10406, 5220
CELL_SIZE = 100

CLUSTER_COLORS = [
    "#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16",
    "#06b6d4", "#e11d48", "#7c3aed", "#0891b2", "#65a30d",
]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #1e1b4b, #312e81, #1e3a5f);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hero p  { font-size: 1rem; color: #a5b4fc; margin: 0; }
.metric-card {
    background: #1e1b4b; border: 1px solid #3730a3; border-radius: 12px;
    padding: 1rem 1.2rem; text-align: center; color: white;
}
.metric-card .val { font-size: 2rem; font-weight: 700; color: #818cf8; }
.metric-card .lbl { font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem; }
.section-title {
    font-size: 1.1rem; font-weight: 600; color: #312e81;
    margin: 1.2rem 0 0.6rem 0; border-left: 4px solid #6366f1; padding-left: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🗂️ Aktiivisuusvyöhykkeiden klusterointi</h1>
    <p>KMeans tunnistaa automaattisesti missä kärryt viettävät aikaa – ilman manuaalisesti määriteltyjä osastoja</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _get_conn():
    if SILVER_PARQUET.exists():
        conn = duckdb.connect()
        conn.execute(
            f"CREATE VIEW silver_device_diagnostics AS "
            f"SELECT * FROM read_parquet('{SILVER_PARQUET}')"
        )
        return conn
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("silver_device_diagnostics.parquet eikä dev.duckdb löydy.")
    st.stop()


@st.cache_data(show_spinner=False)
def fetch_date_range() -> tuple:
    conn = _get_conn()
    row = conn.execute("SELECT MIN(dt), MAX(dt) FROM silver_device_diagnostics").fetchone()
    return row[0], row[1]


@st.cache_data(show_spinner="🔍 Haetaan data…", ttl=300)
def fetch_grid(date_start: str, date_end: str, only_daytime: bool) -> pl.DataFrame:
    conn = _get_conn()
    night_filter = "AND is_night_time = 0" if only_daytime else ""
    arrow = conn.execute(f"""
        SELECT
            FLOOR(x / {CELL_SIZE}.0) * {CELL_SIZE}  AS grid_x,
            FLOOR(y / {CELL_SIZE}.0) * {CELL_SIZE}  AS grid_y,
            COUNT(*)                                  AS total_pings
        FROM silver_device_diagnostics
        WHERE is_out_of_bounds = 0
          AND dt >= '{date_start}'
          AND dt <= '{date_end}'
          {night_filter}
        GROUP BY grid_x, grid_y
    """).fetch_arrow_table()
    return pl.from_arrow(arrow)


@st.cache_resource(show_spinner=False)
def load_image(path: Path) -> Image.Image:
    return Image.open(path)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("## ⚙️ Asetukset")

dt_min, dt_max = fetch_date_range()
date_range = st.sidebar.date_input(
    "Aikaväli", value=(dt_min, dt_max), min_value=dt_min, max_value=dt_max,
)
if len(date_range) != 2:
    st.sidebar.info("Valitse alku- ja loppupäivä.")
    st.stop()
date_start, date_end = str(date_range[0]), str(date_range[1])

st.sidebar.markdown("---")

n_clusters = st.sidebar.slider("Klustereiden määrä", min_value=2, max_value=15, value=6)

only_daytime = st.sidebar.checkbox("Vain aukioloaika (07–22)", value=True)

min_pings = st.sidebar.slider(
    "Minimi pingejä per ruutu",
    min_value=1, max_value=1000, value=50, step=10,
    help="Poistaa harvoin vieraillut ruudut ennen klusterointia",
)

opacity = st.sidebar.slider("Kartan läpinäkyvyys", 0.3, 1.0, 0.7, 0.05)

# ---------------------------------------------------------------------------
# Load & filter
# ---------------------------------------------------------------------------
df = fetch_grid(date_start, date_end, only_daytime)
df = df.filter(pl.col("total_pings") >= min_pings)

if df.is_empty():
    st.warning("Ei dataa valituilla suodattimilla.")
    st.stop()

# ---------------------------------------------------------------------------
# KMeans – weighted by ping count so busy cells pull clusters harder
# ---------------------------------------------------------------------------
X = df.select(["grid_x", "grid_y"]).to_numpy()
weights = df["total_pings"].to_numpy().astype(float)

kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
kmeans.fit(X, sample_weight=weights)

df = df.with_columns(pl.Series("cluster", kmeans.labels_.astype(int)))
centroids = kmeans.cluster_centers_  # shape (n_clusters, 2)

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
total_pings = df["total_pings"].sum()
active_cells = len(df)

st.markdown('<div class="section-title">📊 Yhteenveto</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
for col, label, val in [
    (c1, "Aktiivisia ruutuja", f"{active_cells:,}"),
    (c2, "Pingiä yhteensä",    f"{total_pings:,}"),
    (c3, "Klustereita",        f"{n_clusters}"),
]:
    col.markdown(
        f'<div class="metric-card"><div class="val">{val}</div>'
        f'<div class="lbl">{label}</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Cluster map
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">🗺️ Aktiivisuusvyöhykkeet kartalla</div>',
            unsafe_allow_html=True)

if IMAGE_PATH.exists():
    img = load_image(IMAGE_PATH)
    fig = go.Figure()

    fig.add_layout_image(dict(
        source=img, xref="x", yref="y", x=0, y=0,
        sizex=MAP_MAX_X, sizey=MAP_MAX_Y, sizing="stretch",
        opacity=1.0, layer="below", xanchor="left", yanchor="top",
    ))

    # One scatter trace per cluster for legend
    for c in range(n_clusters):
        c_df = df.filter(pl.col("cluster") == c)
        if c_df.is_empty():
            continue
        color = CLUSTER_COLORS[c % len(CLUSTER_COLORS)]
        fig.add_trace(go.Scatter(
            x=c_df["grid_x"].to_list(),
            y=c_df["grid_y"].to_list(),
            mode="markers",
            marker=dict(
                size=8,
                color=color,
                opacity=opacity,
                symbol="square",
                line=dict(width=0),
            ),
            name=f"Vyöhyke {c + 1}",
            hovertemplate=(
                f"<b>Vyöhyke {c + 1}</b><br>"
                "x=%{x} cm<br>y=%{y} cm<extra></extra>"
            ),
        ))

    # Centroid markers
    for c, (cx, cy) in enumerate(centroids):
        color = CLUSTER_COLORS[c % len(CLUSTER_COLORS)]
        fig.add_trace(go.Scatter(
            x=[cx], y=[cy],
            mode="markers+text",
            marker=dict(size=18, color=color, symbol="star", line=dict(color="white", width=2)),
            text=[str(c + 1)],
            textposition="middle center",
            textfont=dict(color="white", size=10, family="Inter"),
            showlegend=False,
            hovertemplate=f"<b>Vyöhyke {c + 1} – keskipiste</b><br>x={cx:.0f} cm<br>y={cy:.0f} cm<extra></extra>",
        ))

    fig.update_xaxes(range=[0, MAP_MAX_X], showgrid=False, showticklabels=False)
    fig.update_yaxes(range=[MAP_MAX_Y, 0], showgrid=False, showticklabels=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=550, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="top", y=-0.02, xanchor="left", x=0,
            bgcolor="rgba(255,255,255,0.85)", bordercolor="#e2e8f0", borderwidth=1,
            font=dict(size=11),
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Cluster stats table
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📋 Vyöhykkeiden tilastot</div>', unsafe_allow_html=True)

stats = (
    df.group_by("cluster")
    .agg([
        pl.col("total_pings").sum().alias("pingiä_yhteensä"),
        pl.len().alias("ruutuja"),
        pl.col("grid_x").mean().alias("keskipiste_x"),
        pl.col("grid_y").mean().alias("keskipiste_y"),
    ])
    .sort("cluster")
    .with_columns([
        (pl.col("cluster") + 1).alias("Vyöhyke"),
        pl.col("pingiä_yhteensä").cast(pl.Int64),
        pl.col("ruutuja").cast(pl.Int32),
        pl.col("keskipiste_x").round(0).cast(pl.Int32),
        pl.col("keskipiste_y").round(0).cast(pl.Int32),
        (pl.col("pingiä_yhteensä") * 100.0 / pl.col("pingiä_yhteensä").sum()).round(1).alias("osuus_%"),
    ])
    .select(["Vyöhyke", "pingiä_yhteensä", "osuus_%", "ruutuja", "keskipiste_x", "keskipiste_y"])
)

st.dataframe(stats.to_arrow(), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Ping share bar chart per cluster
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📊 Pingien jakautuminen vyöhykkeittäin</div>',
            unsafe_allow_html=True)

bar_fig = go.Figure(go.Bar(
    x=[f"Vyöhyke {r[0]}" for r in stats.select("Vyöhyke").iter_rows()],
    y=stats["osuus_%"].to_list(),
    marker_color=[CLUSTER_COLORS[i % len(CLUSTER_COLORS)] for i in range(n_clusters)],
    text=[f"{v:.1f}%" for v in stats["osuus_%"].to_list()],
    textposition="outside",
))
bar_fig.update_layout(
    xaxis=dict(title="Vyöhyke"),
    yaxis=dict(title="Osuus pingeistä (%)"),
    height=280, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    showlegend=False,
)
st.plotly_chart(bar_fig, use_container_width=True)

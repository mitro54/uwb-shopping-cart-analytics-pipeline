"""
Paikannustarkkuus – yöaikaiset tarkkuusmittarit
"""

import math
from datetime import date as _date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Paikannustarkkuus", page_icon="🎯", layout="wide")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
PROJECT_ROOT   = Path(__file__).resolve().parents[2]
GOLD_PARQUET   = PROJECT_ROOT / "data" / "pbi_prototypes" / "f_paikannustarkkuus.parquet"
SILVER_PARQUET = PROJECT_ROOT / "data" / "pbi_prototypes" / "silver_device_diagnostics.parquet"
IMAGE_PATH     = PROJECT_ROOT / "image" / "kauppa2.png"
MAP_MAX_X, MAP_MAX_Y = 10406, 5220
CHARGING_STATIONS = [
    {"x": 100,  "y": 2500, "radius": 400},
    {"x": 900,  "y": 3600, "radius": 600},
]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
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
    <h1>🎯 Paikannustarkkuus – yöanalyysi</h1>
    <p>Esiaggregoidut tarkkuusmittarit paikallaan olleille laitteille</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="📅 Haetaan gold-data…", ttl=300)
def fetch_gold() -> pl.DataFrame:
    if not GOLD_PARQUET.exists():
        st.error(f"Gold-parquet ei löydy: {GOLD_PARQUET}")
        st.stop()
    return pl.read_parquet(GOLD_PARQUET).sort(["yo_paiva", "node_id"])


@st.cache_resource(show_spinner=False)
def _silver_conn() -> duckdb.DuckDBPyConnection:
    if not SILVER_PARQUET.exists():
        st.error(f"Silver-parquet ei löydy: {SILVER_PARQUET}")
        st.stop()
    conn = duckdb.connect()
    conn.execute(
        f"CREATE VIEW silver_device_diagnostics AS "
        f"SELECT * FROM read_parquet('{SILVER_PARQUET}')"
    )
    return conn


def _charging_exclusion() -> str:
    parts = []
    for cs in CHARGING_STATIONS:
        r_sq = cs["radius"] ** 2
        parts.append(f"(POWER(x - {cs['x']}, 2) + POWER(y - {cs['y']}, 2) > {r_sq})")
    return " AND ".join(parts)


@st.cache_data(show_spinner="🔗 Haetaan yön raakadata…", ttl=300)
def fetch_device_night(node_id: str, yo_paiva: str, cx: float, cy: float) -> pl.DataFrame:
    conn       = _silver_conn()
    exclusion  = _charging_exclusion()
    next_date  = str(_date.fromisoformat(yo_paiva) + timedelta(days=1))
    arrow = conn.execute(f"""
        WITH tz AS (
            SELECT node_id,
                   timezone('Europe/Helsinki', aika::TIMESTAMPTZ) AS aika_hki,
                   x, y, q, is_low_quality, is_jitter
            FROM silver_device_diagnostics
            WHERE node_id = '{node_id}'
              AND x IS NOT NULL AND y IS NOT NULL
              AND x >= 500
              AND {exclusion}
        )
        SELECT aika_hki,
               EXTRACT('hour' FROM aika_hki)::INT              AS tunti,
               x, y,
               ROUND(x - {cx}, 1)                              AS dx,
               ROUND(y - {cy}, 1)                              AS dy,
               ROUND(SQRT(POWER(x-{cx},2)+POWER(y-{cy},2)),1) AS dist,
               q, is_low_quality, is_jitter
        FROM tz
        WHERE (CAST(aika_hki AS DATE) = CAST('{yo_paiva}' AS DATE)
               AND EXTRACT('hour' FROM aika_hki) >= 22)
           OR (CAST(aika_hki AS DATE) = CAST('{next_date}' AS DATE)
               AND EXTRACT('hour' FROM aika_hki) < 7)
        ORDER BY aika_hki
    """).to_arrow_table()
    return pl.from_arrow(arrow)


@st.cache_resource(show_spinner=False)
def load_image(path: Path) -> Image.Image:
    return Image.open(path)


# ---------------------------------------------------------------------------
# Load gold summary
# ---------------------------------------------------------------------------
df_all = fetch_gold()
if df_all.is_empty():
    st.warning("Gold-taulussa ei ole dataa. Aja ensin `dbt run`.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔍 Suodattimet")

all_option      = "— Kaikki laitteet —"
available_nodes = sorted(df_all["node_id"].unique().to_list())
selected_node   = st.sidebar.selectbox(
    "📡 Valitse laite",
    options=[all_option] + [str(n) for n in available_nodes],
    index=0,
)

if selected_node == all_option:
    nights_for_node = sorted(df_all["yo_paiva"].cast(pl.String).unique().to_list())
else:
    nights_for_node = sorted(
        df_all.filter(pl.col("node_id").cast(pl.String) == selected_node)
        ["yo_paiva"].cast(pl.String).unique().to_list()
    )

if len(nights_for_node) == 1:
    selected_date = nights_for_node[0]
    st.sidebar.markdown(f"📅 **Yö:** {selected_date}")
else:
    selected_date = st.sidebar.selectbox("📅 Valitse yö", options=nights_for_node, index=0)

df_night = df_all.filter(pl.col("yo_paiva").cast(pl.String) == selected_date)

# ---------------------------------------------------------------------------
# Night-level summary
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📊 Yön yhteenveto</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
for col, label, val in [
    (c1, "Laitteita",        f"{len(df_night)}"),
    (c2, "Mediaani RMSE 2D", f"{df_night['rmse_2d'].median():.1f} cm"),
    (c3, "Mediaani CEP50",   f"{df_night['cep50'].median():.1f} cm"),
    (c4, "Mediaani CEP95",   f"{df_night['cep95'].median():.1f} cm"),
    (c5, "Mediaani Jitter",  f"{df_night['jitter_ka_cm'].median():.1f} cm"),
]:
    col.markdown(
        f'<div class="metric-card"><div class="val">{val}</div>'
        f'<div class="lbl">{label}</div></div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# All-devices table + RMSE bar
# ---------------------------------------------------------------------------
display_cols = [
    "yo_paiva", "node_id", "n_pings", "rmse_2d", "cep50", "cep68", "cep95",
    "jitter_ka_cm", "jitter_p95_cm", "drift_x_cmh", "drift_y_cmh",
    "outlier_pct", "avg_q", "low_quality_pct",
]
st.markdown('<div class="section-title">📋 Kaikki laitteet – valittu yö</div>', unsafe_allow_html=True)
st.dataframe(df_night.select(display_cols).sort("node_id").to_arrow(),
             use_container_width=True, hide_index=True)

st.markdown('<div class="section-title">📏 RMSE 2D per laite</div>', unsafe_allow_html=True)
df_sorted = df_night.sort("rmse_2d")
bar_fig = go.Figure(go.Bar(
    x=[str(n) for n in df_sorted["node_id"].to_list()],
    y=df_sorted["rmse_2d"].to_list(),
    marker_color="#6366f1",
    text=[f"{v:.1f}" for v in df_sorted["rmse_2d"].to_list()],
    textposition="outside",
))
bar_fig.update_layout(
    xaxis=dict(title="node_id", type="category"),
    yaxis=dict(title="RMSE 2D (cm)"),
    height=300, margin=dict(l=40, r=20, t=10, b=40),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
)
st.plotly_chart(bar_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Single-device view
# ---------------------------------------------------------------------------
if selected_node == all_option:
    st.stop()

df_node = df_all.filter(pl.col("node_id").cast(pl.String) == selected_node).sort("yo_paiva")
st.markdown(f'<div class="section-title">🔍 Laite {selected_node} – tarkkuusanalyysi</div>',
            unsafe_allow_html=True)

row = df_night.filter(pl.col("node_id").cast(pl.String) == selected_node)
if row.is_empty():
    st.info("Laitteella ei ole dataa valitulle yölle.")
    st.stop()

r  = row.row(0, named=True)
cx = r["centroid_x"]
cy = r["centroid_y"]

m1, m2, m3, m4, m5, m6 = st.columns(6)
for col, label, val, unit in [
    (m1, "RMSE 2D",   r["rmse_2d"],     "cm"),
    (m2, "CEP50",     r["cep50"],        "cm"),
    (m3, "CEP95",     r["cep95"],        "cm"),
    (m4, "Jitter ka", r["jitter_ka_cm"], "cm/step"),
    (m5, "Drift X",   r["drift_x_cmh"], "cm/h"),
    (m6, "Outlierit", r["outlier_pct"],  "%"),
]:
    col.markdown(f'<div class="metric-card"><div class="val">{val:.1f}</div>'
                 f'<div class="lbl">{label} ({unit})</div></div>', unsafe_allow_html=True)

with st.spinner("Haetaan yön raakadata silveristä…"):
    df_raw = fetch_device_night(selected_node, selected_date, cx, cy)

angles    = np.linspace(0, 2 * math.pi, 361)
cos_a     = np.cos(angles).tolist()
sin_a     = np.sin(angles).tolist()
dx_arr    = df_raw["dx"].to_list()
dy_arr    = df_raw["dy"].to_list()
dist_arr  = df_raw["dist"].to_list()
tunti_arr = df_raw["tunti"].to_list()
aika_arr  = df_raw["aika_hki"].cast(pl.String).to_list()

# ── Sijaintipilvi + säteisvirhejakauma ────────────────────────────────────────
st.markdown('<div class="section-title">🎯 Paikannustarkkuus – sijaintipilvi ja säteisvirhejakauma</div>',
            unsafe_allow_html=True)
left, right = st.columns([3, 2])

with left:
    st.markdown("<div style='font-size:0.85rem;font-weight:600;color:#312e81;"
                "margin:0.8rem 0 0.4rem;'>Sijaintipilvi suhteessa keskipisteeseen</div>",
                unsafe_allow_html=True)
    scatter_fig = go.Figure()
    scatter_fig.add_trace(go.Scattergl(
        x=dx_arr, y=[-d for d in dy_arr], mode="markers",
        marker=dict(size=3, color=tunti_arr, colorscale="Viridis", opacity=0.45,
                    colorbar=dict(title="Tunti", thickness=10, len=0.6), line=dict(width=0)),
        name="Havainnot",
    ))
    for radius, color, label in [
        (r["cep50"], "#22c55e", f"CEP50 {r['cep50']:.0f} cm"),
        (r["cep68"], "#f59e0b", f"CEP68 {r['cep68']:.0f} cm"),
        (r["cep95"], "#ef4444", f"CEP95 {r['cep95']:.0f} cm"),
    ]:
        scatter_fig.add_trace(go.Scatter(
            x=[radius * c for c in cos_a], y=[-radius * s for s in sin_a],
            mode="lines", line=dict(color=color, width=2), name=label,
        ))
    scatter_fig.update_layout(
        xaxis=dict(title="ΔX (cm)", zeroline=True, zerolinewidth=1, zerolinecolor="#cbd5e1", showgrid=True),
        yaxis=dict(title="ΔY (cm, ↑=pohj.)", zeroline=True, zerolinewidth=1, zerolinecolor="#cbd5e1",
                   showgrid=True, scaleanchor="x", scaleratio=1),
        height=420, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        legend=dict(font=dict(size=11)),
    )
    st.plotly_chart(scatter_fig, use_container_width=True)

with right:
    st.markdown("<div style='font-size:0.85rem;font-weight:600;color:#312e81;"
                "margin:0.8rem 0 0.4rem;'>Säteisvirheen jakauma</div>",
                unsafe_allow_html=True)
    dist_np = np.array(dist_arr)
    hist_vals, bin_edges = np.histogram(dist_np, bins=50)
    bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()
    err_fig = go.Figure()
    err_fig.add_trace(go.Bar(x=bin_centers, y=hist_vals.tolist(),
                             marker_color="#6366f1", opacity=0.8, name="Havainnot"))
    for radius, color, label in [
        (r["cep50"], "#22c55e", "CEP50"),
        (r["cep95"], "#ef4444", "CEP95"),
    ]:
        err_fig.add_vline(x=radius, line_color=color, line_width=2, line_dash="dash",
                          annotation_text=label, annotation_position="top right",
                          annotation_font_size=11)
    err_fig.update_layout(
        xaxis=dict(title="Säteisvirhe (cm)"), yaxis=dict(title="Havaintojen määrä"),
        height=420, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)", showlegend=False,
    )
    st.plotly_chart(err_fig, use_container_width=True)

# ── Floor plan ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🗺️ Laitteen sijainti pohjapiirustuksessa</div>',
            unsafe_allow_html=True)
if IMAGE_PATH.exists():
    img    = load_image(IMAGE_PATH)
    fp_fig = go.Figure()
    fp_fig.add_layout_image(dict(
        source=img, xref="x", yref="y", x=0, y=0,
        sizex=MAP_MAX_X, sizey=MAP_MAX_Y, sizing="stretch", opacity=1.0, layer="below",
        xanchor="left", yanchor="top",
    ))
    for radius, color, label in [
        (r["cep50"], "#22c55e", "CEP50"),
        (r["cep68"], "#f59e0b", "CEP68"),
        (r["cep95"], "#ef4444", "CEP95"),
    ]:
        fp_fig.add_trace(go.Scatter(
            x=[cx + radius * c for c in cos_a], y=[cy + radius * s for s in sin_a],
            mode="lines", line=dict(color=color, width=2), name=label,
        ))
    fp_fig.add_trace(go.Scattergl(
        x=df_raw["x"].to_list(), y=df_raw["y"].to_list(), mode="markers",
        marker=dict(size=3, color=tunti_arr, colorscale="Viridis", opacity=0.45,
                    colorbar=dict(title="Tunti", thickness=10, len=0.6), line=dict(width=0)),
        name="Havainnot",
    ))
    fp_fig.add_trace(go.Scatter(
        x=[cx], y=[cy], mode="markers",
        marker=dict(size=12, color="#6366f1", symbol="cross"),
        name=f"Keskipiste ({cx:.0f}, {cy:.0f})",
    ))
    zoom_pad = max(r["cep95"] * 10, 1500)
    if zoom_pad < MAP_MAX_X * 0.4:
        x_range = [max(cx - zoom_pad, 0), min(cx + zoom_pad, MAP_MAX_X)]
        y_range = [max(cy - zoom_pad, 0), min(cy + zoom_pad, MAP_MAX_Y)]
    else:
        x_range, y_range = [0, MAP_MAX_X], [0, MAP_MAX_Y]

    fp_fig.update_xaxes(range=x_range, showgrid=False, showticklabels=False)
    fp_fig.update_yaxes(range=[y_range[1], y_range[0]], showgrid=False, showticklabels=False,
                        scaleanchor="x", scaleratio=1)
    fp_fig.update_layout(
        height=420, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="left", x=0,
                    font=dict(size=11)),
    )
    st.plotly_chart(fp_fig, use_container_width=True)
else:
    st.info("Pohjapiirros ei löydy (image/kauppa2.png).")

# ── Drift ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📉 Drift – systemaattinen sijaintimuutos yön yli</div>',
            unsafe_allow_html=True)
n     = len(dx_arr)
t_idx = np.arange(n, dtype=float)
dx_np = np.array(dx_arr, dtype=float)
dy_np = np.array(dy_arr, dtype=float)
trend_x = np.polyval(np.polyfit(t_idx, dx_np, 1), t_idx).tolist()
trend_y = np.polyval(np.polyfit(t_idx, dy_np, 1), t_idx).tolist()

drift_fig = go.Figure()
drift_fig.add_trace(go.Scattergl(x=aika_arr, y=dx_arr, mode="markers",
                                  marker=dict(size=2, color="#6366f1", opacity=0.3), name="ΔX"))
drift_fig.add_trace(go.Scattergl(x=aika_arr, y=[-d for d in dy_arr], mode="markers",
                                  marker=dict(size=2, color="#ec4899", opacity=0.3), name="ΔY"))
drift_fig.add_trace(go.Scatter(x=aika_arr, y=trend_x, mode="lines",
                                line=dict(color="#6366f1", width=2),
                                name=f"Trendi X ({r['drift_x_cmh']:+.1f} cm/h)"))
drift_fig.add_trace(go.Scatter(x=aika_arr, y=[-v for v in trend_y], mode="lines",
                                line=dict(color="#ec4899", width=2),
                                name=f"Trendi Y ({r['drift_y_cmh']:+.1f} cm/h)"))
drift_fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
drift_fig.update_layout(
    xaxis=dict(title="Aika (Helsinki)"), yaxis=dict(title="Poikkeama keskipisteestä (cm)"),
    height=280, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    legend=dict(orientation="h", y=1.1, font=dict(size=11)),
)
st.plotly_chart(drift_fig, use_container_width=True)

# ── Multi-night trends ────────────────────────────────────────────────────────
if len(df_node) > 1:
    dates = df_node["yo_paiva"].cast(pl.String).to_list()
    st.markdown('<div class="section-title">📈 Tarkkuustrendi – useamman yön vertailu</div>',
                unsafe_allow_html=True)
    cep_fig = go.Figure()
    for col_name, color, label in [
        ("cep50",   "#22c55e", "CEP50"),
        ("cep68",   "#f59e0b", "CEP68"),
        ("cep95",   "#ef4444", "CEP95"),
        ("rmse_2d", "#6366f1", "RMSE 2D"),
    ]:
        cep_fig.add_trace(go.Scatter(x=dates, y=df_node[col_name].to_list(),
                                      mode="lines+markers", line=dict(color=color, width=2),
                                      marker=dict(size=6), name=label))
    cep_fig.update_layout(
        xaxis=dict(title="Yöpäivä"), yaxis=dict(title="cm"), height=300,
        margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        legend=dict(orientation="h", y=1.12, font=dict(size=11)),
    )
    st.plotly_chart(cep_fig, use_container_width=True)

# ── Summary table ─────────────────────────────────────────────────────────────
with st.expander("📊 Kaikki mittarit taulukossa"):
    st.dataframe(df_node.select(display_cols).sort("yo_paiva").to_arrow(),
                 use_container_width=True, hide_index=True)

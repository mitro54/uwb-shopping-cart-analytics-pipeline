"""
UWB-verkon laatu – kattavuus ja signaalin taso
===============================================
UWB-toimittajan näkymä: missä verkko toimii hyvin, missä on ongelmia.
"""

from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Verkon laatu", page_icon="📶", layout="wide")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
PROJECT_ROOT  = Path(__file__).resolve().parents[3]
DUCKDB_PATH   = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"
IMAGE_PATH    = PROJECT_ROOT / "image" / "kauppa2.png"
MAP_MAX_X, MAP_MAX_Y = 10406, 5220
CELL_SIZE = 100  # cm

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #0f2c0f, #1a3a2e, #0d2b1e);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hero p  { font-size: 1rem; color: #6ee7b7; margin: 0; }
.metric-card {
    background: #052e16; border: 1px solid #166534; border-radius: 12px;
    padding: 1rem 1.2rem; text-align: center; color: white;
}
.metric-card .val { font-size: 2rem; font-weight: 700; color: #4ade80; }
.metric-card .val.warn { color: #fbbf24; }
.metric-card .val.bad  { color: #f87171; }
.metric-card .lbl { font-size: 0.8rem; color: #86efac; margin-top: 0.2rem; }
.section-title {
    font-size: 1.1rem; font-weight: 600; color: #166534;
    margin: 1.2rem 0 0.6rem 0; border-left: 4px solid #22c55e; padding-left: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>📶 UWB-verkon laatu</h1>
    <p>Signaalin laatu ja kattavuus 1×1 m ruudukolla – UWB-toimittajan järjestelmänäkymä</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def _get_conn():
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb-tiedostoa ei löydy.")
    st.stop()


@st.cache_data(show_spinner=False)
def fetch_date_range() -> tuple:
    conn = _get_conn()
    row = conn.execute("SELECT MIN(dt), MAX(dt) FROM silver_device_diagnostics").fetchone()
    return row[0], row[1]


# Mirrors silver_positions filters: daytime, q threshold, charging stations, rectangular exclusions
_CORR_WHERE = """
    is_out_of_bounds = 0
    AND is_night_time = 0
    AND (POWER(x - 100, 2) + POWER(y - 2500, 2)) > POWER(400, 2)
    AND (POWER(x - 900, 2) + POWER(y - 3600, 2)) > POWER(600, 2)
    AND NOT (y > 3000 AND x >= 0 AND x <= 1500)
    AND NOT (y >= 0  AND y <= 600  AND x > 8400)
    AND NOT (y > 4700 AND x > 9900)
"""


@st.cache_data(show_spinner="📡 Haetaan verkkolaatu-data…", ttl=300)
def fetch_verkko(date_start: str, date_end: str) -> pl.DataFrame:
    conn = _get_conn()
    arrow = conn.execute(f"""
        SELECT
            FLOOR(x / 100.0) * 100                                          AS grid_x,
            FLOOR(y / 100.0) * 100                                          AS grid_y,
            COUNT(*)                                                         AS total_pings,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY q), 1)          AS median_quality,
            MIN(q)                                                           AS min_quality,
            SUM(is_low_quality)                                              AS low_quality_pings,
            SUM(is_jitter)                                                   AS jitter_pings,
            ROUND(SUM(is_low_quality) * 100.0 / NULLIF(COUNT(*), 0), 2)     AS low_quality_pct
        FROM silver_device_diagnostics
        WHERE is_out_of_bounds = 0
          AND dt >= '{date_start}'
          AND dt <= '{date_end}'
        GROUP BY grid_x, grid_y
    """).fetch_arrow_table()
    df = pl.from_arrow(arrow)
    return df.with_columns(
        (pl.col("jitter_pings") * 100.0 / pl.col("total_pings")).alias("jitter_pct")
    )


@st.cache_data(show_spinner="🔗 Haetaan korrelaatiodata…", ttl=300)
def fetch_verkko_corr(date_start: str, date_end: str) -> pl.DataFrame:
    """Grid aggregation with silver_positions filters for correlation analysis."""
    conn = _get_conn()
    arrow = conn.execute(f"""
        SELECT
            FLOOR(x / 100.0) * 100                                      AS grid_x,
            FLOOR(y / 100.0) * 100                                      AS grid_y,
            COUNT(*)                                                     AS total_pings,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY q), 1)     AS median_quality,
            ROUND(SUM(is_jitter) * 100.0 / NULLIF(COUNT(*), 0), 2)     AS jitter_pct,
            ROUND(SUM(is_low_quality) * 100.0 / NULLIF(COUNT(*), 0), 2) AS low_quality_pct
        FROM silver_device_diagnostics
        WHERE {_CORR_WHERE}
          AND dt >= '{date_start}'
          AND dt <= '{date_end}'
        GROUP BY grid_x, grid_y
    """).fetch_arrow_table()
    return pl.from_arrow(arrow)


@st.cache_data(show_spinner="⏱️ Lasketaan samanaikainen tiheys…", ttl=300)
def fetch_concurrent_density(date_start: str, date_end: str, grid_cm: int = 300) -> pl.DataFrame:
    """Q statistics grouped by concurrent cart count — aggregated fully in SQL."""
    conn = _get_conn()
    arrow = conn.execute(f"""
        WITH bucketed AS (
            SELECT
                DATE_TRUNC('minute', aika)                          AS minuutti,
                FLOOR(x / {grid_cm}.0) * {grid_cm}                 AS grid_x,
                FLOOR(y / {grid_cm}.0) * {grid_cm}                 AS grid_y,
                COUNT(DISTINCT node_id)                             AS concurrent_carts,
                AVG(q)                                              AS avg_q,
                AVG(CAST(is_jitter AS DOUBLE)) * 100.0             AS jitter_pct
            FROM silver_device_diagnostics
            WHERE {_CORR_WHERE}
              AND dt >= '{date_start}'
              AND dt <= '{date_end}'
            GROUP BY minuutti, grid_x, grid_y
        ),
        corr_val AS (
            SELECT
                CORR(CAST(concurrent_carts AS DOUBLE), avg_q)       AS pearson_r_q,
                CORR(CAST(concurrent_carts AS DOUBLE), jitter_pct)  AS pearson_r_jitter,
                MIN(concurrent_carts)                                AS cart_min,
                MAX(concurrent_carts)                                AS cart_max,
                ROUND(AVG(concurrent_carts), 2)                      AS cart_mean,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY concurrent_carts) AS cart_median,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY concurrent_carts) AS cart_p95
            FROM bucketed
            WHERE concurrent_carts >= 1
        ),
        aggregated AS (
            SELECT
                concurrent_carts,
                COUNT(*)                                                            AS n_observations,
                AVG(avg_q)                                                          AS mean_q,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY avg_q)                AS q25,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_q)                AS median_q,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY avg_q)                AS q75,
                PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY avg_q)                AS q05,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY avg_q)                AS q95,
                AVG(jitter_pct)                                                     AS mean_jitter,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY jitter_pct)           AS j25,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY jitter_pct)           AS median_jitter,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY jitter_pct)           AS j75,
                PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY jitter_pct)           AS j05,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY jitter_pct)           AS j95,
                ROUND(SUM(CASE WHEN jitter_pct > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_buckets_with_jitter
            FROM bucketed
            WHERE concurrent_carts >= 1
            GROUP BY concurrent_carts
        )
        SELECT a.*, c.pearson_r_q, c.pearson_r_jitter,
               c.cart_min, c.cart_max, c.cart_mean, c.cart_median, c.cart_p95
        FROM aggregated a, corr_val c
        ORDER BY concurrent_carts
    """).fetch_arrow_table()
    return pl.from_arrow(arrow)


@st.cache_resource(show_spinner=False)
def load_image(path: Path) -> Image.Image:
    return Image.open(path)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("## ⚙️ Suodattimet")

dt_min, dt_max = fetch_date_range()

date_range = st.sidebar.date_input(
    "Aikaväli",
    value=(dt_min, dt_max),
    min_value=dt_min,
    max_value=dt_max,
)
if len(date_range) != 2:
    st.sidebar.info("Valitse alku- ja loppupäivä.")
    st.stop()
date_start, date_end = str(date_range[0]), str(date_range[1])

st.sidebar.markdown("---")

min_pings = st.sidebar.slider(
    "Minimi pingejä per ruutu",
    min_value=10, max_value=5000, value=200, step=10,
    help="Poistaa tilastollisesti epäluotettavat ruudut joissa on vähän havaintoja",
)

metric_label = st.sidebar.radio(
    "Näytettävä mittari",
    options=["Heikkolaatuiset pingit (%)", "Jitter (%)", "Mediaani Q-arvo"],
    index=0,
)

opacity = st.sidebar.slider("Kartan läpinäkyvyys", 0.3, 1.0, 0.75, 0.05)

st.sidebar.markdown("---")
density_grid_m = st.sidebar.select_slider(
    "Ruutukoko (samanaikaisuusanalyysi)",
    options=[1, 2, 3, 5, 10],
    value=3,
    format_func=lambda v: f"{v}×{v} m",
    help="Isompi ruutu = enemmän kärryjä per solu = parempi samanaikaisuusdata",
)
density_grid_cm = density_grid_m * 100

df = fetch_verkko(date_start, date_end)
df_filtered = df.filter(pl.col("total_pings") >= min_pings)

metric_col, colorscale, zmin, zmax, low_is_bad = {
    "Heikkolaatuiset pingit (%)": ("low_quality_pct", "RdYlGn_r", 0,   50,  True),
    "Jitter (%)":                 ("jitter_pct",      "RdYlGn_r", 0,   10,  True),
    "Mediaani Q-arvo":            ("median_quality",  "RdYlGn",   0,  255,  False),
}[metric_label]

# ---------------------------------------------------------------------------
# Dead zones – grid cells inside the floor bounds with zero pings ever
# ---------------------------------------------------------------------------
all_grid_cells = pl.DataFrame({
    "grid_x": pl.Series([x for x in range(0, MAP_MAX_X, CELL_SIZE) for _ in range(0, MAP_MAX_Y, CELL_SIZE)], dtype=pl.Float64),
    "grid_y": pl.Series([y for _ in range(0, MAP_MAX_X, CELL_SIZE) for y in range(0, MAP_MAX_Y, CELL_SIZE)], dtype=pl.Float64),
})
dead_zones = all_grid_cells.join(
    df.select(["grid_x", "grid_y"]),
    on=["grid_x", "grid_y"],
    how="anti",
)

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
total_cells      = len(df_filtered)
good_coverage    = df_filtered.filter(pl.col("low_quality_pct") < 20)
problem_cells    = df_filtered.filter(pl.col("low_quality_pct") >= 50)
avg_lq           = df_filtered["low_quality_pct"].mean()
avg_jitter       = df_filtered["jitter_pct"].mean()
n_dead           = len(dead_zones)
total_floor_cells = len(all_grid_cells)
dead_pct         = n_dead / total_floor_cells * 100

st.markdown('<div class="section-title">📊 Verkon tila – yhteenveto</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6 = st.columns(6)
metrics = [
    (c1, "Aktiivisia ruutuja",           f"{total_cells:,}",                         ""),
    (c2, "Katvealueet (0 pingiä)",       f"{n_dead:,}",                              "bad" if dead_pct > 30 else "warn" if dead_pct > 15 else ""),
    (c3, "Hyvä kattavuus (<20% heikko)", f"{len(good_coverage)/total_cells*100:.0f}%", ""),
    (c4, "Ongelmaruutuja (≥50% heikko)", f"{len(problem_cells)}",                    "bad" if len(problem_cells) > 50 else "warn"),
    (c5, "Heikko signaali ka",           f"{avg_lq:.1f}%",                           "bad" if avg_lq > 20 else "warn" if avg_lq > 10 else ""),
    (c6, "Jitter ka",                    f"{avg_jitter:.1f}%",                       "bad" if avg_jitter > 5 else ""),
]
for col, label, val, cls in metrics:
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="val {cls}">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Heatmap helper
# ---------------------------------------------------------------------------
def build_heatmap(df_plot: pl.DataFrame, z_col: str, cs: str,
                  z0: float, z1: float, title: str, img: Image.Image,
                  cell_opacity: float,
                  dz: pl.DataFrame | None = None) -> go.Figure:
    """Overlay a signal-quality heatmap on the floor plan."""
    all_x = sorted(df_plot["grid_x"].unique().to_list())
    all_y = sorted(df_plot["grid_y"].unique().to_list())

    x_idx = {x: i for i, x in enumerate(all_x)}
    y_idx = {y: i for i, y in enumerate(all_y)}

    z = np.full((len(all_y), len(all_x)), np.nan)
    for row in df_plot.iter_rows(named=True):
        z[y_idx[row["grid_y"]], x_idx[row["grid_x"]]] = row[z_col]

    fig = go.Figure()
    fig.add_layout_image(dict(
        source=img, xref="x", yref="y", x=0, y=0,
        sizex=MAP_MAX_X, sizey=MAP_MAX_Y, sizing="stretch",
        opacity=1.0, layer="below", xanchor="left", yanchor="top",
    ))

    # Dead zones: grey squares for cells with zero pings ever
    if dz is not None and not dz.is_empty():
        dz_x = sorted(dz["grid_x"].unique().to_list())
        dz_y = sorted(dz["grid_y"].unique().to_list())
        dz_x_idx = {x: i for i, x in enumerate(dz_x)}
        dz_y_idx = {y: i for i, y in enumerate(dz_y)}
        z_dead = np.full((len(dz_y), len(dz_x)), np.nan)
        for row in dz.iter_rows(named=True):
            z_dead[dz_y_idx[row["grid_y"]], dz_x_idx[row["grid_x"]]] = 1.0
        fig.add_trace(go.Heatmap(
            x=dz_x, y=dz_y, z=z_dead,
            colorscale=[[0, "rgba(50,50,50,0.55)"], [1, "rgba(50,50,50,0.55)"]],
            showscale=False,
            xgap=1, ygap=1,
            name="Katvealue",
            hovertemplate="x=%{x} cm<br>y=%{y} cm<br>Katvealue – ei yhtään pingiä<extra></extra>",
        ))

    fig.add_trace(go.Heatmap(
        x=all_x, y=all_y, z=z,
        colorscale=cs,
        zmin=z0, zmax=z1,
        opacity=cell_opacity,
        xgap=1, ygap=1,
        colorbar=dict(title=title, thickness=14, len=0.6),
        hovertemplate="x=%{x} cm<br>y=%{y} cm<br>" + title + "=%{z:.1f}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, MAP_MAX_X], showgrid=False, showticklabels=False)
    fig.update_yaxes(range=[MAP_MAX_Y, 0], showgrid=False, showticklabels=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=500, margin=dict(l=0, r=60, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------------------------------------------------------------------------
# Main heatmap
# ---------------------------------------------------------------------------
st.markdown(f'<div class="section-title">🗺️ Kattavuuskartta – {metric_label}</div>',
            unsafe_allow_html=True)

if IMAGE_PATH.exists():
    img = load_image(IMAGE_PATH)
    fig = build_heatmap(df_filtered, metric_col, colorscale, zmin, zmax,
                        metric_label, img, opacity, dz=dead_zones)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Pohjapiirros ei löydy (image/kauppa2.png).")

# ---------------------------------------------------------------------------
# Worst cells table
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">⚠️ Ongelmaruudut – heikoin kattavuus</div>',
            unsafe_allow_html=True)

worst = (
    df_filtered
    .sort("low_quality_pct", descending=True)
    .head(20)
    .select(["grid_x", "grid_y", "total_pings", "median_quality",
             "low_quality_pct", "jitter_pct"])
)
st.dataframe(worst.to_arrow(), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Quality distribution histogram
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📊 Heikkolaatuisten pingien jakauma ruuduittain</div>',
            unsafe_allow_html=True)

hist_vals, bin_edges = np.histogram(
    df_filtered["low_quality_pct"].to_numpy(), bins=40, range=(0, 100)
)
bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()

dist_fig = go.Figure()
dist_fig.add_trace(go.Bar(
    x=bin_centers, y=hist_vals.tolist(),
    marker_color=[
        "#22c55e" if x < 20 else "#fbbf24" if x < 50 else "#ef4444"
        for x in bin_centers
    ],
    opacity=0.85,
))
dist_fig.add_vline(x=20, line_color="#fbbf24", line_width=2, line_dash="dash",
                   annotation_text="Hyvä (<20%)", annotation_position="top right",
                   annotation_font_size=11)
dist_fig.add_vline(x=50, line_color="#ef4444", line_width=2, line_dash="dash",
                   annotation_text="Ongelma (≥50%)", annotation_position="top right",
                   annotation_font_size=11)
dist_fig.update_layout(
    xaxis=dict(title="Heikkolaatuisten pingien osuus (%)"),
    yaxis=dict(title="Ruutujen määrä"),
    height=280, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    showlegend=False,
)
st.plotly_chart(dist_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Coverage by zone (x-axis quartiles)
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📍 Laatu kaupan vyöhykkeittäin (x-akseli)</div>',
            unsafe_allow_html=True)
st.caption("Kauppa jaettu neljään vyöhykkeeseen x-koordinaatin mukaan. "
           "Auttaa tunnistamaan ankkuriverkon ongelmakohdat.")

zone_labels = ["Vyöhyke 1 (vasen)", "Vyöhyke 2", "Vyöhyke 3", "Vyöhyke 4 (oikea)"]
zone_width  = MAP_MAX_X / 4
zone_fig    = go.Figure()

for i, label in enumerate(zone_labels):
    x0 = i * zone_width
    x1 = (i + 1) * zone_width
    zone_df = df_filtered.filter((pl.col("grid_x") >= x0) & (pl.col("grid_x") < x1))
    if zone_df.is_empty():
        continue
    lq_vals = zone_df["low_quality_pct"].to_list()
    zone_fig.add_trace(go.Box(
        y=lq_vals, name=label,
        marker_color=["#22c55e", "#84cc16", "#fbbf24", "#f97316"][i],
        boxmean=True,
    ))

zone_fig.add_hline(y=20, line_color="#fbbf24", line_width=1, line_dash="dot",
                   annotation_text="Hyvä-raja (20%)")
zone_fig.add_hline(y=50, line_color="#ef4444", line_width=1, line_dash="dot",
                   annotation_text="Ongelma-raja (50%)")
zone_fig.update_layout(
    yaxis=dict(title="Heikko signaali (%)"),
    height=320, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    showlegend=False,
)
st.plotly_chart(zone_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Ping density map – all pings, no quality filter
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📍 Pingien levinneisyys – kaikki havainnot</div>',
            unsafe_allow_html=True)
st.caption("Kaikki pingit valitulla aikavälillä ilman laatu- tai pingimääräsuodatusta.")

if IMAGE_PATH.exists():
    all_x = sorted(df["grid_x"].unique().to_list())
    all_y = sorted(df["grid_y"].unique().to_list())
    x_idx = {x: i for i, x in enumerate(all_x)}
    y_idx = {y: i for i, y in enumerate(all_y)}
    z_density = np.full((len(all_y), len(all_x)), np.nan)
    for row in df.iter_rows(named=True):
        z_density[y_idx[row["grid_y"]], x_idx[row["grid_x"]]] = row["total_pings"]

    density_fig = go.Figure()
    density_fig.add_layout_image(dict(
        source=load_image(IMAGE_PATH), xref="x", yref="y", x=0, y=0,
        sizex=MAP_MAX_X, sizey=MAP_MAX_Y, sizing="stretch",
        opacity=1.0, layer="below", xanchor="left", yanchor="top",
    ))
    density_fig.add_trace(go.Heatmap(
        x=all_x, y=all_y, z=z_density,
        colorscale="Plasma",
        opacity=opacity,
        xgap=1, ygap=1,
        colorbar=dict(title="Pingiä", thickness=14, len=0.6),
        hovertemplate="x=%{x} cm<br>y=%{y} cm<br>Pingiä=%{z:,.0f}<extra></extra>",
    ))
    density_fig.update_xaxes(range=[0, MAP_MAX_X], showgrid=False, showticklabels=False)
    density_fig.update_yaxes(range=[MAP_MAX_Y, 0], showgrid=False, showticklabels=False,
                              scaleanchor="x", scaleratio=1)
    density_fig.update_layout(
        height=500, margin=dict(l=0, r=60, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(density_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Correlation analysis helper
# ---------------------------------------------------------------------------
def _corr_label(r: float) -> tuple[str, str]:
    abs_r = abs(r)
    strength = "vahva" if abs_r >= 0.7 else "kohtalainen" if abs_r >= 0.4 else "heikko"
    direction = "negatiivinen" if r < 0 else "positiivinen"
    return strength, direction


def show_correlation(x_vals, y_vals, weights, x_label: str, y_label: str,
                     r_label: str, interpretation: str):
    r = float(np.corrcoef(x_vals, y_vals)[0, 1])
    coeffs = np.polyfit(x_vals, y_vals, 1)
    x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
    y_line = np.polyval(coeffs, x_line)
    strength, direction = _corr_label(r)

    col_r, col_exp = st.columns([1, 3])
    col_r.markdown(
        f'<div class="metric-card"><div class="val">{r:.3f}</div>'
        f'<div class="lbl">Pearsonin r ({r_label})</div></div>',
        unsafe_allow_html=True,
    )
    col_exp.info(f"Korrelaatio on **{strength} ja {direction}** (r = {r:.3f}). {interpretation}")

    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=x_vals.tolist(), y=y_vals.tolist(),
        mode="markers",
        marker=dict(
            size=6, color=weights.tolist(), colorscale="Viridis", opacity=0.6,
            colorbar=dict(title="Pingiä", thickness=12, len=0.5), line=dict(width=0),
        ),
        hovertemplate=f"{x_label}=%{{x:.1f}}<br>{y_label}=%{{y:.2f}}<extra></extra>",
        name="Ruudut",
    ))
    fig.add_trace(go.Scatter(
        x=x_line.tolist(), y=y_line.tolist(),
        mode="lines", line=dict(color="#ef4444", width=2, dash="dash"),
        name=f"Trendi (r={r:.3f})",
    ))
    fig.update_layout(
        xaxis=dict(title=x_label), yaxis=dict(title=y_label),
        height=350, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        legend=dict(font=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Correlation analyses
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">🔗 Korrelaatioanalyysit</div>', unsafe_allow_html=True)

corr_df = fetch_verkko_corr(date_start, date_end).select(
    ["median_quality", "jitter_pct", "low_quality_pct", "total_pings"]
).drop_nulls()

if len(corr_df) > 1:
    q      = corr_df["median_quality"].to_numpy()
    jitter = corr_df["jitter_pct"].to_numpy()
    pings  = corr_df["total_pings"].to_numpy()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Jitter vs Q-arvo",
        "Pingimäärä vs Q-arvo",
        "Pingimäärä vs Jitter",
        "Samanaikaiset kärryt vs Q-arvo",
        "Samanaikaiset kärryt vs Jitter",
    ])

    with tab1:
        st.caption("Onko korkea jitter yhteydessä heikkoon signaaliin?")
        show_correlation(
            q, jitter, pings,
            x_label="Mediaani Q-arvo (suurempi = parempi)",
            y_label="Jitter (%)",
            r_label="jitter vs Q",
            interpretation=(
                "Korkea Q-arvo liittyy matalaan jitteriin — signaalilaatu ja "
                "paikannusstabiliteetti kulkevat käsi kädessä."
                if np.corrcoef(q, jitter)[0, 1] < -0.3
                else "Q-arvon ja jitterin välillä ei ole selkeää lineaarista yhteyttä."
            ),
        )

    with tab2:
        st.caption("Onko vilkkailla alueilla parempi vai heikompi signaali?")
        show_correlation(
            pings, q, pings,
            x_label="Pingejä per ruutu (liikennemäärä)",
            y_label="Mediaani Q-arvo",
            r_label="pingimäärä vs Q",
            interpretation=(
                "Vilkkaammilla alueilla signaali on parempi — ankkuriverkko on "
                "optimoitu pääkäytäville."
                if np.corrcoef(pings, q)[0, 1] > 0.3
                else "Liikennemäärällä ja signaalin laadulla ei ole selkeää yhteyttä — "
                     "verkko toimii tasaisesti riippumatta alueen vilkkaudesta."
            ),
        )

    with tab3:
        st.caption("Aiheuttaako suuri tagitiheys enemmän jitteriä? (UWB-interferenssi)")
        show_correlation(
            pings, jitter, pings,
            x_label="Pingejä per ruutu (liikennemäärä)",
            y_label="Jitter (%)",
            r_label="pingimäärä vs jitter",
            interpretation=(
                "Vilkkaammilla alueilla esiintyy enemmän jitteriä — viittaa UWB-kanavien "
                "ruuhkautumiseen kun useita tageja on samanaikaisesti aktiivisena."
                if np.corrcoef(pings, jitter)[0, 1] > 0.3
                else "Liikennemäärä ei selitä jitteriä — interferenssi ei ole "
                     "merkittävä ongelma tässä verkossa."
            ),
        )
    with tab4:
        st.caption(
            "Jokaisessa 1 minuutin aikaikkunassa lasketaan kuinka monta eri kärryä "
            "on samassa ruudussa yhtä aikaa — laskeeko Q kun kärryjä on enemmän?"
        )
        cd = fetch_concurrent_density(date_start, date_end, density_grid_cm)
        if len(cd) > 1:
            # r computed in SQL on all raw bucketed rows — not on group means
            r_cd = float(cd["pearson_r_q"][0])
            strength_cd, direction_cd = _corr_label(r_cd)

            col_r2, col_exp2 = st.columns([1, 3])
            col_r2.markdown(
                f'<div class="metric-card"><div class="val">{r_cd:.3f}</div>'
                f'<div class="lbl">Pearsonin r (samanaikaiset kärryt vs Q)</div></div>',
                unsafe_allow_html=True,
            )
            col_exp2.info(
                f"Korrelaatio on **{strength_cd} ja {direction_cd}** (r = {r_cd:.3f}). "
                + (
                    "Mitä enemmän kärryjä samassa ruudussa samanaikaisesti, sitä heikompi signaali — "
                    "viittaa UWB-kanavien ruuhkautumiseen."
                    if r_cd < -0.2
                    else "Samanaikaisella kärrytiheydellä ei ole selkeää vaikutusta signaalin laatuun — "
                         "heikot alueet johtuvat todennäköisesti rakenteellisista tekijöistä kuten hyllyistä."
                )
            )

            cd_plot = cd.filter(pl.col("concurrent_carts") <= 10)
            xs      = cd_plot["concurrent_carts"].to_list()
            box_fig = go.Figure()
            box_fig.add_trace(go.Scatter(
                x=xs + xs[::-1], y=cd_plot["q95"].to_list() + cd_plot["q05"].to_list()[::-1],
                fill="toself", fillcolor="rgba(99,102,241,0.12)", line=dict(width=0),
                hoverinfo="skip", showlegend=False,
            ))
            box_fig.add_trace(go.Scatter(
                x=xs + xs[::-1], y=cd_plot["q75"].to_list() + cd_plot["q25"].to_list()[::-1],
                fill="toself", fillcolor="rgba(99,102,241,0.25)", line=dict(width=0),
                hoverinfo="skip", name="IQR (Q25–Q75)",
            ))
            box_fig.add_trace(go.Scatter(
                x=xs, y=cd_plot["median_q"].to_list(),
                mode="lines+markers", line=dict(color="#6366f1", width=3),
                marker=dict(size=8), name="Mediaani Q",
                hovertemplate="%{x} kärryä<br>Mediaani Q: %{y:.1f}<extra></extra>",
            ))
            box_fig.update_layout(
                xaxis=dict(title="Samanaikaisia kärryjä samassa ruudussa (1 min ikkuna)",
                           tickmode="array", tickvals=xs),
                yaxis=dict(title="Q-arvo"),
                height=380, margin=dict(l=50, r=20, t=10, b=50),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
                legend=dict(orientation="h", y=1.1, font=dict(size=11)),
            )
            st.plotly_chart(box_fig, use_container_width=True)
        else:
            st.info("Ei tarpeeksi dataa.")

    with tab5:
        st.caption(
            "Jokaisessa 1 minuutin aikaikkunassa lasketaan kuinka monta eri kärryä "
            "on samassa ruudussa yhtä aikaa — lisääkö kärryjen tiheys jitteriä?"
        )
        cd5 = fetch_concurrent_density(date_start, date_end, density_grid_cm)
        if len(cd5) > 1:
            # --- Concurrent cart distribution stats ---
            row0 = cd5.row(0, named=True)
            st.markdown('<div class="section-title">📊 Samanaikaisten kärryjen jakauma</div>', unsafe_allow_html=True)
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            for col, label, val in [
                (sc1, "Minimi",   f"{int(row0['cart_min'])}"),
                (sc2, "Mediaani", f"{int(row0['cart_median'])}"),
                (sc3, "Keskiarvo",f"{row0['cart_mean']:.1f}"),
                (sc4, "P95",      f"{int(row0['cart_p95'])}"),
                (sc5, "Maksimi",  f"{int(row0['cart_max'])}"),
            ]:
                col.markdown(
                    f'<div class="metric-card"><div class="val">{val}</div>'
                    f'<div class="lbl">{label}</div></div>',
                    unsafe_allow_html=True,
                )

            r_jitter = float(cd5["pearson_r_jitter"][0])
            strength_j, direction_j = _corr_label(r_jitter)

            col_rj, col_expj = st.columns([1, 3])
            col_rj.markdown(
                f'<div class="metric-card"><div class="val">{r_jitter:.3f}</div>'
                f'<div class="lbl">Pearsonin r (samanaikaiset kärryt vs Jitter-%)</div></div>',
                unsafe_allow_html=True,
            )
            col_expj.info(
                f"Korrelaatio on **{strength_j} ja {direction_j}** (r = {r_jitter:.3f}). "
                + (
                    "Mitä enemmän kärryjä samassa ruudussa samanaikaisesti, sitä enemmän jitteriä — "
                    "viittaa UWB-signaalien keskinäiseen häiriöön (multipath / crowding)."
                    if r_jitter > 0.2
                    else "Samanaikaisella kärrytiheydellä ei ole selkeää vaikutusta jitteriin — "
                         "jitterin syy on todennäköisesti rakenteellinen eikä ruuhkaperusteinen."
                )
            )

            cd5_plot = cd5.filter(pl.col("concurrent_carts") <= 10)
            xs5      = cd5_plot["concurrent_carts"].to_list()
            jitter_fig = go.Figure()
            jitter_fig.add_trace(go.Scatter(
                x=xs5, y=cd5_plot["pct_buckets_with_jitter"].to_list(),
                mode="lines+markers", line=dict(color="#f97316", width=3),
                marker=dict(size=8), name="% aikaikkunoista joissa jitteriä",
                hovertemplate="%{x} kärryä<br>%{y:.1f}% aikaikkunoista sisälsi jitteriä<extra></extra>",
            ))
            jitter_fig.update_layout(
                xaxis=dict(title="Samanaikaisia kärryjä samassa ruudussa (1 min ikkuna)",
                           tickmode="array", tickvals=xs5),
                yaxis=dict(title="% aikaikkunoista joissa jitteriä", range=[0, 100]),
                height=340, margin=dict(l=50, r=20, t=10, b=50),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
                showlegend=False,
            )
            st.plotly_chart(jitter_fig, use_container_width=True)
        else:
            st.info("Ei tarpeeksi dataa.")

else:
    st.info("Ei tarpeeksi dataa korrelaatioanalyysiin.")

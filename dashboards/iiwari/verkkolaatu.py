"""
Verkkolaatu – UWB-verkon laadun heatmap-analyysi
=================================================
Ruudukkopohjainen (100 cm × 100 cm) visualisointi pingausten laadusta,
heikkolaatuisista pingauksista ja jitteristä kaupan alueella.

Kutsutaan iiwari.py:stä: dashboards.iiwari.verkkolaatu.render()
"""

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

_CSS = """
<style>
.vl-hero {
    background: linear-gradient(135deg, #0a1f1a, #0d3321, #0f4c35);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.vl-hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.vl-hero p  { font-size: 1rem; color: #6ee7b7; margin: 0; }
.vl-metric {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid #334155; border-radius: 14px;
    padding: 1.2rem 1.4rem; text-align: center; color: white;
}
.vl-metric .val { font-size: 2.2rem; font-weight: 700; color: #34d399; }
.vl-metric .lbl { font-size: 0.78rem; color: #94a3b8; margin-top: 0.3rem; font-weight: 500; }
.vl-metric .sub { font-size: 0.7rem; color: #64748b; margin-top: 0.15rem; }
.vl-section {
    font-size: 1.1rem; font-weight: 600; color: var(--text-color, #e2e8f0);
    margin: 1.5rem 0 0.6rem 0; border-left: 4px solid #10b981; padding-left: 0.6rem;
}
</style>
"""


@st.cache_resource(show_spinner=False)
def _get_conn():
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb ei löydy. Aja ensin `dbt run`.")
    st.stop()


@st.cache_data(show_spinner="📡 Haetaan verkkolaatu…", ttl=300)
def _load() -> pl.DataFrame:
    conn = _get_conn()
    return conn.execute(f"""
        SELECT grid_x, grid_y, total_pings,
               median_quality, min_quality,
               low_quality_pings, jitter_pings, low_quality_pct
        FROM f_verkko_laatu
        ORDER BY grid_x, grid_y
    """).pl()


def _kpi(col, val, label, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="vl-metric">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def _load_image(path: Path) -> Image.Image:
    return Image.open(path)


def _heatmap(df: pl.DataFrame, z_col: str, title: str, colorscale: str, zmin=None, zmax=None, log_scale=False):
    all_x = sorted(df["grid_x"].unique().to_list())
    all_y = sorted(df["grid_y"].unique().to_list())
    x_idx = {x: i for i, x in enumerate(all_x)}
    y_idx = {y: i for i, y in enumerate(all_y)}

    z_raw = np.full((len(all_y), len(all_x)), np.nan)
    for row in df.iter_rows(named=True):
        z_raw[y_idx[row["grid_y"]], x_idx[row["grid_x"]]] = row[z_col]

    z = np.log1p(z_raw) if log_scale else z_raw
    hover_z = z_raw

    fig = go.Figure()

    if IMAGE_PATH.exists():
        fig.add_layout_image(dict(
            source=_load_image(IMAGE_PATH),
            xref="x", yref="y", x=0, y=0,
            sizex=MAP_MAX_X, sizey=MAP_MAX_Y,
            sizing="stretch", opacity=1.0, layer="below",
            xanchor="left", yanchor="top",
        ))

    fig.add_trace(go.Heatmap(
        x=all_x, y=all_y, z=z,
        customdata=hover_z,
        colorscale=colorscale,
        zmin=zmin, zmax=zmax,
        opacity=0.75,
        xgap=1, ygap=1,
        colorbar=dict(title=title, thickness=14, len=0.6, tickvals=[], ticktext=[]),
        hovertemplate=f"x=%{{x}} cm<br>y=%{{y}} cm<br>{title}=%{{customdata:.0f}}<extra></extra>",
    ))

    fig.update_xaxes(range=[0, MAP_MAX_X], showgrid=False, showticklabels=False)
    fig.update_yaxes(range=[MAP_MAX_Y, 0], showgrid=False, showticklabels=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=520, margin=dict(l=0, r=60, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="vl-hero">
        <h1>📡 Verkkolaatu</h1>
        <p>UWB-verkon laadun spatiaalinen analyysi — pingausten laatu, heikkolaatuiset alueet ja jitter kaupan pohjapiirrostasolla</p>
    </div>
    """, unsafe_allow_html=True)

    df = _load()

    if df.is_empty():
        st.warning("Ei dataa tietokannassa.")
        st.stop()

    # --- KPIs ---
    st.markdown('<div class="vl-section">📊 Yhteenveto</div>', unsafe_allow_html=True)

    total_pings = int(df["total_pings"].sum())
    median_q = float(df["median_quality"].median())
    avg_lq_pct = float(df["low_quality_pct"].mean())
    n_cells = len(df)
    high_lq_cells = int((df["low_quality_pct"] > 10).sum())
    total_jitter = int(df["jitter_pings"].sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _kpi(c1, f"{total_pings:,}", "Pingauksia yhteensä")
    _kpi(c2, f"{median_q:.0f}", "Mediaanilaatu (q)", "koko kauppa")
    _kpi(c3, f"{avg_lq_pct:.1f} %", "Heikkolaatuisia ka", "per ruutu")
    _kpi(c4, str(n_cells), "Ruutuja (100×100 cm)")
    _kpi(c5, str(high_lq_cells), "Ruutuja >10 % heikkolaatuisia")
    _kpi(c6, f"{total_jitter:,}", "Jitter-pingauksia")

    # --- Heatmap controls ---
    st.markdown('<div class="vl-section">🗺️ Spatiaalinen heatmap</div>', unsafe_allow_html=True)

    metric_opts = {
        "Mediaanilaatu (q)": ("median_quality", "RdYlGn", None, None, False),
        "Heikkolaatuisia (%)": ("low_quality_pct", "Reds", 0, None, False),
        "Jitter-pingauksia": ("jitter_pings", "OrRd", 0, None, True),
        "Pingauksia yhteensä": ("total_pings", "Blues", 0, None, True),
    }
    selected = st.selectbox("Näytettävä mittari", list(metric_opts.keys()))
    z_col, colorscale, zmin, zmax, log_scale = metric_opts[selected]

    ping_p95 = float(df["total_pings"].quantile(0.95))
    df_map = df.filter(pl.col("total_pings") <= ping_p95)
    fig_map = _heatmap(df_map, z_col, selected, colorscale, zmin, zmax, log_scale)
    st.plotly_chart(fig_map, use_container_width=True)

    # --- Quality distribution histogram ---
    st.markdown('<div class="vl-section">📊 Laadun jakauma ruuduittain</div>', unsafe_allow_html=True)

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        q_vals = df["median_quality"].to_list()
        fig_qh = go.Figure(go.Histogram(
            x=q_vals, nbinsx=40,
            marker_color="#34d399", opacity=0.85,
            hovertemplate="q: %{x}<br>Ruutuja: %{y}<extra></extra>",
        ))
        fig_qh.update_layout(
            title="Mediaanilaatu per ruutu",
            height=280, margin=dict(l=50, r=20, t=40, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Mediaanilaatu (q)"), yaxis=dict(title="Ruutuja"),
            showlegend=False,
        )
        st.plotly_chart(fig_qh, use_container_width=True)

    with col_h2:
        lq_vals = df["low_quality_pct"].to_list()
        fig_lqh = go.Figure(go.Histogram(
            x=lq_vals, nbinsx=40,
            marker_color="#f87171", opacity=0.85,
            hovertemplate="Heikkolaatuisia: %{x:.1f}%<br>Ruutuja: %{y}<extra></extra>",
        ))
        fig_lqh.update_layout(
            title="Heikkolaatuisten pingausten osuus per ruutu",
            height=280, margin=dict(l=50, r=20, t=40, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Heikkolaatuisia (%)"), yaxis=dict(title="Ruutuja"),
            showlegend=False,
        )
        st.plotly_chart(fig_lqh, use_container_width=True)

    # --- Top worst cells ---
    st.markdown('<div class="vl-section">🔴 Heikoimmat ruudut (heikkolaatuisia > 5 %)</div>', unsafe_allow_html=True)

    worst = (
        df.filter(pl.col("low_quality_pct") > 5)
        .sort("low_quality_pct", descending=True)
        .head(20)
        .select(["grid_x", "grid_y", "total_pings", "median_quality", "low_quality_pct", "jitter_pings"])
    )
    if worst.is_empty():
        st.success("Ei ruutuja joissa heikkolaatuisia yli 5 %.")
    else:
        st.dataframe(worst.to_pandas(), use_container_width=True)

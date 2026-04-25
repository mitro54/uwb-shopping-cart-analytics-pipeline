"""
Paikannustarkkuus laitteittain – yöaikaiset tarkkuusmittarit
=============================================================
Laitekohtainen näkymä: sijaintipilvi, CEP-ympyrät, drift ja
tarkkuustrendi useamman yön yli.

Kutsutaan iiwari.py:stä: dashboards.iiwari.paikannustarkkuus.render()
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH  = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"
IMAGE_PATH   = PROJECT_ROOT / "image" / "kauppa2.png"
MAP_MAX_X, MAP_MAX_Y = 10406, 5220

_CSS = """
<style>
.pt-hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.pt-hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.pt-hero p  { font-size: 1rem; color: #a5b4fc; margin: 0; }
.pt-metric {
    background: #1e1b4b; border: 1px solid #3730a3; border-radius: 12px;
    padding: 1rem 1.2rem; text-align: center; color: white;
}
.pt-metric .val { font-size: 2rem; font-weight: 700; color: #818cf8; }
.pt-metric .lbl { font-size: 0.8rem; color: #94a3b8; margin-top: 0.2rem; }
.pt-section {
    font-size: 1.1rem; font-weight: 600; color: var(--text-color, #e2e8f0);
    margin: 1.2rem 0 0.6rem 0; border-left: 4px solid #6366f1; padding-left: 0.6rem;
}
</style>
"""

DISPLAY_COLS = [
    "yo_paiva", "node_id", "n_pings", "rmse_2d", "cep50", "cep68", "cep95",
    "jitter_ka_cm", "jitter_p95_cm", "drift_x_cmh", "drift_y_cmh",
    "outlier_pct", "avg_q", "low_quality_pct",
]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _get_conn() -> duckdb.DuckDBPyConnection:
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb ei löydy. Aja ensin `dbt run`.")
    st.stop()


@st.cache_data(show_spinner="📅 Haetaan gold-data…", ttl=300)
def _fetch_gold() -> pl.DataFrame:
    conn = _get_conn()
    return conn.execute("SELECT * FROM f_paikannustarkkuus").pl().sort(["yo_paiva", "node_id"])


@st.cache_data(show_spinner="🔗 Haetaan yön raakadata…", ttl=300)
def _fetch_night(node_id: str, yo_paiva: str, cx: float, cy: float) -> pl.DataFrame:
    conn      = _get_conn()
    next_date = str(_date.fromisoformat(yo_paiva) + timedelta(days=1))
    arrow = conn.execute(f"""
        WITH tz AS (
            SELECT node_id,
                   timezone('Europe/Helsinki', aika::TIMESTAMPTZ) AS aika_hki,
                   x, y, "q", is_low_quality, is_jitter
            FROM silver_device_diagnostics
            WHERE node_id = '{node_id}'
              AND x IS NOT NULL AND y IS NOT NULL
              AND x >= 500
        )
        SELECT aika_hki,
               EXTRACT('hour' FROM aika_hki)::INT              AS tunti,
               x, y,
               ROUND(x - ({cx}), 1)                              AS dx,
               ROUND(y - ({cy}), 1)                              AS dy,
               ROUND(SQRT(POWER(x-({cx}),2)+POWER(y-({cy}),2)),1) AS dist,
               "q", is_low_quality, is_jitter
        FROM tz
        WHERE (CAST(aika_hki AS DATE) = CAST('{yo_paiva}' AS DATE)
               AND EXTRACT('hour' FROM aika_hki) >= 22)
           OR (CAST(aika_hki AS DATE) = CAST('{next_date}' AS DATE)
               AND EXTRACT('hour' FROM aika_hki) < 7)
        ORDER BY aika_hki
    """).to_arrow_table()
    return pl.from_arrow(arrow)


@st.cache_resource(show_spinner=False)
def _load_image(path: Path) -> Image.Image:
    return Image.open(path)


def _metric(col, val, label):
    col.markdown(
        f'<div class="pt-metric"><div class="val">{val}</div>'
        f'<div class="lbl">{label}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="pt-hero">
        <h1>🎯 Paikannustarkkuus laitteittain</h1>
        <p>Laitekohtainen yöanalyysi — sijaintipilvi, CEP-ympyrät, drift ja tarkkuustrendi</p>
    </div>
    """, unsafe_allow_html=True)

    df_all = _fetch_gold()
    if df_all.is_empty():
        st.warning("Gold-taulussa ei ole dataa. Aja ensin `dbt run`.")
        st.stop()

    # --- Filters in sidebar ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Suodattimet")

    all_nodes     = sorted(df_all["node_id"].unique().to_list())
    selected_node = st.sidebar.selectbox("📡 Laite (node_id)", options=all_nodes)

    nights = sorted(
        df_all.filter(pl.col("node_id") == selected_node)
        ["yo_paiva"].cast(pl.Utf8).unique().to_list()
    )
    selected_date = st.sidebar.selectbox("📅 Yö", options=nights, index=0)

    df_night = df_all.filter(pl.col("yo_paiva").cast(pl.Utf8) == selected_date)

    # --- Single-device detail ---
    st.markdown(f'<div class="pt-section">🔍 Laite {selected_node} – yksityiskohtainen analyysi</div>',
                unsafe_allow_html=True)

    row = df_night.filter(pl.col("node_id") == selected_node)
    if row.is_empty():
        st.info("Laitteella ei ole dataa valitulle yölle.")
        st.stop()

    r  = row.row(0, named=True)
    cx = r["centroid_x"]
    cy = r["centroid_y"]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    _metric(m1, f"{r['rmse_2d']:.1f}", "RMSE 2D (cm)")
    _metric(m2, f"{r['cep50']:.1f}", "CEP50 (cm)")
    _metric(m3, f"{r['cep95']:.1f}", "CEP95 (cm)")
    _metric(m4, f"{r['jitter_ka_cm']:.1f}", "Jitter ka (cm/step)")
    _metric(m5, f"{r['drift_x_cmh']:+.1f}", "Drift X (cm/h)")
    _metric(m6, f"{r['outlier_pct']:.1f}", "Outlierit (%)")

    with st.spinner("Haetaan yön raakadata silveristä…"):
        df_raw = _fetch_night(selected_node, selected_date, cx, cy)

    if df_raw.is_empty():
        st.info("Ei raakadataa tälle laite/yö-kombinaatiolle.")
        st.stop()

    angles   = np.linspace(0, 2 * math.pi, 361)
    cos_a    = np.cos(angles).tolist()
    sin_a    = np.sin(angles).tolist()
    dx_arr   = df_raw["dx"].to_list()
    dy_arr   = df_raw["dy"].to_list()
    dist_arr = df_raw["dist"].to_list()
    tunti_arr = df_raw["tunti"].to_list()
    aika_arr  = df_raw["aika_hki"].cast(pl.Utf8).to_list()

    # --- Scatter + error histogram ---
    st.markdown('<div class="pt-section">🎯 Sijaintipilvi ja säteisvirhejakauma</div>', unsafe_allow_html=True)
    left, right = st.columns([3, 2])

    with left:
        st.markdown("<small><b>Sijaintipilvi suhteessa keskipisteeseen</b></small>", unsafe_allow_html=True)
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
            xaxis=dict(title="ΔX (cm)", zeroline=True, zerolinewidth=1, zerolinecolor="#cbd5e1"),
            yaxis=dict(title="ΔY (cm, ↑=pohj.)", zeroline=True, zerolinewidth=1,
                       zerolinecolor="#cbd5e1", scaleanchor="x", scaleratio=1),
            height=420, margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            legend=dict(font=dict(size=11)),
        )
        st.plotly_chart(scatter_fig, use_container_width=True)

    with right:
        st.markdown("<small><b>Säteisvirheen jakauma</b></small>", unsafe_allow_html=True)
        dist_np = np.array(dist_arr)
        hist_vals, bin_edges = np.histogram(dist_np, bins=50)
        bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()
        nz   = hist_vals[hist_vals > 0]
        y_cap = float(np.percentile(nz, 90) * 2.5) if len(nz) > 1 else float(hist_vals.max())
        err_fig = go.Figure()
        err_fig.add_trace(go.Bar(x=bin_centers, y=hist_vals.tolist(),
                                  marker_color="#6366f1", opacity=0.8))
        for radius, color, label in [
            (r["cep50"], "#22c55e", "CEP50"),
            (r["cep95"], "#ef4444", "CEP95"),
        ]:
            err_fig.add_vline(x=radius, line_color=color, line_width=2, line_dash="dash",
                              annotation_text=label, annotation_position="top right",
                              annotation_font_size=11)
        err_fig.update_layout(
            xaxis=dict(title="Säteisvirhe (cm)"),
            yaxis=dict(title="Havaintojen määrä", range=[0, y_cap]),
            height=420, margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)", showlegend=False,
        )
        st.plotly_chart(err_fig, use_container_width=True)

    # --- Floor plan ---
    st.markdown('<div class="pt-section">🗺️ Laitteen sijainti pohjapiirustuksessa</div>', unsafe_allow_html=True)
    if IMAGE_PATH.exists():
        img    = _load_image(IMAGE_PATH)
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

    # --- Drift ---
    st.markdown('<div class="pt-section">📉 Drift – systemaattinen sijaintimuutos yön yli</div>',
                unsafe_allow_html=True)
    n      = len(dx_arr)
    t_idx  = np.arange(n, dtype=float)
    dx_np  = np.array(dx_arr, dtype=float)
    dy_np  = np.array(dy_arr, dtype=float)
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

    # --- Multi-night trend ---
    df_node = df_all.filter(pl.col("node_id") == selected_node).sort("yo_paiva")
    if len(df_node) > 1:
        dates = df_node["yo_paiva"].cast(pl.Utf8).to_list()
        st.markdown('<div class="pt-section">📈 Tarkkuustrendi – useamman yön vertailu</div>',
                    unsafe_allow_html=True)
        cep_fig = go.Figure()
        for col_name, color, label in [
            ("cep50",   "#22c55e", "CEP50"),
            ("cep68",   "#f59e0b", "CEP68"),
            ("cep95",   "#ef4444", "CEP95"),
            ("rmse_2d", "#6366f1", "RMSE 2D"),
        ]:
            cep_fig.add_trace(go.Scatter(
                x=dates, y=df_node[col_name].to_list(),
                mode="lines+markers", line=dict(color=color, width=2),
                marker=dict(size=6), name=label,
            ))
        cep_fig.update_layout(
            xaxis=dict(title="Yöpäivä"), yaxis=dict(title="cm"), height=300,
            margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            legend=dict(orientation="h", y=1.12, font=dict(size=11)),
        )
        st.plotly_chart(cep_fig, use_container_width=True)

    with st.expander("📊 Kaikki mittarit taulukossa"):
        st.dataframe(df_node.select(DISPLAY_COLS).sort("yo_paiva").to_arrow(),
                     use_container_width=True, hide_index=True)

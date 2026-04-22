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
.pt-hero {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    border-radius: 16px; padding: 2rem 2.5rem; margin: 2rem 0 1.5rem 0; color: white;
}
.pt-hero h2 { font-size: 1.6rem; font-weight: 700; margin: 0 0 0.4rem 0; }
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


@st.cache_data(show_spinner="🔎 Haetaan instanssin raakadata…", ttl=300)
def _fetch_instance_raw(node_id: str, tunti_alku: str) -> pl.DataFrame:
    return _get_conn().execute(f"""
        SELECT aika, x, y
        FROM silver_positions
        WHERE node_id = '{node_id}'
          AND aika >= TIMESTAMP '{tunti_alku}'
          AND aika <  TIMESTAMP '{tunti_alku}' + INTERVAL 3 HOUR
          AND x IS NOT NULL AND y IS NOT NULL
        ORDER BY aika
    """).pl()


def _compute_metrics(df_raw: pl.DataFrame):
    xs = df_raw["x"].to_numpy(allow_copy=True).astype(float)
    ys = df_raw["y"].to_numpy(allow_copy=True).astype(float)
    cx, cy = float(xs.mean()), float(ys.mean())
    dx = xs - cx
    dy = ys - cy
    dists = np.sqrt(dx**2 + dy**2)
    rmse_2d = float(np.sqrt((dx**2 + dy**2).mean()))
    cep50 = float(np.percentile(dists, 50))
    cep68 = float(np.percentile(dists, 68))
    cep95 = float(np.percentile(dists, 95))
    return cx, cy, dx, dy, dists, rmse_2d, cep50, cep68, cep95


def _kpi(col, val, label, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="hk-metric">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def _metric(col, val, label):
    col.markdown(
        f'<div class="pt-metric"><div class="val">{val}</div>'
        f'<div class="lbl">{label}</div></div>',
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

    # --- Sidebar: summary filters ---
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
            marker=dict(size=12, color=colors[i % len(colors)], symbol="x", line=dict(width=2)),
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
    daily = df_f.group_by("paiva").agg(pl.len().alias("n")).sort("paiva")
    fig_time = go.Figure(go.Bar(
        x=daily["paiva"].cast(pl.Utf8).to_list(), y=daily["n"].to_list(),
        marker_color="#f97316",
        hovertemplate="<b>%{x}</b><br>Tapauksia: %{y}<extra></extra>",
    ))
    fig_time.update_layout(
        height=260, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Päivämäärä"), yaxis=dict(title="Tapauksia"), showlegend=False,
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # --- Per-device bar ---
    st.markdown('<div class="hk-section">📦 Tapaukset laitteittain</div>', unsafe_allow_html=True)
    per_dev = df_f.group_by("node_id").agg(pl.len().alias("n")).sort("n", descending=True)
    fig_dev = go.Figure(go.Bar(
        x=per_dev["node_id"].cast(pl.Utf8).to_list(), y=per_dev["n"].to_list(),
        marker_color="#fb923c", text=per_dev["n"].to_list(), textposition="outside",
        hovertemplate="<b>%{x}</b><br>Tapauksia: %{y}<extra></extra>",
    ))
    fig_dev.update_layout(
        height=300, margin=dict(l=50, r=20, t=10, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Laite (node_id)", type="category"),
        yaxis=dict(title="Tapauksia"), showlegend=False,
    )
    st.plotly_chart(fig_dev, use_container_width=True)

    # --- Hour of day ---
    st.markdown('<div class="hk-section">🕐 Mihin kellonaikaan kärryt hylätään?</div>', unsafe_allow_html=True)
    by_hour = (
        df_f.with_columns(pl.col("tunti_alku").dt.hour().alias("tunti"))
        .group_by("tunti").agg(pl.len().alias("n")).sort("tunti")
    )
    fig_h = go.Figure(go.Bar(
        x=[f"{h}:00" for h in by_hour["tunti"].to_list()], y=by_hour["n"].to_list(),
        marker_color="#fbbf24",
        hovertemplate="<b>%{x}</b><br>Tapauksia: %{y}<extra></extra>",
    ))
    fig_h.update_layout(
        height=260, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Kellonaika"), yaxis=dict(title="Tapauksia"), showlegend=False,
    )
    st.plotly_chart(fig_h, use_container_width=True)

    with st.expander("📋 Kaikki tapaukset taulukossa"):
        st.dataframe(df_f.sort("paiva", "tunti_alku").to_pandas(),
                     use_container_width=True, hide_index=True)

    # =========================================================================
    # Paikannustarkkuus per instanssi
    # =========================================================================
    st.markdown("""
    <div class="pt-hero">
        <h2>🎯 Paikannustarkkuus – instanssikohtainen analyysi</h2>
        <p>Valitse laite ja instanssi — tarkkuusanalyysi päiväaikaisesta paikallaan olevasta kärrystä</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Sidebar: instance selectors ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Tarkkuusanalyysi")

    inst_nodes = sorted(df["node_id"].unique().to_list())
    acc_node   = st.sidebar.selectbox("📡 Laite", inst_nodes, key="acc_node")

    node_instances = (
        df.filter(pl.col("node_id") == acc_node)
        .sort("paiva", "tunti_alku")
    )
    inst_labels = [
        f"{row['paiva']}  {str(row['tunti_alku'])[11:16]}  "
        f"({int(row['x'])}, {int(row['y'])})"
        for row in node_instances.iter_rows(named=True)
    ]
    if not inst_labels:
        st.info(f"Laitteelle {acc_node} ei löydy instansseja.")
        st.stop()

    sel_inst_label = st.sidebar.selectbox("📋 Instanssi", inst_labels, key="acc_inst")
    inst_idx = inst_labels.index(sel_inst_label)
    inst_row = node_instances.row(inst_idx, named=True)
    tunti_alku_str = str(inst_row["tunti_alku"])

    st.markdown(
        f'<div class="pt-section">🔍 Laite {acc_node} — {inst_row["paiva"]} {tunti_alku_str[11:16]}</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Haetaan raakadata silver_positions…"):
        df_raw = _fetch_instance_raw(str(acc_node), tunti_alku_str)

    if df_raw.is_empty():
        st.info("Ei raakadataa tälle instanssille silver_positions-taulusta.")
        st.stop()

    cx, cy, dx_arr, dy_arr, dists, rmse_2d, cep50, cep68, cep95 = _compute_metrics(df_raw)
    n_pings = len(df_raw)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    _metric(m1, f"{rmse_2d:.1f}", "RMSE 2D (cm)")
    _metric(m2, f"{cep50:.1f}", "CEP50 (cm)")
    _metric(m3, f"{cep68:.1f}", "CEP68 (cm)")
    _metric(m4, f"{cep95:.1f}", "CEP95 (cm)")
    _metric(m5, str(n_pings), "Pingauksia")
    _metric(m6, f"{float(inst_row['spread_cm']):.0f}", "Spread (cm)")

    angles = np.linspace(0, 2 * math.pi, 361)
    cos_a  = np.cos(angles).tolist()
    sin_a  = np.sin(angles).tolist()

    # --- Scatter + error histogram ---
    st.markdown('<div class="pt-section">🎯 Sijaintipilvi ja säteisvirhejakauma</div>', unsafe_allow_html=True)
    left, right = st.columns([3, 2])

    with left:
        st.markdown("<small><b>Sijaintipilvi suhteessa keskipisteeseen</b></small>",
                    unsafe_allow_html=True)
        aika_arr = df_raw["aika"].cast(pl.Utf8).to_list()
        scatter_fig = go.Figure()
        scatter_fig.add_trace(go.Scattergl(
            x=dx_arr.tolist(), y=(-dy_arr).tolist(), mode="markers",
            marker=dict(size=3, color="#818cf8", opacity=0.45, line=dict(width=0)),
            name="Havainnot",
            hovertemplate="ΔX=%{x:.0f} cm, ΔY=%{y:.0f} cm<extra></extra>",
        ))
        for radius, color, label in [
            (cep50, "#22c55e", f"CEP50 {cep50:.0f} cm"),
            (cep68, "#f59e0b", f"CEP68 {cep68:.0f} cm"),
            (cep95, "#ef4444", f"CEP95 {cep95:.0f} cm"),
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
        hist_vals, bin_edges = np.histogram(dists, bins=50)
        bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()
        nz    = hist_vals[hist_vals > 0]
        y_cap = float(np.percentile(nz, 90) * 2.5) if len(nz) > 1 else float(hist_vals.max())
        err_fig = go.Figure()
        err_fig.add_trace(go.Bar(x=bin_centers, y=hist_vals.tolist(),
                                  marker_color="#6366f1", opacity=0.8))
        for radius, color, label in [(cep50, "#22c55e", "CEP50"), (cep95, "#ef4444", "CEP95")]:
            err_fig.add_vline(x=radius, line_color=color, line_width=2, line_dash="dash",
                              annotation_text=label, annotation_position="top right",
                              annotation_font_size=11)
        err_fig.update_layout(
            xaxis=dict(title="Säteisvirhe (cm)"),
            yaxis=dict(title="Havaintojen määrä", range=[0, y_cap]),
            height=420, margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            showlegend=False,
        )
        st.plotly_chart(err_fig, use_container_width=True)

    # --- Floor plan ---
    st.markdown('<div class="pt-section">🗺️ Sijainti pohjapiirustuksessa</div>', unsafe_allow_html=True)
    if IMAGE_PATH.exists():
        fp2 = go.Figure()
        fp2.add_layout_image(dict(
            source=_load_image(IMAGE_PATH),
            xref="x", yref="y", x=0, y=0,
            sizex=MAP_MAX_X, sizey=MAP_MAX_Y,
            sizing="stretch", opacity=1.0, layer="below",
            xanchor="left", yanchor="top",
        ))
        for radius, color, label in [
            (cep50, "#22c55e", "CEP50"),
            (cep68, "#f59e0b", "CEP68"),
            (cep95, "#ef4444", "CEP95"),
        ]:
            fp2.add_trace(go.Scatter(
                x=[cx + radius * c for c in cos_a],
                y=[cy + radius * s for s in sin_a],
                mode="lines", line=dict(color=color, width=2), name=label,
            ))
        fp2.add_trace(go.Scattergl(
            x=df_raw["x"].to_list(), y=df_raw["y"].to_list(), mode="markers",
            marker=dict(size=3, color="#818cf8", opacity=0.45, line=dict(width=0)),
            name="Havainnot",
        ))
        fp2.add_trace(go.Scatter(
            x=[cx], y=[cy], mode="markers",
            marker=dict(size=12, color="#6366f1", symbol="cross"),
            name=f"Keskipiste ({cx:.0f}, {cy:.0f})",
        ))
        zoom_pad = max(cep95 * 10, 1500)
        if zoom_pad < MAP_MAX_X * 0.4:
            x_range = [max(cx - zoom_pad, 0), min(cx + zoom_pad, MAP_MAX_X)]
            y_range = [max(cy - zoom_pad, 0), min(cy + zoom_pad, MAP_MAX_Y)]
        else:
            x_range, y_range = [0, MAP_MAX_X], [0, MAP_MAX_Y]

        fp2.update_xaxes(range=x_range, showgrid=False, showticklabels=False)
        fp2.update_yaxes(range=[y_range[1], y_range[0]], showgrid=False, showticklabels=False,
                         scaleanchor="x", scaleratio=1)
        fp2.update_layout(
            height=420, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="top", y=-0.02, font=dict(size=11)),
        )
        st.plotly_chart(fp2, use_container_width=True)
    else:
        st.info("Pohjapiirros ei löydy (image/kauppa2.png).")

    # --- Position over time ---
    st.markdown('<div class="pt-section">📉 Sijainti ajan yli – pysyykö paikallaan?</div>',
                unsafe_allow_html=True)
    pos_fig = go.Figure()
    pos_fig.add_trace(go.Scattergl(
        x=aika_arr, y=df_raw["x"].to_list(), mode="markers",
        marker=dict(size=2, color="#6366f1", opacity=0.4), name="X",
    ))
    pos_fig.add_trace(go.Scattergl(
        x=aika_arr, y=df_raw["y"].to_list(), mode="markers",
        marker=dict(size=2, color="#ec4899", opacity=0.4), name="Y",
    ))
    pos_fig.add_hline(y=cx, line_color="#6366f1", line_width=1, line_dash="dash",
                      annotation_text=f"X̄={cx:.0f}", annotation_font_size=10)
    pos_fig.add_hline(y=cy, line_color="#ec4899", line_width=1, line_dash="dash",
                      annotation_text=f"Ȳ={cy:.0f}", annotation_font_size=10)
    pos_fig.update_layout(
        xaxis=dict(title="Aika"), yaxis=dict(title="Koordinaatti (cm)"),
        height=280, margin=dict(l=60, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        legend=dict(orientation="h", y=1.1, font=dict(size=11)),
    )
    st.plotly_chart(pos_fig, use_container_width=True)

    # --- All instances for this device ---
    if len(node_instances) > 1:
        st.markdown('<div class="pt-section">📈 Kaikki instanssit – tarkkuus vertailu</div>',
                    unsafe_allow_html=True)
        st.dataframe(
            node_instances.select(["paiva", "tunti_alku", "x", "y", "spread_cm"])
            .sort("paiva", "tunti_alku").to_pandas(),
            use_container_width=True, hide_index=True,
        )

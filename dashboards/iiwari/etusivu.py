"""
Etusivu – UWB-järjestelmän tarkkuusanalyysi (kaikki laitteet)
==============================================================
Yöaikaisiin paikallaan oleviin laitteisiin perustuva
CEP50/CEP95, jitter ja drift -seuranta.

Kutsutaan iiwari.py:stä: dashboards.iiwari.etusivu.render()
"""

from pathlib import Path

import duckdb
import plotly.graph_objects as go
import polars as pl
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"

_CSS = """
<style>
.iiwari-hero {
    background: linear-gradient(135deg, #0a1628, #1a2f4e, #0f3460);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.iiwari-hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.iiwari-hero p  { font-size: 1rem; color: #7dd3fc; margin: 0; }
.iiwari-metric {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid #334155; border-radius: 14px;
    padding: 1.2rem 1.4rem; text-align: center; color: white;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.iiwari-metric:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(14, 165, 233, 0.15);
}
.iiwari-metric .val { font-size: 2.2rem; font-weight: 700; color: #38bdf8; }
.iiwari-metric .lbl { font-size: 0.78rem; color: #94a3b8; margin-top: 0.3rem; font-weight: 500; }
.iiwari-metric .sub { font-size: 0.7rem; color: #64748b; margin-top: 0.15rem; }
.iiwari-section {
    font-size: 1.1rem; font-weight: 600; color: var(--text-color, #e2e8f0);
    margin: 1.5rem 0 0.6rem 0; border-left: 4px solid #0ea5e9; padding-left: 0.6rem;
}
</style>
"""


@st.cache_resource(show_spinner=False)
def _get_conn():
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb ei löydy. Aja ensin `dbt run`.")
    st.stop()


@st.cache_data(show_spinner=False, ttl=300)
def _date_range() -> tuple:
    conn = _get_conn()
    row = conn.execute("SELECT MIN(yo_paiva), MAX(yo_paiva) FROM f_paikannustarkkuus").fetchone()
    return row[0], row[1]


@st.cache_data(show_spinner="🎯 Haetaan tarkkuusdata…", ttl=300)
def _load(d0: str, d1: str) -> pl.DataFrame:
    conn = _get_conn()
    return conn.execute(f"""
        SELECT yo_paiva, node_id, n_pings,
               centroid_x, centroid_y,
               std_x, std_y, rmse_2d,
               cep50, cep68, cep95,
               jitter_ka_cm, jitter_p95_cm,
               drift_x_cmh, drift_y_cmh,
               outlier_pct, avg_q, low_quality_pct
        FROM f_paikannustarkkuus
        WHERE yo_paiva >= '{d0}' AND yo_paiva <= '{d1}'
        ORDER BY yo_paiva, node_id
    """).pl()


def _kpi(col, val, label, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="iiwari-metric">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="iiwari-hero">
        <h1>🏠 Etusivu</h1>
        <p>UWB-järjestelmän tarkkuusanalyysi — CEP50/CEP95, jitter ja drift yöaikaisista paikallaan olevista laitteista (kaikki laitteet)</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Filters ---
    st.markdown("### ⚙️ Suodattimet")
    dt_min, dt_max = _date_range()

    date_range = st.date_input(
        "Päivämääräväli", value=(dt_min, dt_max),
        min_value=dt_min, max_value=dt_max,
    )

    if len(date_range) != 2:
        st.info("Valitse alku- ja loppupäivä.")
        st.stop()

    d0, d1 = str(date_range[0]), str(date_range[1])
    df = _load(d0, d1)

    if df.is_empty():
        st.warning("Ei dataa valituilla suodattimilla.")
        st.stop()

    # --- KPIs ---
    st.markdown('<div class="iiwari-section">📊 Yhteenveto</div>', unsafe_allow_html=True)

    med_cep50 = df["cep50"].median()
    med_cep95 = df["cep95"].median()
    med_jitter = df["jitter_ka_cm"].median()
    med_rmse = df["rmse_2d"].median()
    n_nights = df["yo_paiva"].n_unique()
    n_devices = df["node_id"].n_unique()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _kpi(c1, f"{med_cep50:.1f} cm", "Mediaani CEP50", "50 % pisteistä")
    _kpi(c2, f"{med_cep95:.1f} cm", "Mediaani CEP95", "95 % pisteistä")
    _kpi(c3, f"{med_jitter:.1f} cm", "Mediaani jitter")
    _kpi(c4, f"{med_rmse:.1f} cm", "Mediaani RMSE 2D")
    _kpi(c5, str(n_devices), "Laitteita")
    _kpi(c6, str(n_nights), "Yötä analysoitu")

    # --- CEP over time ---
    st.markdown('<div class="iiwari-section">📅 CEP50 & CEP95 ajan yli</div>', unsafe_allow_html=True)

    daily = (
        df.group_by("yo_paiva")
        .agg([
            pl.col("cep50").median().alias("cep50_med"),
            pl.col("cep95").median().alias("cep95_med"),
        ])
        .sort("yo_paiva")
    )

    fig_cep = go.Figure()
    fig_cep.add_trace(go.Scatter(
        x=daily["yo_paiva"].to_list(), y=daily["cep50_med"].to_list(),
        name="CEP50 (mediaani)", mode="lines+markers",
        line=dict(color="#38bdf8", width=2.5),
        marker=dict(size=5),
        hovertemplate="<b>%{x}</b><br>CEP50: %{y:.1f} cm<extra></extra>",
    ))
    fig_cep.add_trace(go.Scatter(
        x=daily["yo_paiva"].to_list(), y=daily["cep95_med"].to_list(),
        name="CEP95 (mediaani)", mode="lines+markers",
        line=dict(color="#f97316", width=2.5, dash="dash"),
        marker=dict(size=5),
        hovertemplate="<b>%{x}</b><br>CEP95: %{y:.1f} cm<extra></extra>",
    ))
    fig_cep.update_layout(
        height=320, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Yöpäivä"), yaxis=dict(title="CEP (cm)"),
        legend=dict(orientation="h", y=1.12, font=dict(size=11)),
    )
    st.plotly_chart(fig_cep, use_container_width=True)

    # --- Per-device bar chart ---
    st.markdown('<div class="iiwari-section">📦 Mediaani CEP50 laitteittain</div>', unsafe_allow_html=True)

    per_dev = (
        df.group_by("node_id")
        .agg(pl.col("cep50").median().alias("cep50_med"))
        .sort("cep50_med")
    )
    fig_bar = go.Figure(go.Bar(
        x=per_dev["node_id"].cast(pl.Utf8).to_list(),
        y=per_dev["cep50_med"].to_list(),
        marker_color="#38bdf8",
        text=[f"{v:.1f}" for v in per_dev["cep50_med"].to_list()],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>CEP50 med: %{y:.1f} cm<extra></extra>",
    ))
    fig_bar.update_layout(
        height=360, margin=dict(l=50, r=20, t=10, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Laite (node_id)", type="category"),
        yaxis=dict(title="Mediaani CEP50 (cm)"),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Jitter & drift ---
    col_j, col_d = st.columns(2)

    with col_j:
        st.markdown('<div class="iiwari-section">⚡ Jitter laitteittain</div>', unsafe_allow_html=True)
        jit = (
            df.group_by("node_id")
            .agg(pl.col("jitter_ka_cm").median().alias("jitter_med"))
            .sort("jitter_med")
        )
        fig_j = go.Figure(go.Bar(
            x=jit["node_id"].cast(pl.Utf8).to_list(),
            y=jit["jitter_med"].to_list(),
            marker_color="#38bdf8",
            text=[f"{v:.1f}" for v in jit["jitter_med"].to_list()],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Jitter: %{y:.1f} cm<extra></extra>",
        ))
        fig_j.update_layout(
            height=300, margin=dict(l=50, r=20, t=10, b=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Laite (node_id)", type="category"),
            yaxis=dict(title="Mediaani jitter (cm)"),
            showlegend=False,
        )
        st.plotly_chart(fig_j, use_container_width=True)

    with col_d:
        st.markdown('<div class="iiwari-section">🧭 Drift laitteittain</div>', unsafe_allow_html=True)
        drift = (
            df.group_by("node_id")
            .agg([
                pl.col("drift_x_cmh").mean().alias("dx"),
                pl.col("drift_y_cmh").mean().alias("dy"),
            ])
        )
        drift = drift.with_columns(
            (pl.col("dx").pow(2) + pl.col("dy").pow(2)).sqrt().alias("drift_tot")
        ).sort("drift_tot")
        fig_dr = go.Figure(go.Bar(
            x=drift["node_id"].cast(pl.Utf8).to_list(),
            y=drift["drift_tot"].to_list(),
            marker_color="#f59e0b",
            text=[f"{v:.2f}" for v in drift["drift_tot"].to_list()],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Drift: %{y:.2f} cm/h<extra></extra>",
        ))
        fig_dr.update_layout(
            height=300, margin=dict(l=50, r=20, t=10, b=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Laite (node_id)", type="category"),
            yaxis=dict(title="Drift kokonaismagnitude (cm/h)"),
            showlegend=False,
        )
        st.plotly_chart(fig_dr, use_container_width=True)

    # --- Raw data table ---
    with st.expander("📋 Raakadata"):
        st.dataframe(df.to_pandas(), use_container_width=True)

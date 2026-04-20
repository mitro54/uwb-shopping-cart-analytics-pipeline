"""
Liiketoiminnan tunnusluvut – Asiakaskäyttäytymisen dashboard
============================================================
Kauppiaan näkymä: käyntimäärät, viipymät, osastojen suosio ja
asiakasvirrat aikarajauksella suodatettuna.
"""

from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st

st.set_page_config(page_title="Liiketoiminta", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "data" / "warehouse" / "dev.duckdb"

WEEKDAY_LABELS = ["Ma", "Ti", "Ke", "To", "Pe", "La", "Su"]

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.hero {
    background: linear-gradient(135deg, #0c1a3a, #1e3a5f, #2d4a7c);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.hero p  { font-size: 1rem; color: #93c5fd; margin: 0; }
.metric-card {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid #334155; border-radius: 14px;
    padding: 1.2rem 1.4rem; text-align: center; color: white;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(59, 130, 246, 0.15);
}
.metric-card .val { font-size: 2.2rem; font-weight: 700; color: #60a5fa; }
.metric-card .lbl { font-size: 0.78rem; color: #94a3b8; margin-top: 0.3rem; font-weight: 500; }
.metric-card .sub { font-size: 0.7rem; color: #64748b; margin-top: 0.15rem; }
.section-title {
    font-size: 1.1rem; font-weight: 600; color: #1e3a5f;
    margin: 1.5rem 0 0.6rem 0; border-left: 4px solid #3b82f6; padding-left: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>📈 Liiketoiminnan tunnusluvut</h1>
    <p>Asiakaskäyttäytymisen analyysi — käynnit, viipymät ja osastojen suosio</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data connection
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _get_conn():
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb-tiedostoa ei löydy. Aja ensin dbt run.")
    st.stop()


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=300)
def fetch_date_range() -> tuple:
    conn = _get_conn()
    row = conn.execute("SELECT MIN(kaynti_paiva), MAX(kaynti_paiva) FROM f_kaynti").fetchone()
    return row[0], row[1]


@st.cache_data(show_spinner="📅 Haetaan käyntidata…", ttl=300)
def fetch_kaynti(date_start: str, date_end: str) -> pl.DataFrame:
    conn = _get_conn()
    arrow = conn.execute(f"""
        SELECT
            kaynti_id,
            node_id,
            kaynti_paiva,
            kaynti_tunti,
            kaynti_viikonpaiva,
            kesto_sekunteina,
            matka,
            keskinopeus
        FROM f_kaynti
        WHERE kaynti_paiva >= '{date_start}'
          AND kaynti_paiva <= '{date_end}'
    """).fetch_arrow_table()
    return pl.from_arrow(arrow)


@st.cache_data(show_spinner="🏬 Haetaan osastodata…", ttl=300)
def fetch_osastokaynti(date_start: str, date_end: str) -> pl.DataFrame:
    conn = _get_conn()
    arrow = conn.execute(f"""
        SELECT
            ok.kaynti_id,
            ok.osasto_id,
            ok.osaston_nimi,
            ok.vietetty_aika_sekunteina,
            ok.matka_osastolla_m,
            ok.havainnot_osastolla
        FROM f_osastokaynti ok
        INNER JOIN f_kaynti k ON ok.kaynti_id = k.kaynti_id
        WHERE k.kaynti_paiva >= '{date_start}'
          AND k.kaynti_paiva <= '{date_end}'
    """).fetch_arrow_table()
    return pl.from_arrow(arrow)


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

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
df_kaynti = fetch_kaynti(date_start, date_end)
df_osasto = fetch_osastokaynti(date_start, date_end)

if df_kaynti.is_empty():
    st.warning("Ei käyntejä valitulla aikavälillä.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI calculations
# ---------------------------------------------------------------------------
total_visits = len(df_kaynti)
avg_duration_min = df_kaynti["kesto_sekunteina"].mean() / 60.0
median_duration_min = df_kaynti["kesto_sekunteina"].median() / 60.0
avg_distance = df_kaynti["matka"].mean()
avg_speed = df_kaynti["keskinopeus"].mean()

# Vilkkain tunti
hour_counts = df_kaynti.group_by("kaynti_tunti").agg(pl.len().alias("n")).sort("n", descending=True)
busiest_hour = int(hour_counts["kaynti_tunti"][0])

# Vilkkain viikonpäivä
wd_counts = df_kaynti.group_by("kaynti_viikonpaiva").agg(pl.len().alias("n")).sort("n", descending=True)
busiest_wd = WEEKDAY_LABELS[int(wd_counts["kaynti_viikonpaiva"][0]) - 1]

# Osastojen lukumäärä per käynti
if not df_osasto.is_empty():
    depts_per_visit = df_osasto.group_by("kaynti_id").agg(
        pl.col("osasto_id").n_unique().alias("n_depts")
    )["n_depts"].mean()
else:
    depts_per_visit = 0

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📊 Yhteenveto</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
kpis_row1 = [
    (c1, f"{total_visits:,}", "Käyntejä yhteensä", ""),
    (c2, f"{avg_duration_min:.1f}", "Keskim. kesto (min)", f"Mediaani {median_duration_min:.1f} min"),
    (c3, f"{avg_distance:.0f}", "Keskim. kävelymatka (m)", f"Nopeus {avg_speed:.2f} m/s"),
    (c4, f"{depts_per_visit:.1f}", "Osastoja per käynti", ""),
]
for col, val, label, sub in kpis_row1:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

c5, c6, c7, c8 = st.columns(4)
kpis_row2 = [
    (c5, f"{busiest_hour}:00", "Vilkkain tunti", ""),
    (c6, busiest_wd, "Vilkkain viikonpäivä", ""),
    (c7, f"{df_kaynti['matka'].max():.0f}", "Pisin reitti (m)", ""),
    (c8, f"{df_kaynti['kesto_sekunteina'].max() / 60:.0f}", "Pisin käynti (min)", ""),
]
for col, val, label, sub in kpis_row2:
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# 1. Käynnit päivittäin – trendiviiva
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📅 Käynnit päivittäin</div>', unsafe_allow_html=True)

daily = (
    df_kaynti.group_by("kaynti_paiva")
    .agg(pl.len().alias("kaynteja"))
    .sort("kaynti_paiva")
)

trend_fig = go.Figure()
trend_fig.add_trace(go.Scatter(
    x=daily["kaynti_paiva"].to_list(),
    y=daily["kaynteja"].to_list(),
    mode="lines+markers",
    line=dict(color="#3b82f6", width=2.5),
    marker=dict(size=5, color="#3b82f6"),
    fill="tozeroy",
    fillcolor="rgba(59, 130, 246, 0.08)",
    hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
))

# 7 päivän liukuva keskiarvo
if len(daily) >= 7:
    ma7 = daily.with_columns(
        pl.col("kaynteja").rolling_mean(window_size=7).alias("ma7")
    )
    trend_fig.add_trace(go.Scatter(
        x=ma7["kaynti_paiva"].to_list(),
        y=ma7["ma7"].to_list(),
        mode="lines",
        line=dict(color="#f59e0b", width=2, dash="dash"),
        name="7 pv liukuva ka",
        hovertemplate="7 pv ka: %{y:.1f}<extra></extra>",
    ))

trend_fig.update_layout(
    height=320, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    xaxis=dict(title="Päivämäärä"),
    yaxis=dict(title="Käyntejä"),
    showlegend=True,
    legend=dict(orientation="h", y=1.12, font=dict(size=11)),
)
st.plotly_chart(trend_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 2. Käynnit tunneittain & viikonpäivittäin (rinnakkain)
# ---------------------------------------------------------------------------
col_hour, col_wd = st.columns(2)

with col_hour:
    st.markdown('<div class="section-title">🕐 Käynnit tunneittain</div>', unsafe_allow_html=True)

    hourly = (
        df_kaynti.group_by("kaynti_tunti")
        .agg(pl.len().alias("kaynteja"))
        .sort("kaynti_tunti")
    )
    hours = hourly["kaynti_tunti"].to_list()
    counts = hourly["kaynteja"].to_list()

    max_c = max(counts) if counts else 1
    colors = [
        f"rgba(59, 130, 246, {0.3 + 0.7 * (c / max_c)})" for c in counts
    ]

    hour_fig = go.Figure(go.Bar(
        x=[f"{h}:00" for h in hours],
        y=counts,
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
    ))
    hour_fig.update_layout(
        height=300, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Tunti"), yaxis=dict(title="Käyntejä"),
        showlegend=False,
    )
    st.plotly_chart(hour_fig, use_container_width=True)

with col_wd:
    st.markdown('<div class="section-title">📆 Käynnit viikonpäivittäin</div>', unsafe_allow_html=True)

    weekly = (
        df_kaynti.group_by("kaynti_viikonpaiva")
        .agg(pl.len().alias("kaynteja"))
        .sort("kaynti_viikonpaiva")
    )
    wds = weekly["kaynti_viikonpaiva"].to_list()
    wd_counts_list = weekly["kaynteja"].to_list()
    wd_labels = [WEEKDAY_LABELS[int(w) - 1] for w in wds]

    max_wd = max(wd_counts_list) if wd_counts_list else 1
    wd_colors = [
        f"rgba(16, 185, 129, {0.3 + 0.7 * (c / max_wd)})" for c in wd_counts_list
    ]

    wd_fig = go.Figure(go.Bar(
        x=wd_labels,
        y=wd_counts_list,
        marker_color=wd_colors,
        text=[str(c) for c in wd_counts_list],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
    ))
    wd_fig.update_layout(
        height=300, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Viikonpäivä"), yaxis=dict(title="Käyntejä"),
        showlegend=False,
    )
    st.plotly_chart(wd_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. Osastoanalytiikka
# ---------------------------------------------------------------------------
if not df_osasto.is_empty():
    st.markdown('<div class="section-title">🏬 Osastojen suosio ja viipymäajat</div>',
                unsafe_allow_html=True)

    dept_stats = (
        df_osasto.group_by("osaston_nimi")
        .agg([
            pl.col("kaynti_id").n_unique().alias("uniikkeja_kaynteja"),
            pl.col("vietetty_aika_sekunteina").mean().alias("keskim_viipyma_s"),
            pl.col("matka_osastolla_m").mean().alias("keskim_matka_m"),
        ])
        .sort("uniikkeja_kaynteja", descending=True)
    )

    # Poistetaan kassat vertailusta (ne eivät ole varsinainen osasto)
    dept_stats_no_kassa = dept_stats.filter(pl.col("osaston_nimi") != "kassat")

    col_pop, col_dwell = st.columns(2)

    with col_pop:
        st.markdown("**Käyntimäärä osastoittain**")
        names = dept_stats_no_kassa["osaston_nimi"].to_list()
        visits = dept_stats_no_kassa["uniikkeja_kaynteja"].to_list()

        pop_fig = go.Figure(go.Bar(
            y=names[::-1],
            x=visits[::-1],
            orientation="h",
            marker=dict(
                color=visits[::-1],
                colorscale="Blues",
                line=dict(width=0),
            ),
            text=[f"{v:,}" for v in visits[::-1]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Käyntejä: %{x:,}<extra></extra>",
        ))
        pop_fig.update_layout(
            height=420, margin=dict(l=160, r=60, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Uniikkeja käyntejä"),
            yaxis=dict(tickfont=dict(size=11)),
            showlegend=False,
        )
        st.plotly_chart(pop_fig, use_container_width=True)

    with col_dwell:
        st.markdown("**Keskim. viipymäaika osastoittain**")
        dwell_sorted = dept_stats_no_kassa.sort("keskim_viipyma_s", descending=True)
        dnames = dwell_sorted["osaston_nimi"].to_list()
        dwell = [s / 60.0 for s in dwell_sorted["keskim_viipyma_s"].to_list()]

        dwell_fig = go.Figure(go.Bar(
            y=dnames[::-1],
            x=dwell[::-1],
            orientation="h",
            marker=dict(
                color=dwell[::-1],
                colorscale="Oranges",
                line=dict(width=0),
            ),
            text=[f"{d:.1f} min" for d in dwell[::-1]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Viipymä: %{x:.1f} min<extra></extra>",
        ))
        dwell_fig.update_layout(
            height=420, margin=dict(l=160, r=70, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Keskim. viipymä (min)"),
            yaxis=dict(tickfont=dict(size=11)),
            showlegend=False,
        )
        st.plotly_chart(dwell_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Käyntiajan jakauma
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">⏱️ Käyntiajan jakauma</div>', unsafe_allow_html=True)
st.caption("Kuinka pitkiä asiakkaiden kauppareissut ovat? Asteikolla minuutteina.")

durations_min = (df_kaynti["kesto_sekunteina"] / 60.0).to_numpy()

hist_vals, bin_edges = np.histogram(durations_min, bins=40, range=(0, max(120, durations_min.max())))
bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()

dur_fig = go.Figure()
dur_fig.add_trace(go.Bar(
    x=bin_centers,
    y=hist_vals.tolist(),
    marker_color=[
        "#22c55e" if x < 30 else "#3b82f6" if x < 60 else "#f59e0b" if x < 90 else "#ef4444"
        for x in bin_centers
    ],
    opacity=0.85,
    hovertemplate="<b>%{x:.0f} min</b><br>Käyntejä: %{y}<extra></extra>",
))

# Mediaani ja ka viivat
dur_fig.add_vline(
    x=float(np.median(durations_min)),
    line_color="#6366f1", line_width=2, line_dash="dash",
    annotation_text=f"Mediaani {np.median(durations_min):.0f} min",
    annotation_position="top right", annotation_font_size=11,
)
dur_fig.add_vline(
    x=float(np.mean(durations_min)),
    line_color="#f97316", line_width=2, line_dash="dot",
    annotation_text=f"Keskiarvo {np.mean(durations_min):.0f} min",
    annotation_position="top left", annotation_font_size=11,
)

dur_fig.update_layout(
    height=300, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    xaxis=dict(title="Käynnin kesto (min)"),
    yaxis=dict(title="Käyntien lukumäärä"),
    showlegend=False,
)
st.plotly_chart(dur_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 5. Kävelymatkan jakauma
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">🚶 Kävelymatkan jakauma</div>', unsafe_allow_html=True)
st.caption("Kuinka pitkän matkan asiakkaat kävelevät kaupassa?")

distances = df_kaynti["matka"].to_numpy()
hist_d, bin_d = np.histogram(distances, bins=40, range=(0, min(3000, distances.max())))
bin_d_centers = ((bin_d[:-1] + bin_d[1:]) / 2).tolist()

dist_fig = go.Figure()
dist_fig.add_trace(go.Bar(
    x=bin_d_centers,
    y=hist_d.tolist(),
    marker_color=[
        "#22c55e" if x < 500 else "#3b82f6" if x < 1000 else "#f59e0b" if x < 2000 else "#ef4444"
        for x in bin_d_centers
    ],
    opacity=0.85,
    hovertemplate="<b>%{x:.0f} m</b><br>Käyntejä: %{y}<extra></extra>",
))

dist_fig.add_vline(
    x=float(np.median(distances)),
    line_color="#6366f1", line_width=2, line_dash="dash",
    annotation_text=f"Mediaani {np.median(distances):.0f} m",
    annotation_position="top right", annotation_font_size=11,
)

dist_fig.update_layout(
    height=300, margin=dict(l=50, r=20, t=10, b=50),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
    xaxis=dict(title="Kävelymatka (m)"),
    yaxis=dict(title="Käyntien lukumäärä"),
    showlegend=False,
)
st.plotly_chart(dist_fig, use_container_width=True)

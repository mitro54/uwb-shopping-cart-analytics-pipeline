"""
Liiketoiminnan tunnusluvut – Asiakaskäyttäytymisen dashboard
============================================================
Kauppiaan näkymä: käyntimäärät, viipymät, osastojen suosio ja
asiakasvirrat aikarajauksella suodatettuna.

Kutsutaan app.py:stä: dashboards.liiketoiminta.render()
"""

from pathlib import Path

import duckdb
import numpy as np
import plotly.graph_objects as go
import polars as pl
import streamlit as st

from agents.shared.config import CONFIG
DUCKDB_PATH = CONFIG.duckdb_path
WEEKDAY_LABELS = ["Ma", "Ti", "Ke", "To", "Pe", "La", "Su"]

# ---------------------------------------------------------------------------
# Styles (injected once per render)
# ---------------------------------------------------------------------------
_CSS = """
<style>
.biz-hero {
    background: linear-gradient(135deg, #0c1a3a, #1e3a5f, #2d4a7c);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.biz-hero h1 { font-size: 2rem; font-weight: 700; margin: 0 0 0.4rem 0; }
.biz-hero p  { font-size: 1rem; color: #93c5fd; margin: 0; }
.biz-metric {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    border: 1px solid #334155; border-radius: 14px;
    padding: 1.2rem 1.4rem; text-align: center; color: white;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.biz-metric:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(59, 130, 246, 0.15);
}
.biz-metric .val { font-size: 2.2rem; font-weight: 700; color: #60a5fa; }
.biz-metric .lbl { font-size: 0.78rem; color: #94a3b8; margin-top: 0.3rem; font-weight: 500; }
.biz-metric .sub { font-size: 0.7rem; color: #64748b; margin-top: 0.15rem; }
.biz-section {
    font-size: 1.1rem; font-weight: 600; color: var(--text-color, #e2e8f0);
    margin: 1.5rem 0 0.6rem 0; border-left: 4px solid #3b82f6; padding-left: 0.6rem;
}
</style>
"""


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _get_conn():
    if DUCKDB_PATH.exists():
        return duckdb.connect(str(DUCKDB_PATH), read_only=True)
    st.error("dev.duckdb-tiedostoa ei löydy. Aja ensin `dbt run`.")
    st.stop()


@st.cache_data(show_spinner=False, ttl=600)
def _get_time_options():
    conn = _get_conn()
    df = conn.execute("""
        SELECT 
            DISTINCT YEAR(kaynti_paiva) as year,
            MONTH(kaynti_paiva) as month,
            WEEK(kaynti_paiva) as week
        FROM f_kaynti
    """).pl()
    years = sorted(df["year"].unique().to_list())
    months = sorted(df["month"].unique().to_list())
    weeks = sorted(df["week"].unique().to_list())
    return years, months, weeks


@st.cache_data(show_spinner="📅 Haetaan käyntidata…", ttl=300)
def _kaynti(years, months, weeks, h0: int, h1: int) -> pl.DataFrame:
    conn = _get_conn()
    where_clauses = [f"kaynti_tunti >= {h0} AND kaynti_tunti <= {h1}"]
    if years:
        where_clauses.append(f"YEAR(kaynti_paiva) IN ({','.join(map(str, years))})")
    if months:
        where_clauses.append(f"MONTH(kaynti_paiva) IN ({','.join(map(str, months))})")
    if weeks:
        where_clauses.append(f"WEEK(kaynti_paiva) IN ({','.join(map(str, weeks))})")
    
    where_str = " AND ".join(where_clauses)
    return conn.execute(f"""
        SELECT kaynti_id, node_id, kaynti_paiva, kaynti_tunti,
               kaynti_viikonpaiva, kesto_sekunteina, matka, keskinopeus
        FROM f_kaynti
        WHERE {where_str}
    """).pl()


@st.cache_data(show_spinner="🏬 Haetaan osastodata…", ttl=300)
def _osasto(years, months, weeks, h0: int, h1: int) -> pl.DataFrame:
    conn = _get_conn()
    where_clauses = [f"k.kaynti_tunti >= {h0} AND k.kaynti_tunti <= {h1}"]
    if years:
        where_clauses.append(f"YEAR(k.kaynti_paiva) IN ({','.join(map(str, years))})")
    if months:
        where_clauses.append(f"MONTH(k.kaynti_paiva) IN ({','.join(map(str, months))})")
    if weeks:
        where_clauses.append(f"WEEK(k.kaynti_paiva) IN ({','.join(map(str, weeks))})")
    
    where_str = " AND ".join(where_clauses)
    return conn.execute(f"""
        SELECT ok.kaynti_id, ok.osasto_id, ok.osaston_nimi,
               ok.vietetty_aika_sekunteina, ok.matka_osastolla_m,
               ok.havainnot_osastolla
        FROM f_osastokaynti ok
        INNER JOIN f_kaynti k ON ok.kaynti_id = k.kaynti_id
        WHERE {where_str}
    """).pl()


# ---------------------------------------------------------------------------
# Render helper
# ---------------------------------------------------------------------------
def _kpi(col, val, label, sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    col.markdown(
        f'<div class="biz-metric">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render():
    """Piirtää liiketoiminta-dashboardin. Kutsutaan app.py:stä."""

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="biz-hero">
        <h1>📈 {CONFIG.store_name}: Liiketoiminnan tunnusluvut</h1>
        <p>Asiakaskäyttäytymisen analyysi — käynnit, viipymät ja osastojen suosio</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Filters ----------------------------------------------------------
    st.markdown("### ⚙️ Suodattimet")
    years_opt, months_opt, weeks_opt = _get_time_options()
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sel_years = st.multiselect("Vuodet", options=years_opt, placeholder="Kaikki vuodet")
    with col_f2:
        month_labels = {
            1: "Tammi", 2: "Helmi", 3: "Maalis", 4: "Huhti", 5: "Touko", 6: "Kesä",
            7: "Heinä", 8: "Elo", 9: "Syys", 10: "Loka", 11: "Marras", 12: "Joulu"
        }
        sel_months = st.multiselect(
            "Kuukaudet", 
            options=months_opt, 
            format_func=lambda x: month_labels.get(x, str(x)),
            placeholder="Kaikki kuukaudet"
        )
    with col_f3:
        sel_weeks = st.multiselect("Viikot", options=weeks_opt, placeholder="Kaikki viikot")

    col_f4 = st.columns(1)[0]
    with col_f4:
        hour_range = st.slider(
            "Kellonajat", min_value=0, max_value=23,
            value=(0, 23), step=1, format="%d:00"
        )
    
    h0, h1 = hour_range

    # --- Load data ---------------------------------------------------------
    df = _kaynti(sel_years, sel_months, sel_weeks, h0, h1)
    df_o = _osasto(sel_years, sel_months, sel_weeks, h0, h1)
    if df.is_empty():
        st.warning("Ei käyntejä valitulla aikavälillä.")
        st.stop()

    # --- KPI calculations --------------------------------------------------
    total = len(df)
    avg_dur = df["kesto_sekunteina"].mean() / 60.0
    med_dur = df["kesto_sekunteina"].median() / 60.0
    avg_dist = df["matka"].mean()
    avg_spd = df["keskinopeus"].mean()

    hour_top = df.group_by("kaynti_tunti").agg(pl.len().alias("n")).sort("n", descending=True)
    busiest_h = int(hour_top["kaynti_tunti"][0])

    wd_top = df.group_by("kaynti_viikonpaiva").agg(pl.len().alias("n")).sort("n", descending=True)
    busiest_wd = WEEKDAY_LABELS[int(wd_top["kaynti_viikonpaiva"][0]) - 1]

    depts_per = 0.0
    if not df_o.is_empty():
        depts_per = df_o.group_by("kaynti_id").agg(
            pl.col("osasto_id").n_unique().alias("n")
        )["n"].mean()

    # --- KPI cards ---------------------------------------------------------
    st.markdown('<div class="biz-section">📊 Yhteenveto</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, f"{total:,}", "Käyntejä yhteensä")
    _kpi(c2, f"{avg_dur:.1f}", "Keskim. kesto (min)", f"Mediaani {med_dur:.1f} min")
    _kpi(c3, f"{avg_dist:.0f}", "Keskim. kävelymatka (m)", f"Nopeus {avg_spd:.2f} m/s")
    _kpi(c4, f"{depts_per:.1f}", "Osastoja per käynti")

    c5, c6, c7, c8 = st.columns(4)
    _kpi(c5, f"{busiest_h}:00", "Vilkkain tunti")
    _kpi(c6, busiest_wd, "Vilkkain viikonpäivä")
    _kpi(c7, f"{df['matka'].max():.0f}", "Pisin reitti (m)")
    _kpi(c8, f"{df['kesto_sekunteina'].max() / 60:.0f}", "Pisin käynti (min)")

    # --- 1. Daily trend ----------------------------------------------------
    st.markdown('<div class="biz-section">📅 Käynnit päivittäin</div>', unsafe_allow_html=True)

    daily = df.group_by("kaynti_paiva").agg(pl.len().alias("n")).sort("kaynti_paiva")
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=daily["kaynti_paiva"].to_list(), y=daily["n"].to_list(),
        mode="lines+markers", line=dict(color="#3b82f6", width=2.5),
        marker=dict(size=5, color="#3b82f6"),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
        hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
    ))
    if len(daily) >= 7:
        ma7 = daily.with_columns(pl.col("n").rolling_mean(window_size=7).alias("ma7"))
        fig_trend.add_trace(go.Scatter(
            x=ma7["kaynti_paiva"].to_list(), y=ma7["ma7"].to_list(),
            mode="lines", line=dict(color="#f59e0b", width=2, dash="dash"),
            name="7 pv liukuva ka",
        ))
    fig_trend.update_layout(
        height=320, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Päivämäärä"), yaxis=dict(title="Käyntejä"),
        showlegend=True, legend=dict(orientation="h", y=1.12, font=dict(size=11)),
    )
    st.plotly_chart(fig_trend, width="stretch")

    # --- 2. Hourly & weekday -----------------------------------------------
    col_h, col_w = st.columns(2)

    with col_h:
        st.markdown('<div class="biz-section">🕐 Käynnit tunneittain</div>', unsafe_allow_html=True)
        hourly = df.group_by("kaynti_tunti").agg(pl.len().alias("n")).sort("kaynti_tunti")
        hrs, cnts = hourly["kaynti_tunti"].to_list(), hourly["n"].to_list()
        mx = max(cnts) if cnts else 1
        fig_h = go.Figure(go.Bar(
            x=[f"{h}:00" for h in hrs], y=cnts,
            marker_color=[f"rgba(59,130,246,{0.3+0.7*c/mx})" for c in cnts],
            hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
        ))
        fig_h.update_layout(
            height=300, margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Tunti"), yaxis=dict(title="Käyntejä"), showlegend=False,
        )
        st.plotly_chart(fig_h, width="stretch")

    with col_w:
        st.markdown('<div class="biz-section">📆 Käynnit viikonpäivittäin</div>', unsafe_allow_html=True)
        weekly = df.group_by("kaynti_viikonpaiva").agg(pl.len().alias("n")).sort("kaynti_viikonpaiva")
        wds = weekly["kaynti_viikonpaiva"].to_list()
        wc = weekly["n"].to_list()
        wl = [WEEKDAY_LABELS[int(w) - 1] for w in wds]
        mw = max(wc) if wc else 1
        fig_w = go.Figure(go.Bar(
            x=wl, y=wc,
            marker_color=[f"rgba(16,185,129,{0.3+0.7*c/mw})" for c in wc],
            text=[str(c) for c in wc], textposition="outside",
            hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
        ))
        fig_w.update_layout(
            height=300, margin=dict(l=50, r=20, t=10, b=50),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
            xaxis=dict(title="Viikonpäivä"), yaxis=dict(title="Käyntejä"), showlegend=False,
        )
        st.plotly_chart(fig_w, width="stretch")

    # --- 3. Department analytics -------------------------------------------
    if not df_o.is_empty():
        st.markdown('<div class="biz-section">🏬 Osastojen suosio ja viipymäajat</div>',
                    unsafe_allow_html=True)

        ds = (df_o.group_by("osaston_nimi").agg([
            pl.col("kaynti_id").n_unique().alias("visits"),
            pl.col("vietetty_aika_sekunteina").mean().alias("avg_s"),
        ]).sort("visits", descending=True)
            .filter(pl.col("osaston_nimi") != "kassat"))

        col_p, col_d = st.columns(2)
        with col_p:
            st.markdown("**Käyntimäärä osastoittain**")
            names = ds["osaston_nimi"].to_list()
            vis = ds["visits"].to_list()
            fig_p = go.Figure(go.Bar(
                y=names[::-1], x=vis[::-1], orientation="h",
                marker=dict(color=vis[::-1], colorscale="Blues"),
                text=[f"{v:,}" for v in vis[::-1]], textposition="outside",
            ))
            fig_p.update_layout(
                height=420, margin=dict(l=160, r=60, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
                xaxis=dict(title="Käyntejä"), showlegend=False,
            )
            st.plotly_chart(fig_p, width="stretch")

        with col_d:
            st.markdown("**Keskim. viipymäaika osastoittain**")
            dw = ds.sort("avg_s", descending=True)
            dn = dw["osaston_nimi"].to_list()
            dt_vals = [s / 60.0 for s in dw["avg_s"].to_list()]
            fig_d = go.Figure(go.Bar(
                y=dn[::-1], x=dt_vals[::-1], orientation="h",
                marker=dict(color=dt_vals[::-1], colorscale="Oranges"),
                text=[f"{d:.1f} min" for d in dt_vals[::-1]], textposition="outside",
            ))
            fig_d.update_layout(
                height=420, margin=dict(l=160, r=70, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
                xaxis=dict(title="Viipymä (min)"), showlegend=False,
            )
            st.plotly_chart(fig_d, width="stretch")

    # --- 4. Duration histogram ---------------------------------------------
    st.markdown('<div class="biz-section">⏱️ Käyntiajan jakauma</div>', unsafe_allow_html=True)
    st.caption("Kuinka pitkiä asiakkaiden kauppareissut ovat?")

    dur = (df["kesto_sekunteina"] / 60.0).to_numpy()
    hv, be = np.histogram(dur, bins=40, range=(0, max(120, dur.max())))
    bc = ((be[:-1] + be[1:]) / 2).tolist()

    fig_dur = go.Figure(go.Bar(
        x=bc, y=hv.tolist(), opacity=0.85,
        marker_color=["#22c55e" if x < 30 else "#3b82f6" if x < 60 else "#f59e0b" if x < 90 else "#ef4444" for x in bc],
    ))
    fig_dur.add_vline(x=float(np.median(dur)), line_color="#6366f1", line_width=2, line_dash="dash",
                      annotation_text=f"Mediaani {np.median(dur):.0f} min", annotation_position="top right")
    fig_dur.add_vline(x=float(np.mean(dur)), line_color="#f97316", line_width=2, line_dash="dot",
                      annotation_text=f"Keskiarvo {np.mean(dur):.0f} min", annotation_position="top left")
    fig_dur.update_layout(
        height=300, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Kesto (min)"), yaxis=dict(title="Käyntejä"), showlegend=False,
    )
    st.plotly_chart(fig_dur, width="stretch")

    # --- 5. Distance histogram ---------------------------------------------
    st.markdown('<div class="biz-section">🚶 Kävelymatkan jakauma</div>', unsafe_allow_html=True)
    st.caption("Kuinka pitkän matkan asiakkaat kävelevät kaupassa?")

    dist = df["matka"].to_numpy()
    hd, bd = np.histogram(dist, bins=40, range=(0, min(3000, dist.max())))
    bdc = ((bd[:-1] + bd[1:]) / 2).tolist()

    fig_dist = go.Figure(go.Bar(
        x=bdc, y=hd.tolist(), opacity=0.85,
        marker_color=["#22c55e" if x < 500 else "#3b82f6" if x < 1000 else "#f59e0b" if x < 2000 else "#ef4444" for x in bdc],
    ))
    fig_dist.add_vline(x=float(np.median(dist)), line_color="#6366f1", line_width=2, line_dash="dash",
                       annotation_text=f"Mediaani {np.median(dist):.0f} m", annotation_position="top right")
    fig_dist.update_layout(
        height=300, margin=dict(l=50, r=20, t=10, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
        xaxis=dict(title="Kävelymatka (m)"), yaxis=dict(title="Käyntejä"), showlegend=False,
    )
    st.plotly_chart(fig_dist, width="stretch")

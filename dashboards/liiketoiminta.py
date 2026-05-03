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

@st.cache_data(show_spinner=False, ttl=600)
def _get_special_events():
    """Lataa erikoistapahtumat CSV-tiedostosta (myöhemmin Gold-taulusta)."""
    try:
        df = pl.read_csv("bytebuddies_dbt/seeds/special_events.csv")
        return df
    except:
        return pl.DataFrame()

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
.biz-metric .delta { font-size: 0.8rem; font-weight: 600; margin-top: 0.4rem; padding: 0.1rem 0.4rem; border-radius: 4px; display: inline-block; }
.delta-up { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.delta-down { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.delta-neutral { background: rgba(148, 163, 184, 0.1); color: #94a3b8; }
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
    # Haetaan uniikit yhdistelmät, jotta voimme tehdä ristiinsuodatusta
    df = conn.execute("""
        SELECT 
            DISTINCT YEAR(kaynti_paiva) as year,
            MONTH(kaynti_paiva) as month,
            WEEK(kaynti_paiva) as week,
            kaynti_viikonpaiva as weekday,
            kaynti_tunti as hour
        FROM f_kaynti
    """).pl()
    return df


@st.cache_data(show_spinner="📅 Haetaan käyntidata…", ttl=300)
def _kaynti(years, months, weeks, weekdays, hours) -> pl.DataFrame:
    conn = _get_conn()
    where_clauses = []
    if years:
        where_clauses.append(f"YEAR(kaynti_paiva) IN ({','.join(map(str, years))})")
    if months:
        where_clauses.append(f"MONTH(kaynti_paiva) IN ({','.join(map(str, months))})")
    if weeks:
        where_clauses.append(f"WEEK(kaynti_paiva) IN ({','.join(map(str, weeks))})")
    if weekdays:
        where_clauses.append(f"kaynti_viikonpaiva IN ({','.join(map(str, weekdays))})")
    if hours:
        where_clauses.append(f"kaynti_tunti IN ({','.join(map(str, hours))})")
    
    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
    return conn.execute(f"""
        SELECT kaynti_id, node_id, kaynti_paiva, kaynti_tunti,
               kaynti_viikonpaiva, kesto_sekunteina, matka, keskinopeus
        FROM f_kaynti
        WHERE {where_str}
    """).pl()


@st.cache_data(show_spinner="🏬 Haetaan osastodata…", ttl=300)
def _osasto(years, months, weeks, weekdays, hours, min_dwell: int = 0) -> pl.DataFrame:
    conn = _get_conn()
    
    # Suhteellinen suodatus: lasketaan osaston koko (diagonaali) ja suhteutetaan viipymä siihen
    where_clauses = [
        f"ok.vietetty_aika_sekunteina >= {min_dwell} * "
        "(SQRT(POWER(d.loppu_x-d.alku_x, 2) + POWER(d.loppu_y-d.alku_y, 2)) / "
        "(SELECT MAX(SQRT(POWER(loppu_x-alku_x, 2) + POWER(loppu_y-alku_y, 2))) FROM dim_osastot))"
    ]
    
    if years:
        where_clauses.append(f"YEAR(k.kaynti_paiva) IN ({','.join(map(str, years))})")
    if months:
        where_clauses.append(f"MONTH(k.kaynti_paiva) IN ({','.join(map(str, months))})")
    if weeks:
        where_clauses.append(f"WEEK(k.kaynti_paiva) IN ({','.join(map(str, weeks))})")
    if weekdays:
        where_clauses.append(f"k.kaynti_viikonpaiva IN ({','.join(map(str, weekdays))})")
    if hours:
        where_clauses.append(f"k.kaynti_tunti IN ({','.join(map(str, hours))})")
    
    where_str = " AND ".join(where_clauses)
    return conn.execute(f"""
        SELECT ok.kaynti_id, ok.osasto_id, ok.osaston_nimi,
               ok.vietetty_aika_sekunteina, ok.matka_osastolla_m,
               ok.havainnot_osastolla
        FROM f_osastokaynti ok
        INNER JOIN f_kaynti k ON ok.kaynti_id = k.kaynti_id
        INNER JOIN dim_osastot d ON ok.osasto_id = d.osasto_id
        WHERE {where_str}
    """).pl()



@st.cache_data(show_spinner=False, ttl=600)
def _get_baseline_stats(min_dwell: int = 0):
    conn = _get_conn()
    # Lasketaan globaalit keskiarvot vertailupohjaksi
    res = conn.execute("""
        SELECT 
            CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT kaynti_paiva),
            AVG(kesto_sekunteina),
            AVG(matka),
            MEDIAN(kesto_sekunteina),
            MEDIAN(matka)
        FROM f_kaynti
    """).fetchone()
    
    # Osastokäyntien keskiarvo suhteellisella suodatuksella
    res_o = conn.execute(f"""
        SELECT AVG(n) FROM (
            SELECT ok.kaynti_id, COUNT(DISTINCT ok.osasto_id) as n
            FROM f_osastokaynti ok
            INNER JOIN f_kaynti k ON ok.kaynti_id = k.kaynti_id
            INNER JOIN dim_osastot d ON ok.osasto_id = d.osasto_id
            WHERE ok.vietetty_aika_sekunteina >= {min_dwell} * 
                (SQRT(POWER(d.loppu_x-d.alku_x, 2) + POWER(d.loppu_y-d.alku_y, 2)) / 
                (SELECT MAX(SQRT(POWER(loppu_x-alku_x, 2) + POWER(loppu_y-alku_y, 2))) FROM dim_osastot))
            GROUP BY ok.kaynti_id
        )
    """).fetchone()
    
    # Segmenttien osuudet vertailupohjaksi (900s = 15min)
    res_seg = conn.execute("""
        SELECT 
            SUM(CASE WHEN kesto_sekunteina < 900 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0),
            SUM(CASE WHEN kesto_sekunteina >= 900 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0)
        FROM f_kaynti
    """).fetchone()

    return {
        "visits": res[0] or 0,
        "duration": (res[1] or 0) / 60.0,
        "distance": res[2] or 0,
        "med_duration": (res[3] or 0) / 60.0,
        "med_distance": res[4] or 0,
        "depts": res_o[0] or 0,
        "pct_Läpikävelijä": res_seg[0] or 0.0,
        "pct_Tutkiskelija": res_seg[1] or 0.0
    }


# ---------------------------------------------------------------------------
# Render helper
# ---------------------------------------------------------------------------
def _kpi(col, val, label, sub="", delta=None, invert=False):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    delta_html = ""
    if delta is not None:
        cls = "delta-neutral"
        prefix = ""
        if delta > 0.5:
            cls = "delta-down" if invert else "delta-up"
            prefix = "↑ "
        elif delta < -0.5:
            cls = "delta-up" if invert else "delta-down"
            prefix = "↓ "
        delta_html = f'<div class="delta {cls}">{prefix}{abs(delta):.1f}%</div>'

    col.markdown(
        f'<div class="biz-metric">'
        f'<div class="val">{val}</div>'
        f'<div class="lbl">{label}</div>'
        f'{sub_html}{delta_html}</div>',
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
        <h1>📈 Liiketoiminnan tunnusluvut</h1>
        <p>Asiakaskäyttäytymisen analyysi — käynnit, viipymät ja osastojen suosio</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Filters ----------------------------------------------------------
    st.markdown("### ⚙️ Suodattimet")
    
    conn = _get_conn()
    import datetime
    max_d_res = conn.execute("SELECT MAX(kaynti_paiva) FROM f_kaynti").fetchone()
    max_d = max_d_res[0] if max_d_res and max_d_res[0] else datetime.date.today()
    default_start = max_d - datetime.timedelta(days=6)
    
    def reset_filters():
        st.session_state.date_filter = (default_start, max_d)
        st.session_state.time_mode = "date"
        for k in ["sel_weekdays", "sel_hours", "sel_segments", "min_dwell",
                  "sel_years", "sel_months", "sel_weeks",
                  "sel_event_names", "sel_event_years"]:
            if k in st.session_state:
                del st.session_state[k]

    if "date_filter" not in st.session_state:
        st.session_state.date_filter = (default_start, max_d)

    col_btn, col_mode = st.columns([1, 2])
    with col_btn:
        st.button("🔄 Nollaa kaikki valinnat", on_click=reset_filters, use_container_width=True)
    with col_mode:
        time_mode = st.radio(
            "Aikasuodatustapa",
            options=["date", "year", "event"],
            format_func=lambda x: {"date": "📅 Päivämääräalue",
                                    "year": "📆 Vuosivertailu",
                                    "event": "🎄 Erikoistapahtumat"}[x],
            horizontal=True,
            label_visibility="collapsed",
            key="time_mode"
        )

    df_ev = _get_special_events()
    if not df_ev.is_empty():
        df_ev = df_ev.with_columns(
            pl.col("start_date").str.to_date(),
            pl.col("end_date").str.to_date()
        )

    # ── TILA 1: Päivämääräalue ──────────────────────────────────────────────
    if time_mode == "date":
        sel_daterange = st.date_input("Päivämääräalue (oletuksena tuoreimmat 7 pv)", key="date_filter")
        sel_years, sel_months, sel_weeks = [], [], []
        sel_events_filter = None
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_weekdays = st.multiselect(
                "Viikonpäivät", options=list(range(1, 8)),
                format_func=lambda x: WEEKDAY_LABELS[x-1],
                placeholder="Kaikki päivät", key="sel_weekdays")
        with col_f2:
            sel_hours = st.multiselect(
                "Kellonajat", options=list(range(0, 24)),
                format_func=lambda x: f"{x}:00",
                placeholder="Kaikki tunnit", key="sel_hours")

    # ── TILA 2: Vuosivertailu ───────────────────────────────────────────────
    elif time_mode == "year":
        sel_daterange = None
        sel_events_filter = None
        all_years = sorted(conn.execute(
            "SELECT DISTINCT YEAR(kaynti_paiva) FROM f_kaynti").df().iloc[:, 0].tolist())
        sel_years = st.multiselect(
            "Vuodet vertailuun", options=all_years,
            placeholder="Valitse yksi tai useampi vuosi", key="sel_years")
        month_labels = {
            1:"Tammi",2:"Helmi",3:"Maalis",4:"Huhti",5:"Touko",6:"Kesä",
            7:"Heinä",8:"Elo",9:"Syys",10:"Loka",11:"Marras",12:"Joulu"}
        col_m, col_w = st.columns(2)
        with col_m:
            sel_months = st.multiselect(
                "Kuukaudet", options=list(range(1, 13)),
                format_func=lambda x: month_labels[x],
                placeholder="Kaikki kuukaudet", key="sel_months")
        with col_w:
            wc = []
            if sel_years:
                wc.append(f"YEAR(kaynti_paiva) IN ({','.join(map(str, sel_years))})")
            if sel_months:
                wc.append(f"MONTH(kaynti_paiva) IN ({','.join(map(str, sel_months))})")
            wq = "SELECT DISTINCT WEEK(kaynti_paiva) as w FROM f_kaynti"
            if wc:
                wq += " WHERE " + " AND ".join(wc)
            all_weeks = sorted(conn.execute(wq).df().iloc[:, 0].tolist())
            sel_weeks = st.multiselect(
                "Viikot", options=all_weeks,
                placeholder="Kaikki viikot", key="sel_weeks")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_weekdays = st.multiselect(
                "Viikonpäivät", options=list(range(1, 8)),
                format_func=lambda x: WEEKDAY_LABELS[x-1],
                placeholder="Kaikki päivät", key="sel_weekdays")
        with col_f2:
            sel_hours = st.multiselect(
                "Kellonajat", options=list(range(0, 24)),
                format_func=lambda x: f"{x}:00",
                placeholder="Kaikki tunnit", key="sel_hours")

    # ── TILA 3: Erikoistapahtumat ───────────────────────────────────────────
    else:
        sel_daterange = None
        sel_years, sel_months, sel_weeks, sel_weekdays = [], [], [], []
        sel_events_filter = None
        if not df_ev.is_empty():
            unique_names = sorted(df_ev["event_name"].unique().to_list())
            all_ev_years = sorted(df_ev["start_date"].dt.year().unique().to_list())
            col_ev, col_evy = st.columns(2)
            with col_ev:
                sel_event_names = st.multiselect(
                    "Tapahtuma", options=unique_names,
                    placeholder="Valitse tapahtuma...",
                    help="Ostopiikki ajoittuu tyypillisesti 1–3 pv ennen varsinaista tapahtumaa.",
                    key="sel_event_names")
            with col_evy:
                sel_event_years = st.multiselect(
                    "Vuodet", options=all_ev_years,
                    placeholder="Kaikki vuodet", key="sel_event_years")
            df_ev_f = df_ev
            if sel_event_names:
                df_ev_f = df_ev_f.filter(pl.col("event_name").is_in(sel_event_names))
            if sel_event_years:
                df_ev_f = df_ev_f.filter(pl.col("start_date").dt.year().is_in(sel_event_years))
            sel_events_filter = df_ev_f if (sel_event_names or sel_event_years) else None
        else:
            st.warning("Erikoistapahtumatietoja ei löydy.")

        if not sel_event_names:
            st.info("⬆️ Valitse ensin tapahtuma (esim. 'Joulu') — dashboard suodattuu automaattisesti sen ajankohdalle. Voit vertailla useita vuosia rinnakkain.")

        sel_hours = st.multiselect(
            "Kellonajat", options=list(range(0, 24)),
            format_func=lambda x: f"{x}:00",
            placeholder="Kaikki tunnit (tapahtumapäivinä)", key="sel_hours",
            help="Suodata tiettyihin kellonaikoihin tapahtumapäivinä.")

    # --- Apply Time Filters ------------------------------------------------
    if time_mode in ("date", "year"):
        sel_events_filter = None
        effective_weekdays = sel_weekdays
    else:
        effective_weekdays = []

    raw_df = _kaynti(sel_years, sel_months, sel_weeks, effective_weekdays, sel_hours)

    if time_mode == "event" and sel_events_filter is not None and not sel_events_filter.is_empty():
        mask = pl.lit(False)
        for row in sel_events_filter.to_dicts():
            s = pl.lit(str(row["start_date"])).str.to_date()
            e = pl.lit(str(row["end_date"])).str.to_date()
            mask = mask | ((pl.col("kaynti_paiva") >= s) & (pl.col("kaynti_paiva") <= e))
        raw_df = raw_df.filter(mask)
    elif time_mode == "date" and sel_daterange:
        if isinstance(sel_daterange, tuple) and len(sel_daterange) == 2:
            s_date, e_date = sel_daterange
            raw_df = raw_df.filter(
                (pl.col("kaynti_paiva") >= s_date) & (pl.col("kaynti_paiva") <= e_date))
        elif isinstance(sel_daterange, tuple) and len(sel_daterange) == 1:
            raw_df = raw_df.filter(pl.col("kaynti_paiva") == sel_daterange[0])
        elif isinstance(sel_daterange, datetime.date):
            raw_df = raw_df.filter(pl.col("kaynti_paiva") == sel_daterange)

    def classify_visit(sec):
        if sec < 900: return "Läpikävelijä"
        return "Tutkiskelija"

    if not raw_df.is_empty():
        raw_df = raw_df.with_columns(
            pl.col("kesto_sekunteina").map_elements(classify_visit, return_dtype=pl.String).alias("segment")
        )
        segment_counts = raw_df["segment"].value_counts().sort("count", descending=True)
        seg_options = segment_counts["segment"].to_list()
    else:
        seg_options = []

    st.markdown("---")
    col_seg1, col_seg2 = st.columns([1, 2])
    with col_seg1:
        sel_segments = st.multiselect("Kävijäsegmentit", options=seg_options, placeholder="Kaikki segmentit", key="sel_segments")
    with col_seg2:
        min_dwell = st.slider("Osastokohtainen viipymäsuodatin (sekunteina, suhteellinen)", 0, 300, 30, help="Suodattaa pois läpikulut osastotasolla.", key="min_dwell")

    # --- Apply Segment Filter ----------------------------------------------
    df = raw_df
    if sel_segments:
        df = df.filter(pl.col("segment").is_in(sel_segments))
    # Suodataan osastodata aina vastaamaan raw_df/df sisältöä (daterange, tapahtumat, segmentit)
    valid_ids = df["kaynti_id"].to_list()
    df_o = _osasto(sel_years, sel_months, sel_weeks, effective_weekdays, sel_hours, min_dwell).filter(pl.col("kaynti_id").is_in(valid_ids))

    # --- Load baseline (updated with min_dwell) ----------------------------
    baseline = _get_baseline_stats(min_dwell)

    if df.is_empty():
        st.warning("Ei käyntejä valitulla aikavälillä.")
        st.stop()

    # --- KPI calculations --------------------------------------------------
    baseline = _get_baseline_stats()
    
    days_count = df["kaynti_paiva"].n_unique()
    total_visits = len(df)
    v_per_day = total_visits / days_count if days_count > 0 else 0
    
    avg_dur = df["kesto_sekunteina"].mean() / 60.0
    med_dur = df["kesto_sekunteina"].median() / 60.0
    avg_dist = df["matka"].mean()
    med_dist = df["matka"].median()
    avg_spd = df["keskinopeus"].mean()

    # Deltas
    def get_d(curr, base):
        return (curr - base) / base * 100.0 if base > 0 else 0

    d_visits = get_d(v_per_day, baseline["visits"])
    d_dur = get_d(med_dur, baseline["med_duration"])
    d_dist = get_d(med_dist, baseline["med_distance"])

    hour_top = df.group_by("kaynti_tunti").agg(pl.len().alias("n")).sort("n", descending=True)
    busiest_h = int(hour_top["kaynti_tunti"][0])

    wd_top = df.group_by("kaynti_viikonpaiva").agg(pl.len().alias("n")).sort("n", descending=True)
    busiest_wd = WEEKDAY_LABELS[int(wd_top["kaynti_viikonpaiva"][0]) - 1]

    depts_per = 0.0
    if not df_o.is_empty():
        depts_per = df_o.group_by("kaynti_id").agg(
            pl.col("osasto_id").n_unique().alias("n")
        )["n"].mean()
    d_depts = get_d(depts_per, baseline["depts"])

    # --- KPI cards ---------------------------------------------------------
    st.markdown('<div class="biz-section">📊 Yhteenveto ja vertailu keskiarvoon</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, f"{total_visits:,}", "Käyntejä yhteensä", f"{v_per_day:.1f} / päivä", delta=d_visits)
    _kpi(c2, f"{med_dur:.1f}", "Tyypillinen kesto (min)", f"Keskiarvo {avg_dur:.1f} min", delta=d_dur)
    _kpi(c3, f"{med_dist:.0f}", "Tyypillinen matka (m)", f"Keskiarvo {avg_dist:.0f} m", delta=d_dist)
    _kpi(c4, f"{depts_per:.1f}", "Osastoja per käynti", delta=d_depts)

    # Segmenttijakauma-rivi
    if not df.is_empty():
        st.markdown('<div class="biz-section">👥 Kävijäsegmenttien jakauma</div>', unsafe_allow_html=True)
        counts = df["segment"].value_counts().sort("count", descending=True)
        labels = counts["segment"].to_list()
        values = counts["count"].to_list()
        
        # Näytetään segmentit pieninä metric-kortteina
        cols = st.columns(len(labels))
        for i, (lbl, val) in enumerate(zip(labels, values)):
            percent = (val / total_visits) * 100
            
            # Erotus keskiarvosta (baseline)
            base_pct = baseline.get(f"pct_{lbl}", 0.0)
            diff = percent - base_pct
            
            cols[i].metric(lbl, f"{val:,} kpl ({percent:.1f} %)", f"{diff:+.1f} %-yks")

    # --- Vuosivertailu erikoistapahtumatilassa --------------------------------
    if time_mode == "event" and sel_events_filter is not None and not df.is_empty():
        years_in_data = sorted(df.with_columns(
            pl.col("kaynti_paiva").dt.year().alias("vuosi")
        )["vuosi"].unique().to_list())
        if len(years_in_data) > 1:
            st.markdown('<div class="biz-section">📆 Vuosikohtainen vertailu</div>', unsafe_allow_html=True)
            st.caption("Tunnusluvut eriteltynä valitun tapahtuman eri vuosille.")
            year_cols = st.columns(len(years_in_data))
            df_with_year = df.with_columns(pl.col("kaynti_paiva").dt.year().alias("vuosi"))
            for ci, yr in enumerate(years_in_data):
                yr_df = df_with_year.filter(pl.col("vuosi") == yr)
                yr_visits = len(yr_df)
                yr_days = yr_df["kaynti_paiva"].n_unique()
                yr_dur = yr_df["kesto_sekunteina"].median() / 60.0
                yr_dist = yr_df["matka"].median()
                yr_seg = yr_df["segment"].value_counts().sort("count", descending=True)
                seg_str = "  |  ".join(
                    f"{row['segment']}: {(row['count']/yr_visits*100):.0f}%"
                    for row in yr_seg.to_dicts()
                )
                with year_cols[ci]:
                    st.markdown(f"**{yr}**")
                    st.metric("Käyntejä", f"{yr_visits:,} ({yr_days} pv)")
                    st.metric("Kesto (med.)", f"{yr_dur:.1f} min")
                    st.metric("Matka (med.)", f"{yr_dist:.0f} m")
                    st.caption(seg_str)

    # Vilkkain tunti ja viikonpäivä näytetään (jos suodattimia ei ole rajoitettu)
    if not sel_hours or not sel_weekdays:
        c5, c6, c7, c8 = st.columns(4)
        if not sel_hours:
            _kpi(c5, f"{busiest_h}:00", "Vilkkain tunti")
        if not sel_weekdays:
            _kpi(c6, busiest_wd, "Vilkkain viikonpäivä")
        _kpi(c7, f"{df['matka'].max():.0f}", "Pisin reitti (m)")
        _kpi(c8, f"{df['kesto_sekunteina'].max() / 60:.0f}", "Pisin käynti (min)")

    # --- 1. Daily trend ----------------------------------------------------
    st.markdown('<div class="biz-section">📅 Käynnit päivittäin</div>', unsafe_allow_html=True)

    fig_trend = go.Figure()
    if time_mode in ("year", "event"):
        # Eri vuodet eri väreillä — valmiit hex+rgba-parit
        YEAR_COLORS = [
            ("#3b82f6", "rgba(59,130,246,0.08)"),
            ("#10b981", "rgba(16,185,129,0.08)"),
            ("#f59e0b", "rgba(245,158,11,0.08)"),
            ("#ef4444", "rgba(239,68,68,0.08)"),
            ("#8b5cf6", "rgba(139,92,246,0.08)"),
        ]
        df_dated = df.with_columns(pl.col("kaynti_paiva").dt.year().alias("vuosi"))
        for yi, yr in enumerate(sorted(df_dated["vuosi"].unique().to_list())):
            yr_daily = (df_dated.filter(pl.col("vuosi") == yr)
                        .group_by("kaynti_paiva").agg(pl.len().alias("n")).sort("kaynti_paiva"))
            color, fill_color = YEAR_COLORS[yi % len(YEAR_COLORS)]
            fig_trend.add_trace(go.Scatter(
                x=yr_daily["kaynti_paiva"].to_list(), y=yr_daily["n"].to_list(),
                mode="lines+markers", name=str(yr),
                line=dict(color=color, width=2.5),
                marker=dict(size=5, color=color),
                fill="tozeroy", fillcolor=fill_color,
                hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
            ))
    else:
        daily = df.group_by("kaynti_paiva").agg(pl.len().alias("n")).sort("kaynti_paiva")
        fig_trend.add_trace(go.Scatter(
            x=daily["kaynti_paiva"].to_list(), y=daily["n"].to_list(),
            mode="lines+markers", line=dict(color="#3b82f6", width=2.5),
            marker=dict(size=5, color="#3b82f6"),
            fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
            hovertemplate="<b>%{x}</b><br>Käyntejä: %{y}<extra></extra>",
        ))
        daily_for_ma = df.group_by("kaynti_paiva").agg(pl.len().alias("n")).sort("kaynti_paiva")
        if len(daily_for_ma) >= 7:
            ma7 = daily_for_ma.with_columns(pl.col("n").rolling_mean(window_size=7).alias("ma7"))
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
            pl.col("vietetty_aika_sekunteina").median().alias("med_s"),
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
            st.markdown("**Tyypillinen viipymäaika osastoittain (mediaani)**")
            dw = ds.sort("med_s", descending=True)
            dn = dw["osaston_nimi"].to_list()
            dt_vals = [s / 60.0 for s in dw["med_s"].to_list()]
            fig_d = go.Figure(go.Bar(
                y=dn[::-1], x=dt_vals[::-1], orientation="h",
                marker=dict(color=dt_vals[::-1], colorscale="Oranges"),
                text=[f"{d:.1f} min" for d in dt_vals[::-1]], textposition="outside",
                hovertemplate="<b>%{y}</b><br>Mediaaniviipymä: %{x:.1f} min<extra></extra>",
            ))
            fig_d.update_layout(
                height=420, margin=dict(l=160, r=70, t=10, b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(248,250,252,1)",
                xaxis=dict(title="Viipymä (min)"), showlegend=False,
            )
            st.plotly_chart(fig_d, width="stretch")

    # --- 4. Duration histogram ---------------------------------------------
    st.markdown('<div class="biz-section">⏱️ Käyntiajan jakauma</div>', unsafe_allow_html=True)
    st.caption("Kuinka pitkiä asiakkaiden kauppareissut ovat?", help="Värien merkitys kestolle:\n\n🟢 Vihreä: Alle 30 min\n\n🔵 Sininen: 30–60 min\n\n🟠 Oranssi: 60–90 min\n\n🔴 Punainen: Yli 90 min")

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
    st.caption("Kuinka pitkän matkan asiakkaat kävelevät kaupassa?", help="Värien merkitys matkalle:\n\n🟢 Vihreä: Alle 500 m\n\n🔵 Sininen: 500–1000 m\n\n🟠 Oranssi: 1000–2000 m\n\n🔴 Punainen: Yli 2000 m")

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

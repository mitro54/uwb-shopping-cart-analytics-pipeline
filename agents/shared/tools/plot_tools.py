"""
ByteBuddies UWB Dashboard analytiikka sovelluksen visualisointityökalut.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations

import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg') # Käytetään palvelinpohjaista renderöintiä ilman GUI:ta
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import duckdb
from langchain_core.tools import tool
from agents.shared.config import CONFIG

# Ensure the output directory exists
OUTPUT_DIR = Path("data/processed/plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def _get_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
    dbt_path = CONFIG.duckdb_path.parent.parent.parent / "bytebuddies_dbt"
    conn.execute(f"SET FILE_SEARCH_PATH = '{dbt_path.as_posix()}'")
    return conn

@tool
def plot_chart(sql: str, chart_type: str, x_col: str, y_col: str, title: str = "Analysis Chart") -> str:
    """
    Luo pylväs-, viiva- tai pistekaavion SQL-kyselyn perusteella.
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "Kysely ei palauttanut dataa kuvaajaa varten."

        plt.figure(figsize=(10, 6))
        ax = plt.gca()
        if chart_type == "bar":
            sns.barplot(data=df, x=x_col, y=y_col, hue=x_col, palette="viridis", legend=False)
            # Lisää luvut pylväiden päälle (pyöristettynä kokonaisluvuiksi)
            for p in ax.patches:
                height = p.get_height()
                if not np.isnan(height):
                    ax.annotate(f'{int(round(height))}', 
                                (p.get_x() + p.get_width() / 2., height), 
                                ha = 'center', va = 'center', 
                                xytext = (0, 9), 
                                textcoords = 'offset points',
                                fontsize=9, fontweight='bold')
            ax.margins(y=0.20) # Lisää tilaa yläreunaan numeroille
        elif chart_type == "line":
            sns.lineplot(data=df, x=x_col, y=y_col, marker='o')
        elif chart_type == "scatter":
            sns.scatterplot(data=df, x=x_col, y=y_col)
        else:
            return f"Kuvaajatyyppiä ei ole tuettu: {chart_type}"

        plt.title(title, fontsize=12, pad=15)
        plt.xticks(rotation=90) # Käännetään tekstit 90 astetta
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        filename = f"{chart_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath)
        plt.close()

        return f"Kuvaaja luotu onnistuneesti: {filepath.absolute()}"
    except Exception as e:
        return f"Virhe kuvaajan luomisessa: {e}"

@tool
def plot_distribution(sql: str, category_col: str, value_col: str, title: str = "Jakauma-analyysi") -> str:
    """
    Luo Violin plot -jakaumakuvaajan. Sopii erinomaisesti viipymäaikojen tai nopeuksien
    vaihtelun visualisointiin eri osastojen välillä.
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "Kysely ei palauttanut dataa."

        plt.figure(figsize=(12, 7))
        
        # Älykäs skaalaus: leikataan ääripään outlierit (yli 95. persentiili), jos ne venyttävät akselia liikaa
        y_limit = df[value_col].quantile(0.95)
        if df[value_col].max() > y_limit * 2:
            df_plot = df[df[value_col] <= y_limit].copy()
            title += " (95% dataa, extremit leikattu)"
        else:
            df_plot = df

        # Määritetään osastojen järjestys alkuperäisestä datasta, jotta luvut ja viulut täsmäävät
        categories = df[category_col].unique()
        
        ax = sns.violinplot(data=df_plot, x=category_col, y=value_col, hue=category_col, 
                            order=categories, inner="box", palette="viridis", legend=False)
        
        # Lisätään 5-luvun yhteenveto (min, Q1, mediaani, Q3, max) ALKUPERÄISESTÄ datasta
        for i, cat in enumerate(categories):
            # TÄRKEÄÄ: Lasketaan luvut alkuperäisestä df:stä, ei leikatusta df_plot:sta
            full_cat_data = df[df[category_col] == cat][value_col]
            if len(full_cat_data) > 0:
                s = np.percentile(full_cat_data, [0, 25, 50, 75, 100])
                
                # Luodaan päällekkäinen tekstipaketti
                stats_text = (
                    f"max: {int(s[4])}\n"
                    f"q3:  {int(s[3])}\n"
                    f"med: {int(s[2])}\n"
                    f"q1:  {int(s[1])}\n"
                    f"min: {int(s[0])}"
                )
                
                # Sijoitetaan laatikko viulun oikealle puolelle (df_plot:n medianin korkeudelle, jotta se on näkyvissä)
                # Jos koko datan median on leikkausrajan ulkopuolella, käytetään leikatun datan mediania sijoitukseen
                plot_cat_data = df_plot[df_plot[category_col] == cat][value_col]
                y_pos = np.median(plot_cat_data) if len(plot_cat_data) > 0 else s[2]

                ax.text(i + 0.32, y_pos, stats_text, 
                        va='center', ha='left', fontsize=6, family='monospace',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7, edgecolor="gray", lw=0.5))

        plt.title(title, fontsize=14, pad=20)
        plt.xticks(rotation=90)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        filename = f"violin_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath)
        plt.close()

        return f"Jakaumakuvaaja luotu: {filepath.absolute()}"
    except Exception as e:
        return f"Virhe jakaumakuvaajan luomisessa: {e}"

@tool
def plot_grouped_bar(sql: str, x_col: str, y_col: str, hue_col: str, title: str = "Ryhmitelty analyysi") -> str:
    """
    Luo ryhmitellyn pylväsdiagrammin (Clustered Bar Chart), jossa on kaksi kategoriaa ja yksi arvo.
    Esim: x_col='kuukausi', y_col='vietetty_aika', hue_col='osasto'.
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "Kysely ei palauttanut dataa ryhmiteltyä kaaviota varten."

        # Asetetaan teema
        sns.set_theme(style="whitegrid")
        plt.figure(figsize=(14, 8))
        
        # Piirretään kaavio
        ax = sns.barplot(
            data=df, 
            x=x_col, 
            y=y_col, 
            hue=hue_col,
            errorbar=None,
            palette='tab10'
        )

        # Lisätään numeroarvot jokaisen pylvään päälle
        for container in ax.containers:
            ax.bar_label(container, fmt='%.0f', padding=3, fontsize=8, rotation=90)

        plt.title(title, fontweight='bold', fontsize=14, pad=20)
        plt.xticks(rotation=45)
        
        # Siirretään selite oikealle puolelle ulkopuolelle
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', title=hue_col)
        
        plt.tight_layout()

        filename = f"grouped_bar_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath, bbox_inches='tight')
        plt.close()

        return f"Ryhmitelty pylväskaavio luotu: {filepath.absolute()}"
    except Exception as e:
        return f"Virhe ryhmitellyn kaavion luomisessa: {e}"

import plotly.express as px
import plotly.io as pio

@tool
def plot_interactive(sql: str, chart_type: str, x_col: str, y_col: str, title: str = "Interaktiivinen analyysi") -> str:
    """
    Luo interaktiivisen Plotly-kuvaajan.
    chart_type: 'bar', 'line', 'scatter'
    Tallentaa kuvaajan JSON-muodossa Streamlitia varten.
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "Kysely ei palauttanut dataa visualisointia varten."

        if chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title, template="plotly_white")
        elif chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, template="plotly_white")
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_col, y=y_col, title=title, template="plotly_white")
        else:
            return f"Tukematon kaaviotyyppi: {chart_type}"

        # Älykäs skaalaus: jos data on hyvin kapealla välillä, ei aloiteta nollasta
        y_min = df[y_col].min()
        y_max = df[y_col].max()
        if y_min > 0 and (y_max - y_min) / y_max < 0.2:
            fig.update_layout(yaxis=dict(range=[y_min * 0.98, y_max * 1.02]))

        filename = f"interactive_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = OUTPUT_DIR / filename
        pio.write_json(fig, str(filepath))

        return f"Interaktiivinen visualisointi luotu: {filepath.absolute()}"
    except Exception as e:
        return f"Virhe Plotly-visualisoinnissa: {e}"

ALL_PLOT_TOOLS = [plot_chart, plot_distribution, plot_grouped_bar, plot_interactive]

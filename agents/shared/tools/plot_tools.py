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
        if chart_type == "bar":
            sns.barplot(data=df, x=x_col, y=y_col)
        elif chart_type == "line":
            sns.lineplot(data=df, x=x_col, y=y_col)
        elif chart_type == "scatter":
            sns.scatterplot(data=df, x=x_col, y=y_col)
        else:
            return f"Kuvaajatyyppiä ei ole tuettu: {chart_type}"

        plt.title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        filename = f"{chart_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath)
        plt.close()

        return f"Kuvaaja luotu onnistuneesti: {filepath.absolute()}"
    except Exception as e:
        return f"Virhe kuvaajan luomisessa: {e}"

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

ALL_PLOT_TOOLS = [plot_chart, plot_interactive]

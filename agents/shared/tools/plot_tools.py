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
    return duckdb.connect(str(CONFIG.duckdb_path), read_only=True)

@tool
def plot_heatmap(sql: str, x_col: str, y_col: str, title: str = "UWB Heatmap") -> str:
    """
    Generates a heatmap based on a SQL query. 
    The SQL should return at least x and y coordinates.
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "Query returned no data for heatmap."

        plt.figure(figsize=(10, 8))
        sns.kdeplot(data=df, x=x_col, y=y_col, fill=True, cmap="rocket", thresh=0.05, levels=20)
        plt.title(title)
        
        filename = f"heatmap_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath)
        plt.close()

        return f"Heatmap generated successfully: {filepath.absolute()}"
    except Exception as e:
        return f"Error generating heatmap: {e}"

@tool
def plot_chart(sql: str, chart_type: str, x_col: str, y_col: str, title: str = "Analysis Chart") -> str:
    """
    Generates a bar, line or scatter chart.
    chart_type options: 'bar', 'line', 'scatter'
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "Query returned no data for chart."

        plt.figure(figsize=(10, 6))
        if chart_type == "bar":
            sns.barplot(data=df, x=x_col, y=y_col)
        elif chart_type == "line":
            sns.lineplot(data=df, x=x_col, y=y_col)
        elif chart_type == "scatter":
            sns.scatterplot(data=df, x=x_col, y=y_col)
        else:
            return f"Unsupported chart type: {chart_type}"

        plt.title(title)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        filename = f"{chart_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath)
        plt.close()

        return f"Chart generated successfully: {filepath.absolute()}"
    except Exception as e:
        return f"Error generating chart: {e}"

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

ALL_PLOT_TOOLS = [plot_heatmap, plot_chart, plot_interactive]

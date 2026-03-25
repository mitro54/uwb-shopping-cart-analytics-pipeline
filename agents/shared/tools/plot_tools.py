from __future__ import annotations

import os
from pathlib import Path
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

ALL_PLOT_TOOLS = [plot_heatmap, plot_chart]

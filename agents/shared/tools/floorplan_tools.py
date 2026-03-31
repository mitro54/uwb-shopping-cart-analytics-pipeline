"""
Pohjapiirrostyökalu: piirtää UWB-dataa kaupan pohjapiirroksen (kauppa2.png) päälle.

Koordinaattikartoitus:
- UWB-data on senttimetreissä, muunnetaan metreihin (÷100)
- Kaupan mitat: 104.06 m × 52.20 m
- kuva kauppa2.png kartoitetaan näihin mittoihin
"""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import duckdb
from langchain_core.tools import tool

from agents.shared.config import CONFIG

# ── Polut ──
FLOORPLAN_PATH = Path(__file__).resolve().parents[3] / "image" / "kauppa2.png"
OUTPUT_DIR = Path("data/processed/plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Kaupan mitat (metreissä) ──
X_MAX_M = 104.06
Y_MAX_M = 52.20

# ── Latausasemat (ei asiakasliikennettä) ──
CHARGING_STATION_1 = (0, 5, 21.5, 30.0)     # (x_min, x_max, y_min, y_max)
CHARGING_STATION_2 = (8.5, 9.5, 35.5, 36.5)

# ── Poistettavat alueet ──
EXCLUDE_ZONE_1 = {"y_gt": 30.0, "x_lt": 15.0}  # Varastoalue vasen yläkulma
EXCLUDE_ZONE_2 = {"y_lt": 5.0, "x_gt": 85.0}   # Lastauslaituri oikea alakulma

# ── Kassavyöhyke ──
CASHIER_ZONE_X_MAX = 8.0
CASHIER_ZONE_Y_MIN = 5.0
CASHIER_ZONE_Y_MAX = 30.0


def _get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(CONFIG.duckdb_path), read_only=True)


def _filter_valid_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Suodattaa datasta vain kaupan alueella olevat pisteet ja poistaa ei-kiinnostavat alueet."""
    # Muunna cm → m
    df = df.copy()
    df["x_m"] = df["x"] / 100.0
    df["y_m"] = df["y"] / 100.0

    # Rajaa kaupan alueelle
    mask = (
        (df["x_m"] >= 0) & (df["x_m"] <= X_MAX_M) &
        (df["y_m"] >= 0) & (df["y_m"] <= Y_MAX_M)
    )

    # Poista latausasemat
    for cs in [CHARGING_STATION_1, CHARGING_STATION_2]:
        x_min, x_max, y_min, y_max = cs
        mask &= ~(
            (df["x_m"] >= x_min) & (df["x_m"] <= x_max) &
            (df["y_m"] >= y_min) & (df["y_m"] <= y_max)
        )

    # Poista exclude-vyöhykkeet
    mask &= ~((df["y_m"] > EXCLUDE_ZONE_1["y_gt"]) & (df["x_m"] < EXCLUDE_ZONE_1["x_lt"]))
    mask &= ~((df["y_m"] < EXCLUDE_ZONE_2["y_lt"]) & (df["x_m"] > EXCLUDE_ZONE_2["x_gt"]))

    return df[mask]


@tool
def plot_on_floorplan(
    sql: str,
    title: str = "Ostoskärryjen liike",
    plot_type: str = "heatmap",
    alpha: float = 0.55,
) -> str:
    """
    Piirtää UWB-positiontidataa kaupan pohjapiirroksen päälle.

    Parametrit:
    - sql: SQL-kysely joka palauttaa x ja y sarakkeet (cm-yksikössä).
           Voit lisätä WHERE-ehtoja rajoittaaksesi ajanjakson, node_id:n jne.
           Esim: SELECT x, y FROM main.stg_csv_data WHERE timestamp BETWEEN '2019-03-08' AND '2019-03-09' LIMIT 500000
    - title: Kuvan otsikko
    - plot_type: 'heatmap' (oletus, KDE-tiheys) tai 'scatter' (yksittäiset pisteet)
    - alpha: Läpinäkyvyys (0.0–1.0)
    """
    try:
        conn = _get_conn()
        df = conn.execute(sql).fetchdf()
        conn.close()

        if df.empty:
            return "SQL-kysely ei palauttanut dataa."

        if "x" not in df.columns or "y" not in df.columns:
            return f"Virhe: SQL-kyselyn tulee palauttaa 'x' ja 'y' sarakkeet. Löydetyt sarakkeet: {list(df.columns)}"

        # Suodata validit positiot
        df = _filter_valid_positions(df)

        if df.empty or len(df) < 10:
            return "Suodatuksen jälkeen jäi liian vähän datapisteitä (<10). Tarkista SQL-kysely tai ajanjakso."

        # Lataa pohjapiirros
        if not FLOORPLAN_PATH.exists():
            return f"Virhe: Pohjapiirrostiedostoa ei löydy: {FLOORPLAN_PATH}"

        img = mpimg.imread(str(FLOORPLAN_PATH))
        img_h, img_w = img.shape[:2]

        fig, ax = plt.subplots(1, 1, figsize=(16, 8), dpi=120)

        # Näytä pohjapiirros
        ax.imshow(img, extent=[0, X_MAX_M, 0, Y_MAX_M], aspect="auto", zorder=0)

        if plot_type == "heatmap":
            # KDE-pohjainen heatmap pohjapiirrroksen päälle
            x_bins = np.linspace(0, X_MAX_M, 300)
            y_bins = np.linspace(0, Y_MAX_M, 150)

            heatmap_data, xedges, yedges = np.histogram2d(
                df["x_m"].values, df["y_m"].values,
                bins=[x_bins, y_bins],
            )

            # Tasoita (numpy-pohjainen uniform smoothing, korvaa scipy gaussian_filter)
            def _smooth_2d(arr, passes=3, kernel_size=9):
                """Uniform box filter applied repeatedly to approximate Gaussian smoothing."""
                result = arr.astype(float)
                pad = kernel_size // 2
                for _ in range(passes):
                    padded = np.pad(result, pad, mode="constant", constant_values=0)
                    # Cumsum-pohjainen box blur riveille
                    cs = np.cumsum(padded, axis=1)
                    cs = cs[:, kernel_size:] - cs[:, :-kernel_size]
                    # Cumsum-pohjainen box blur sarakkeille
                    cs2 = np.cumsum(cs, axis=0)
                    result = (cs2[kernel_size:] - cs2[:-kernel_size]) / (kernel_size * kernel_size)
                return result

            heatmap_smooth = _smooth_2d(heatmap_data.T)

            # Maskaa tyhjät alueet
            heatmap_masked = np.ma.masked_where(heatmap_smooth < heatmap_smooth.max() * 0.01, heatmap_smooth)

            ax.imshow(
                heatmap_masked,
                extent=[0, X_MAX_M, 0, Y_MAX_M],
                origin="lower",
                cmap="YlOrRd",
                alpha=alpha,
                aspect="auto",
                zorder=1,
            )
            # Väripalkki
            sm = plt.cm.ScalarMappable(cmap="YlOrRd", norm=plt.Normalize(vmin=0, vmax=heatmap_smooth.max()))
            sm.set_array([])
            cbar = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
            cbar.set_label("Käyntitiheys", fontsize=10)

        elif plot_type == "scatter":
            # Scatter pisteet
            sample = df if len(df) <= 50000 else df.sample(50000, random_state=42)
            ax.scatter(
                sample["x_m"], sample["y_m"],
                s=1, alpha=max(0.02, alpha * 0.3), c="#FF4444", zorder=1,
            )

        # Tyylittelyt
        ax.set_xlim(0, X_MAX_M)
        ax.set_ylim(0, Y_MAX_M)
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
        ax.set_xlabel("x (m)", fontsize=10)
        ax.set_ylabel("y (m)", fontsize=10)

        # Info-teksti
        info_text = f"Datapisteitä: {len(df):,}"
        ax.text(
            0.01, 0.01, info_text, transform=ax.transAxes,
            fontsize=8, color="white", alpha=0.8,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="black", alpha=0.5),
        )

        plt.tight_layout()

        filename = f"floorplan_{plot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = OUTPUT_DIR / filename
        fig.savefig(filepath, dpi=120, bbox_inches="tight")
        plt.close(fig)

        return f"Pohjapiirrosvisualisointi luotu: {filepath.absolute()}"

    except Exception as e:
        return f"Virhe pohjapiirrosvisualisoinnissa: {e}"


ALL_FLOORPLAN_TOOLS = [plot_on_floorplan]

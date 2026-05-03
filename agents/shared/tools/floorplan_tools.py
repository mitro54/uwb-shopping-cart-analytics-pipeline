"""
Pohjapiirrostyökalu: piirtää UWB-dataa kaupan pohjapiirroksen (kauppa2.png) päälle.

Koordinaattikartoitus:
- UWB-data on senttimetreissä, muunnetaan metreihin
- Kaupan mitat: 104.06 m x 52.20 m (huomioi koordinaattimuunnoksen)
- kuva kauppa2.png kartoitetaan näihin mittoihin

Kirjoittaja: Toni Kiuru
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

import json

# ── Polut ──
FLOORPLAN_PATH = Path(__file__).resolve().parents[3] / CONFIG.floorplan_image_path
ZONES_PATH = Path(__file__).resolve().parents[3] / "bytebuddies_dbt" / "seeds" / "osastot.csv"
OUTPUT_DIR = Path("data/processed/plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Kaupan mitat (metreissä) ──
X_MAX_M = CONFIG.store_width_m
Y_MAX_M = CONFIG.store_height_m

# ── Latausasemat / Suodatetut alueet ──
def _get_excluded_zones():
    try:
        return json.loads(CONFIG.excluded_zones_json)
    except Exception:
        return []

# ── Kassavyöhyke ──
CASHIER_ZONE_X_MIN = CONFIG.checkout_x_min
CASHIER_ZONE_X_MAX = CONFIG.checkout_x_max
CASHIER_ZONE_Y_MIN = CONFIG.checkout_y_min
CASHIER_ZONE_Y_MAX = CONFIG.checkout_y_max


def _get_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
    dbt_path = CONFIG.duckdb_path.parent.parent.parent / "bytebuddies_dbt"
    conn.execute(f"SET FILE_SEARCH_PATH = '{dbt_path.as_posix()}'")
    return conn


def _load_zones() -> pd.DataFrame | None:
    """Lataa osastojen rajat CSV-tiedostosta."""
    if not ZONES_PATH.exists():
        return None
    try:
        return pd.read_csv(ZONES_PATH)
    except Exception:
        return None


def _draw_zones(ax: matplotlib.axes.Axes, zones_df: pd.DataFrame):
    """Piirtää osastojen rajat ja nimekkeet kuvaan."""
    import matplotlib.patches as patches
    for _, row in zones_df.iterrows():
        # Muunnetaan cm -> m
        x_min, y_min = row["alku_x"] / 100.0, row["alku_y"] / 100.0
        x_max, y_max = row["loppu_x"] / 100.0, row["loppu_y"] / 100.0
        width = x_max - x_min
        height = y_max - y_min
        
        # Piirretään suorakulmio
        rect = patches.Rectangle(
            (x_min, y_min), width, height,
            linewidth=1, edgecolor="blue", facecolor="blue", alpha=0.1,
            zorder=0.5
        )
        ax.add_patch(rect)
        
        # Lisätään osaston nimi (lyhennettynä jos tarpeen)
        name = row["nimi"].replace(" ja ", " & ").capitalize()
        ax.text(
            x_min + width/2, y_min + height/2, name,
            color="darkblue", fontsize=7, alpha=0.6,
            ha="center", va="center", rotation=30,
            zorder=0.6
        )


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

    # Poista suodatetut alueet (latausasemat, varastot jne.)
    excluded = _get_excluded_zones()
    for zone in excluded:
        x_min, x_max = zone.get("x_min", 0), zone.get("x_max", 0)
        y_min, y_max = zone.get("y_min", 0), zone.get("y_max", 0)
        mask &= ~(
            (df["x_m"] >= x_min) & (df["x_m"] <= x_max) &
            (df["y_m"] >= y_min) & (df["y_m"] <= y_max)
        )

    return df[mask]


@tool
def plot_on_floorplan(
    sql: str,
    title: str = "Ostoskärryjen liike",
    plot_type: str = "heatmap",
    alpha: float = 0.55,
    show_zones: bool = False,
) -> str:
    """
    Piirtää UWB-positiontidataa kaupan pohjapiirroksen päälle.

    Parametrit:
    - sql: SQL-kysely joka palauttaa x ja y sarakkeet (cm-yksikössä).
           Route-tyypissä vaaditaan myös 'node_id' tai järjestys (aikaleima).
           Dwell-tyypissä vaaditaan 'dwell_time' tai 'weight'.
           Esim: SELECT x, y FROM main.gold_koordinaatit
    - title: Kuvan otsikko
    - plot_type: 
        - 'heatmap': KDE-tiheyskartta (oletus)
        - 'scatter': Yksittäiset havaintopisteet
        - 'route': Viivalla yhdistetty kulkureitti
        - 'dwell': Pysähdyspaikat (markerin koko riippuu vaipymästä)
    - alpha: Peittävyys (0.0–1.0)
    - show_zones: Jos True, piirtää osastojen rajat ja nimet
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
        ax.imshow(img, extent=[0, X_MAX_M, Y_MAX_M, 0], aspect="auto", zorder=0)

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

        elif plot_type == "route":
            # Reitti: yhdistetään peräkkäiset pisteet viivalla
            ax.plot(
                df["x_m"], df["y_m"],
                color="gray", linewidth=1.5, alpha=0.5, zorder=2
            )
            
            time_colors = range(len(df))
            cbar_label = "Ajan kulku (Mittauspisteen järjestysnumero)"
            num_stops = 0
            
            if "aika" in df.columns:
                df["aika"] = pd.to_datetime(df["aika"])
                total_time = (df["aika"].max() - df["aika"].min()).total_seconds() / 60.0
                elapsed_min = (df["aika"] - df["aika"].min()).dt.total_seconds() / 60.0
                time_colors = elapsed_min
                cbar_label = "Ajan kulku (minuuttia)"
                
                # Pysähdyspaikkojen tunnistus ja keston laskenta
                if "speed_mps" in df.columns:
                    smoothed_speed = df["speed_mps"].rolling(window=10, min_periods=1).mean()
                    
                    valid_dwells = []
                    current_dwell = None
                    
                    # Tehokkaampi läpikäynti tilakoneella, jossa seurataan pysähdysaikaa ja sijaintia
                    for x, y, aika, speed in zip(df["x_m"], df["y_m"], df["aika"], smoothed_speed):
                        if speed < 0.15:
                            if current_dwell is None:
                                # Uusi pysähdys alkaa
                                current_dwell = {"x_m": x, "y_m": y, "start_time": aika, "end_time": aika}
                            else:
                                # Ollaan pysähdyksissä. Tarkistetaan onko liikuttu liikaa (yli 1.5m).
                                dist = ((x - current_dwell["x_m"])**2 + (y - current_dwell["y_m"])**2)**0.5
                                if dist > 1.5:
                                    # Liikuttu liikaa -> edellinen pysähdys päättyy, uusi alkaa
                                    valid_dwells.append(current_dwell)
                                    current_dwell = {"x_m": x, "y_m": y, "start_time": aika, "end_time": aika}
                                else:
                                    # Pysytään paikallaan -> päivitetään vain päättymisaikaa
                                    current_dwell["end_time"] = aika
                        else:
                            # Ei olla pysähdyksissä. Jos oli käynnissä, se päättyy.
                            if current_dwell is not None:
                                valid_dwells.append(current_dwell)
                                current_dwell = None
                                
                    if current_dwell is not None:
                        valid_dwells.append(current_dwell)
                        
                    if valid_dwells:
                        dwells = pd.DataFrame(valid_dwells)
                        # Lasketaan kesto sekunteina
                        dwells["kesto_s"] = (dwells["end_time"] - dwells["start_time"]).dt.total_seconds()
                        # Suodatetaan pois alle 5 sekunnin mikropysähdykset
                        dwells = dwells[dwells["kesto_s"] >= 5.0]
                        num_stops = len(dwells)
                    else:
                        dwells = pd.DataFrame()
                        num_stops = 0
                
                # Päivitetään otsikko
                if "dist_m" in df.columns:
                    total_dist = df["dist_m"].sum()
                    title += f"\n(Kesto: {total_time:.1f} min, Matka: {total_dist:.0f} m, Pysähdyksiä: {num_stops})"
                    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
            
            # Pysähdyspaikat piirretään reitin päälle
            if num_stops > 0 and not dwells.empty:
                # Muutetaan kontrastia (alpha-arvoa) pysähdyksen pituuden mukaan
                max_kesto = dwells["kesto_s"].max()
                if max_kesto > 0:
                    alphas = 0.3 + 0.7 * (dwells["kesto_s"] / max_kesto)
                else:
                    alphas = pd.Series([0.9] * len(dwells))
                
                # Hotpink RGBA
                rgba_colors = np.zeros((len(dwells), 4))
                rgba_colors[:, 0] = 1.0         # R
                rgba_colors[:, 1] = 105 / 255.0 # G
                rgba_colors[:, 2] = 180 / 255.0 # B
                rgba_colors[:, 3] = alphas      # A

                ax.scatter(dwells["x_m"], dwells["y_m"], c=rgba_colors, edgecolor="white", marker="o", s=100, zorder=3.5, label=f"Pysähdykset ({num_stops} kpl)")
                
                # Kirjoitetaan pysähdysaika markerin viereen
                for _, row in dwells.iterrows():
                    kesto_min = int(row["kesto_s"] // 60)
                    kesto_sek = int(row["kesto_s"] % 60)
                    aika_str = f"{kesto_min}m {kesto_sek}s" if kesto_min > 0 else f"{kesto_sek}s"
                    
                    ax.text(row["x_m"] + 0.4, row["y_m"] + 0.4, aika_str, fontsize=8, color='white', 
                            bbox=dict(facecolor='black', alpha=0.6, edgecolor='none', boxstyle='round,pad=0.2'), zorder=4.5)
            
            # Piirretään pisteet aikavärillä
            sc = ax.scatter(
                df["x_m"], df["y_m"],
                c=time_colors, cmap='winter', s=30, alpha=0.9, zorder=3
            )
            
            # Merkitään alku ja loppu yksiselitteisesti
            if not df.empty:
                # Ensimmäinen piste on reitin alku
                ax.scatter(df["x_m"].iloc[0], df["y_m"].iloc[0], color="lime", marker="*", s=400, edgecolor="black", label="Kauppareitin Alku", zorder=4)
                # Viimeinen piste on reitin loppu
                ax.scatter(df["x_m"].iloc[-1], df["y_m"].iloc[-1], color="red", marker="X", s=200, edgecolor="black", label="Kauppareitin Loppu", zorder=4)
                ax.legend(loc="upper right")
                
                # Väripalkki ajan kululle
                plt.colorbar(sc, ax=ax, label=cbar_label, pad=0.02)

        elif plot_type == "dwell":
            # Pysähdyspaikat: markerin koko dwell_time mukaan
            s_col = "dwell_time" if "dwell_time" in df.columns else "weight"
            if s_col not in df.columns:
                df[s_col] = 10  # Fallback koko
            
            # Normalisoidaan koot
            sizes = df[s_col] / df[s_col].max() * 300 + 20
            ax.scatter(
                df["x_m"], df["y_m"],
                s=sizes, alpha=alpha, c=df[s_col], cmap="inferno",
                edgecolors="black", linewidths=0.5, zorder=2
            )
            plt.colorbar(ax.collections[0], ax=ax, label="Viipymä")

        # Piirretään osastot jos pyydetty
        if show_zones:
            zones_df = _load_zones()
            if zones_df is not None:
                _draw_zones(ax, zones_df)

        # Tyylittelyt
        ax.set_xlim(0, X_MAX_M)
        ax.set_ylim(Y_MAX_M, 0)
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

        return f"Pohjapiirrosvisualisointi luotu: {filepath}"

    except Exception as e:
        return f"Virhe pohjapiirrosvisualisoinnissa: {e}"


ALL_FLOORPLAN_TOOLS = [plot_on_floorplan]

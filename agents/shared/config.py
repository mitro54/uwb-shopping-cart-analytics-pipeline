"""
ByteBuddies UWB Dashboard analytiikka sovelluksen konfiguraatio.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_ROOT = PROJECT_ROOT / "agents"
DATA_ROOT = PROJECT_ROOT / "data"


@dataclass(frozen=False)
class AppConfig:
    """Sovelluksen laajuiset asetusarvot ja riippuvuudet."""
    duckdb_path: Path
    ollama_base_url: str
    
    # --- Pilvipalvelun varajärjestelmä (Fallback) ---
    gemini_api_key: str | None
    
    # --- Mallit ---
    orchestrator_model: str
    analytics_model: str
    plotter_model: str
    schema_model: str
    embedding_model: str
    max_iterations: int
    verbose: bool

    # --- Lokalisointi & Identiteetti ---
    store_name: str
    timezone: str
    locale: str

    # --- Kaupan Layout (metreinä) ---
    store_width_m: float
    store_height_m: float
    floorplan_image_path: str

    # --- Operatiiviset asetukset ---
    shop_open_hour: int
    shop_close_hour: int

    # --- Geofencing (metreinä) ---
    checkout_x_min: float
    checkout_x_max: float
    checkout_y_min: float
    checkout_y_max: float

    # --- Suodatetut alueet (JSON string) ---
    excluded_zones_json: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Luo AppConfig-instanssin ympäristömuuttujista.
        """
        return cls(
            duckdb_path=Path(
                os.getenv("DUCKDB_PATH", str(DATA_ROOT / "warehouse" / "dev.duckdb"))
            ),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            orchestrator_model=os.getenv("ORCHESTRATOR_MODEL", "qwen2.5:3b"),
            analytics_model=os.getenv("ANALYTICS_MODEL", "qwen3.5:35b"),
            plotter_model=os.getenv("PLOTTER_MODEL", "qwen3.5:9b"),
            schema_model=os.getenv("SCHEMA_MODEL", "qwen2.5:3b"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest"),
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "25")),
            verbose=os.getenv("AGENT_VERBOSE", "true").lower() == "true",
            
            store_name=os.getenv("STORE_NAME", "ByteBuddies Helsinki"),
            timezone=os.getenv("APP_TIMEZONE", "Europe/Helsinki"),
            locale=os.getenv("APP_LOCALE", "fi_FI"),
            
            store_width_m=float(os.getenv("STORE_WIDTH_M", "104.06")),
            store_height_m=float(os.getenv("STORE_HEIGHT_M", "52.20")),
            floorplan_image_path=os.getenv("FLOORPLAN_IMAGE_PATH", "image/kauppa2.png"),
            
            shop_open_hour=int(os.getenv("SHOP_OPEN_HOUR", "7")),
            shop_close_hour=int(os.getenv("SHOP_CLOSE_HOUR", "22")),
            
            checkout_x_min=float(os.getenv("CHECKOUT_X_MIN", "0.0")),
            checkout_x_max=float(os.getenv("CHECKOUT_X_MAX", "20.0")),
            checkout_y_min=float(os.getenv("CHECKOUT_Y_MIN", "40.0")),
            checkout_y_max=float(os.getenv("CHECKOUT_Y_MAX", "52.2")),
            
            excluded_zones_json=os.getenv("EXCLUDED_ZONES_JSON", "[]"),
        )


CONFIG = AppConfig.from_env()

# Varmistetaan, että tietokantatiedosto on olemassa.
if not CONFIG.duckdb_path.exists():
    CONFIG.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    import duckdb
    _conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=False)
    _conn.close()

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_ROOT = PROJECT_ROOT / "agents"
DATA_ROOT = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class AppConfig:
    duckdb_path: Path
    ollama_base_url: str
    orchestrator_model: str
    analytics_model: str
    plotter_model: str
    schema_model: str
    embedding_model: str
    max_iterations: int
    verbose: bool

    @classmethod
    def from_env(cls) -> "AppConfig":
        default_model = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
        return cls(
            duckdb_path=Path(
                os.getenv("DUCKDB_PATH", str(DATA_ROOT / "warehouse" / "warehouse.duckdb"))
            ),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            orchestrator_model=os.getenv("ORCHESTRATOR_MODEL", "qwen2.5:3b"),
            analytics_model=os.getenv("ANALYTICS_MODEL", "qwen3.5:35b"),
            plotter_model=os.getenv("PLOTTER_MODEL", "qwen3.5:9b"),
            schema_model=os.getenv("SCHEMA_MODEL", "qwen2.5:3b"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest"),
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "25")),
            verbose=os.getenv("AGENT_VERBOSE", "true").lower() == "true",
        )


CONFIG = AppConfig.from_env()

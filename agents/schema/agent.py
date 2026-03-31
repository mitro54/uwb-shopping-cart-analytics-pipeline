from __future__ import annotations

from pathlib import Path
import yaml

from agents.shared.config import AGENTS_ROOT
from agents.shared.schema_registry import SchemaRegistry

AGENT_ROOT = AGENTS_ROOT / "schema"
IDENTITY_PATH = AGENT_ROOT / "identity.yml"
PROMPT_PATH = AGENT_ROOT / "prompt.md"


class SchemaAgent:
    def __init__(self) -> None:
        self.identity = yaml.safe_load(IDENTITY_PATH.read_text(encoding="utf-8"))
        self.prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.registry = SchemaRegistry()

    def refresh(self) -> dict:
        return self.registry.refresh()

    def summary(self, refresh: bool = False) -> str:
        return self.registry.as_text(refresh=refresh)

    def current_hash(self) -> str:
        return self.registry.current_hash()

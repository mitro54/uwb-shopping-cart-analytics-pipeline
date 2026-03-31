from __future__ import annotations

import yaml
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from agents.shared.config import AGENTS_ROOT, CONFIG
from agents.shared.llm import build_chat_ollama
from agents.schema.agent import SchemaAgent
from agents.analytics.agent import AnalyticsAgent

AGENT_ROOT = AGENTS_ROOT / "orchestrator"
IDENTITY_PATH = AGENT_ROOT / "identity.yml"
PROMPT_PATH = AGENT_ROOT / "prompt.md"

class OrchestratorAgent:
    def __init__(self) -> None:
        self.identity = yaml.safe_load(IDENTITY_PATH.read_text(encoding="utf-8"))
        self.base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.llm = build_chat_ollama(model_name=CONFIG.orchestrator_model, temperature=0.1)
        
        # Sub-agents
        self.schema_agent = SchemaAgent()
        self.analytics_agent = AnalyticsAgent()

    def _system_prompt(self, context_info: str = "") -> str:
        return self.base_prompt.format(
            agent_name=self.identity["name"],
            role=self.identity["role"],
            goals=", ".join(self.identity["goals"]),
            constraints=", ".join(self.identity["constraints"]),
            context_info=context_info,
        )

    def process_request(self, question: str, thread_id: str = "default", status_callback=None) -> tuple[str, int]:
        """Käsittelee käyttäjän pyynnön koordinoidusti."""
        if status_callback:
            status_callback("Analytiikka-agentti aloittaa työn...")
        
        answer, interaction_id = self.analytics_agent.ask(question, thread_id=thread_id)
        
        return answer, interaction_id

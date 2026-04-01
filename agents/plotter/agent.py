"""
ByteBuddies UWB Dashboard analytiikka sovelluksen plotter agentti.

Plotter agentti on vastuussa visualisointien luomisesta.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations

import yaml
from pathlib import Path

from langgraph.prebuilt import create_react_agent
from agents.shared.config import AGENTS_ROOT, CONFIG
from agents.shared.llm import build_chat_model
from agents.shared.tools.plot_tools import ALL_PLOT_TOOLS

AGENT_ROOT = AGENTS_ROOT / "plotter"
IDENTITY_PATH = AGENT_ROOT / "identity.yml"
PROMPT_PATH = AGENT_ROOT / "prompt.md"

class PlotterAgent:
    def __init__(self) -> None:
        self.identity = yaml.safe_load(IDENTITY_PATH.read_text(encoding="utf-8"))
        self.base_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def _system_prompt(self) -> str:
        """Luo plotter-agentin järjestelmäohjeen visualisointia varten."""
        return self.base_prompt.format(
            agent_name=self.identity["name"],
            role=self.identity["role"],
            goals=", ".join(self.identity["goals"]),
            constraints=", ".join(self.identity["constraints"]),
        )

    def generate_plot(self, instruction: str) -> str:
        """Luo visualisoinnin annetun ohjeen ja datan perusteella. Tämä agentti on 'stateless'."""
        try:
            llm = build_chat_model(model_name=CONFIG.plotter_model, temperature=0)
            
            # Plotter-agentilla on vain visualisointityökalut käytössä
            graph = create_react_agent(
                model=llm,
                tools=ALL_PLOT_TOOLS,
                prompt=self._system_prompt(),
            )
            
            result = graph.invoke(
                {"messages": [{"role": "user", "content": instruction}]},
            )
            
            answer = result["messages"][-1].content
            if "data/processed/plots" not in answer and len(result["messages"]) > 1:
                # Jos viimeinen viesti ei sisällä polkua, yritetään etsiä sitä aiemmista työkalu-vastauksista
                for msg in reversed(result["messages"]):
                    if hasattr(msg, "content") and "data/processed/plots" in str(msg.content):
                        return f"Visualisointi luotu: {msg.content}"
            
            return answer
        except Exception as e:
            return f"Virhe visualisoinnissa: {str(e)}"

from __future__ import annotations

from pathlib import Path
import yaml

from langgraph.prebuilt import create_react_agent

from agents.shared.config import AGENTS_ROOT, CONFIG
from agents.shared.llm import build_chat_ollama
from agents.shared.memory.checkpointing import build_checkpointer
from agents.shared.memory.feedback_store import FeedbackStore
from agents.shared.schema_registry import SchemaRegistry
from agents.shared.tools.duckdb_tools import ALL_TOOLS as DB_TOOLS
from agents.shared.tools.delegation_tools import generate_visualization

ALL_AGENT_TOOLS = DB_TOOLS + [generate_visualization]

AGENT_ROOT = AGENTS_ROOT / "analytics"
IDENTITY_PATH = AGENT_ROOT / "identity.yml"
PROMPT_PATH = AGENT_ROOT / "prompt.md"
CHECKPOINT_PATH = AGENT_ROOT / "memory" / "checkpoints.sqlite"
FEEDBACK_PATH = AGENT_ROOT / "memory" / "feedback.sqlite"


class AnalyticsAgent:
    def __init__(self) -> None:
        self.identity = yaml.safe_load(IDENTITY_PATH.read_text(encoding="utf-8"))
        self.base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.schema_registry = SchemaRegistry()
        self.feedback_store = FeedbackStore(FEEDBACK_PATH)

    def _system_prompt(self, question: str) -> str:
        schema_text = self.schema_registry.as_text()
        schema_hash = self.schema_registry.current_hash()
        few_shot = self.feedback_store.build_few_shot_block(question, schema_hash=schema_hash)
        lessons_learned = self.feedback_store.build_lessons_learned_block(question)

        return self.base_prompt.format(
            agent_name=self.identity["name"],
            role=self.identity["role"],
            goals=", ".join(self.identity["goals"]),
            constraints=", ".join(self.identity["constraints"]),
            schema_text=schema_text,
            few_shot_block=few_shot or "No prior approved examples available.",
            lessons_learned_block=lessons_learned or "No prior warnings.",
        )

    def build(self, question: str):
        """Rakentaa LangGraph-pohjaisen agentin, jolla on pääsy analyysityökaluihin ja muistiin."""
        llm = build_chat_ollama(model_name=CONFIG.analytics_model, temperature=0)
        checkpointer = build_checkpointer(CHECKPOINT_PATH)
        return create_react_agent(
            model=llm,
            tools=ALL_AGENT_TOOLS,
            prompt=self._system_prompt(question),
            checkpointer=checkpointer,
        )

    def ask(self, question: str, thread_id: str = "default") -> tuple[str, int]:
        """Suorittaa analyysitehtävän: kysyy LLM:ltä, ajaa tarvittavat työkalut ja tallentaa tuloksen muistiin."""
        graph = self.build(question)
        result = graph.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": "analytics",
                },
                "recursion_limit": CONFIG.max_iterations,
            },
        )
        answer = result["messages"][-1].content
        interaction_id = self.feedback_store.save_interaction(
            thread_id=thread_id,
            question=question,
            answer=answer,
            sql_used=self._extract_last_sql(result["messages"]),
            schema_hash=self.schema_registry.current_hash(),
        )
        return answer, interaction_id

    def save_feedback(self, interaction_id: int, rating: str, comment: str = "") -> None:
        normalized = {"good": "good", "bad": "bad", "hyvä": "good", "huono": "bad"}.get(
            rating.strip().lower(), rating.strip().lower()
        )
        self.feedback_store.save_feedback(interaction_id, normalized, comment)

    @staticmethod
    def _extract_last_sql(messages: list) -> str | None:
        for msg in reversed(messages):
            content = getattr(msg, "content", "")
            if isinstance(content, str) and "SELECT" in content.upper():
                return content[:1000]
        return None

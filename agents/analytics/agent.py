"""
ByteBuddies UWB Dashboard analytiikka sovelluksen analytiikka agentti.

Analyysi agentti on vastuussa datan analysoinnista.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations

from pathlib import Path
import yaml

from langgraph.prebuilt import create_react_agent

from agents.shared.config import AGENTS_ROOT, CONFIG
from agents.shared.llm import build_chat_model
from agents.shared.memory.checkpointing import build_checkpointer
from agents.shared.memory.feedback_store import FeedbackStore
from agents.shared.schema_registry import SchemaRegistry
from agents.shared.tools.duckdb_tools import ALL_TOOLS as DB_TOOLS
from agents.shared.tools.plot_tools import ALL_PLOT_TOOLS
from agents.shared.tools.floorplan_tools import ALL_FLOORPLAN_TOOLS
from agents.shared.tools.delegation_tools import generate_visualization

ALL_AGENT_TOOLS = DB_TOOLS + [generate_visualization]

AGENT_ROOT = AGENTS_ROOT / "analytics"
IDENTITY_PATH = AGENT_ROOT / "identity.yml"
PROMPT_PATH = AGENT_ROOT / "prompt.md"
CHECKPOINT_PATH = AGENT_ROOT / "memory" / "checkpoints.sqlite"
FEEDBACK_PATH = AGENT_ROOT / "memory" / "feedback.sqlite"

# Suomenkieliset nimet työkaluille statuskäyttöliittymää varten
TOOL_DISPLAY_NAMES = {
    "list_tables": ("🗄️", "Listataan taulut"),
    "describe_table": ("📋", "Tutkitaan taulun rakennetta"),
    "sample_rows": ("🔍", "Haetaan esimerkkidataa"),
    "get_row_count": ("🔢", "Lasketaan rivimäärä"),
    "get_column_stats": ("📊", "Analysoidaan sarakkeen tilastot"),
    "run_query": ("⚡", "Suoritetaan SQL-kysely"),
    "generate_visualization": ("🎨", "Luodaan visualisointi"),
    "plot_chart": ("📈", "Piirretään kaavio"),
    "plot_distribution": ("🎻", "Analysoidaan jakaumaa"),
    "plot_grouped_bar": ("📊", "Tehdään ryhmitelty pylväskaavio"),
    "plot_interactive": ("📊", "Luodaan interaktiivinen kuvaaja"),
    "plot_on_floorplan": ("🗺️", "Piirretään pohjapiirrokselle"),
    "refresh_schema": ("🌀", "Päivitetään tietokannan muistikuvaa"),
}


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
        llm = build_chat_model(model_name=CONFIG.analytics_model, temperature=0)
        checkpointer = build_checkpointer(CHECKPOINT_PATH)
        return create_react_agent(
            model=llm,
            tools=ALL_AGENT_TOOLS,
            prompt=self._system_prompt(question),
            checkpointer=checkpointer,
        )

    def ask(
        self,
        question: str,
        thread_id: str = "default",
        status_callback=None,
    ) -> tuple[str, int]:
        """Suorittaa analyysitehtävän streamaten: raportoi reaaliajassa mitä agentti tekee."""
        graph = self.build(question)
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "analytics",
            },
            "recursion_limit": CONFIG.max_iterations,
        }

        if status_callback:
            status_callback("thinking", "analytics", "Analytiikka-agentti miettii vastausta...")

        try:
            all_messages = self._stream_graph(graph, question, config, status_callback)
        except Exception as e:
            if "INVALID_CHAT_HISTORY" in str(e) or "tool_calls" in str(e):
                # Checkpoint korruptoitunut → yritetään uudella threadilla
                if status_callback:
                    status_callback(
                        "thinking", "analytics",
                        "⚠️ Edellinen keskustelu oli keskeneräinen — aloitetaan puhtaalta pöydältä..."
                    )
                config["configurable"]["thread_id"] = f"{thread_id}_retry_{id(question)}"
                graph = self.build(question)
                all_messages = self._stream_graph(graph, question, config, status_callback)
            else:
                raise

        if not all_messages:
            answer = "Agentti ei tuottanut vastausta."
        else:
            final_content = all_messages[-1].content
            if isinstance(final_content, list):
                # Gemini saattaa palauttaa sisällön listana blokkeja
                text_blocks = [
                    b.get("text", "") if isinstance(b, dict) else str(b) 
                    for b in final_content
                ]
                answer = "".join(text_blocks)
            else:
                answer = str(final_content)

        interaction_id = self.feedback_store.save_interaction(
            thread_id=thread_id,
            question=question,
            answer=answer,
            sql_used=self._extract_last_sql(all_messages),
            schema_hash=self.schema_registry.current_hash(),
        )
        return answer, interaction_id

    def _stream_graph(self, graph, question: str, config: dict, status_callback=None) -> list:
        """Streamaa LangGraph-agentin ja kerää viestit, raportoiden statuksen reaaliajassa."""
        all_messages = []
        iteration = 0

        for chunk in graph.stream(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
            stream_mode="updates",
        ):
            for node_name, node_output in chunk.items():
                messages = node_output.get("messages", [])
                all_messages.extend(messages)

                if not status_callback:
                    continue

                for msg in messages:
                    # AI-viesti jossa on tool_calls → työkalu kutsutaan
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_name = tc.get("name", "unknown")
                            icon, label = TOOL_DISPLAY_NAMES.get(
                                tool_name, ("🔧", f"Työkalu: {tool_name}")
                            )
                            status_callback("tool_call", "analytics", f"{icon} {label}")

                    # Työkalu-viesti (tulos palautui)
                    elif hasattr(msg, "type") and msg.type == "tool":
                        tool_name = getattr(msg, "name", "")
                        icon, label = TOOL_DISPLAY_NAMES.get(
                            tool_name, ("✅", f"{tool_name}")
                        )
                        status_callback("tool_result", "analytics", f"✅ {label} — valmis")

                        # Jos kutsuttiin generate_visualization → visualisointi-agentti
                        if tool_name == "generate_visualization":
                            status_callback(
                                "agent_delegated", "plotter",
                                "🎨 Visualisointiagentti luo kuvaajaa..."
                            )

                    # AI:n lopullinen vastaus (ei tool_calls)
                    elif hasattr(msg, "tool_calls") and not msg.tool_calls:
                        iteration += 1
                        if iteration > 1:
                            status_callback(
                                "thinking", "analytics",
                                f"Analytiikka-agentti jatkaa pohdintaa (kierros {iteration})..."
                            )

        return all_messages

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

from __future__ import annotations

import argparse
import json

from agents.analytics.agent import AnalyticsAgent
from agents.orchestrator.agent import OrchestratorAgent
from agents.schema.agent import SchemaAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="ByteBuddies local multi-agent CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ... p_schema same ...
    p_schema = sub.add_parser("schema")
    p_schema.add_argument("--refresh", action="store_true")

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("question", type=str)
    p_ask.add_argument("--thread", default="default")

    p_chat = sub.add_parser("chat")
    p_chat.add_argument("--thread", default="default")

    p_memory = sub.add_parser("memory")
    p_memory.add_argument("action", choices=["stats"])

    args = parser.parse_args()

    if args.cmd == "schema":
        agent = SchemaAgent()
        if args.refresh:
            agent.refresh()
        print(agent.summary(refresh=False))

    elif args.cmd == "ask":
        orch = OrchestratorAgent()
        answer, interaction_id = orch.process_request(args.question, thread_id=args.thread)
        print(f"\n{answer}\n")
        feedback = input("Feedback [g=good / b=bad / Enter=skip]: ").strip().lower()
        if feedback in {"g", "good", "hyvä"}:
            orch.analytics_agent.save_feedback(interaction_id, "good")
        elif feedback in {"b", "bad", "huono"}:
            comment = input("Optional comment: ").strip()
            orch.analytics_agent.save_feedback(interaction_id, "bad", comment)

    elif args.cmd == "chat":
        orch = OrchestratorAgent()
        while True:
            question = input("You: ").strip()
            if question.lower() in {"quit", "exit", "q"}:
                break
            if not question:
                continue
            answer, interaction_id = orch.process_request(question, thread_id=args.thread)
            print(f"\nAgent:\n{answer}\n")
            feedback = input("Feedback [g=good / b=bad / Enter=skip]: ").strip().lower()
            if feedback in {"g", "good", "hyvä"}:
                orch.analytics_agent.save_feedback(interaction_id, "good")
            elif feedback in {"b", "bad", "huono"}:
                comment = input("Optional comment: ").strip()
                orch.analytics_agent.save_feedback(interaction_id, "bad", comment)

    elif args.cmd == "memory":
        agent = AnalyticsAgent()
        print(json.dumps(agent.feedback_store.stats(), indent=2))


if __name__ == "__main__":
    main()

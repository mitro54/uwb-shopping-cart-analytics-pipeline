"""
ByteBuddies CLI - Moniagenttijärjestelmän.

Tämä moduuli tarjoaa komentorivikäyttöliittymän, jonka kautta hallinnoidaan
ostoskärryanalytiikan agentteja. Sen avulla voidaan tarkastella tietokannan
rakennetta, keskustella orkestraattorin kanssa ja hallinnoida agenttien muistia.

Tarkemmat käyttöohjeet löytyvät tiedostosta: docs/agentti_kayttoohje.md

Kirjoittaja: Toni Kiuru
"""


from __future__ import annotations

import argparse
import json

from agents.analytics.agent import AnalyticsAgent
from agents.orchestrator.agent import OrchestratorAgent
from agents.schema.agent import SchemaAgent


def main() -> None:
    """
    Komentorivikäyttöliittymän pääfunktio.
    
    Parsii käyttäjän antamat argumentit ja ohjaa pyynnöt oikealle agentille 
    (Orchestrator, Schema tai Analytics) valitun komennon perusteella.
    """
    parser = argparse.ArgumentParser(description="ByteBuddies local multi-agent CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Schema-komento: tietokannan rakenteen hallinta
    p_schema = sub.add_parser("schema")
    p_schema.add_argument("--refresh", action="store_true", help="Päivitä tietokannan rakenne välimuistiin")

    # Ask-komento: kertaluonteinen kysymys
    p_ask = sub.add_parser("ask")
    p_ask.add_argument("question", type=str, help="Kysymys agentille")
    p_ask.add_argument("--thread", default="default", help="Keskustelusäikeen tunniste")

    # Chat-komento: jatkuva keskustelu orkestraattorin kanssa
    p_chat = sub.add_parser("chat")
    p_chat.add_argument("--thread", default="default", help="Keskustelusäikeen tunniste")

    # Memory-komento: agenttien muistin tilastot
    p_memory = sub.add_parser("memory")
    p_memory.add_argument("action", choices=["stats"], help="Muistitoiminto (esim. tilastot)")

    args = parser.parse_args()

    if args.cmd == "schema":
        # SchemaAgent vastaa tietokannan rakenteen tuntemisesta
        agent = SchemaAgent()
        if args.refresh:
            agent.refresh()
        print(agent.summary(refresh=False))

    elif args.cmd == "ask":
        # Orkestraattori koordinoi vastauksen muodostamisen
        orch = OrchestratorAgent()
        answer, interaction_id = orch.process_request(args.question, thread_id=args.thread)
        print(f"\n{answer}\n")
        
        # Palautteen kerääminen on tärkeää agentin oppimisen kannalta
        feedback = input("Feedback [g=good / b=bad / Enter=skip]: ").strip().lower()
        if feedback in {"g", "good", "hyvä"}:
            orch.analytics_agent.save_feedback(interaction_id, "good")
        elif feedback in {"b", "bad", "huono"}:
            comment = input("Optional comment: ").strip()
            orch.analytics_agent.save_feedback(interaction_id, "bad", comment)

    elif args.cmd == "chat":
        # Jatkuva interaktiivinen chat-tila
        orch = OrchestratorAgent()
        print("\nByte-Orchestrator käynnissä. Kirjoita 'quit' lopettaaksesi.\n")
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
        # Muistin ja palautteiden tilastojen tarkastelu
        agent = AnalyticsAgent()
        print(json.dumps(agent.feedback_store.stats(), indent=2))


if __name__ == "__main__":
    main()

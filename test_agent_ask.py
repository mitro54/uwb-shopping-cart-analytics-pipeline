import os
import sys
from pathlib import Path

sys.path.append(str(Path.cwd()))

try:
    from agents.analytics.agent import AnalyticsAgent
    from agents.shared.config import CONFIG
    
    print(f"Testing AnalyticsAgent...")
    print(f"Orchestrator Model: {CONFIG.orchestrator_model}")
    print(f"Analytics Model: {CONFIG.analytics_model}")
    print(f"Embedding Model: {CONFIG.embedding_model}")

    agent = AnalyticsAgent()
    
    question = "How many rows are in the 'raw_uwb_data' table?"
    print(f"Asking agent: '{question}'...")
    
    # Kokeillaan kutsua, mutta lisätään vähän debug-tulostusta jos mahdollista
    # Koska emme voi muokata agentin koodia helposti lennosta, toivotaan parasta
    
    answer, interaction_id = agent.ask(question, thread_id="test_thread")
    
    print(f"\nSUCCESS!")
    print(f"Interaction ID: {interaction_id}")
    print(f"Answer: {answer}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

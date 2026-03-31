import os
import sys
from pathlib import Path

sys.path.append(str(Path.cwd()))

try:
    from agents.orchestrator.agent import OrchestratorAgent
    from agents.shared.config import CONFIG
    
    print(f"Testing OrchestratorAgent...")
    orch = OrchestratorAgent()
    
    question = "How many rows are in the 'silver.weather_hourly' table?"
    print(f"Asking orchestrator: '{question}'...")
    
    answer, interaction_id = orch.process_request(question, thread_id="test_thread_orch")
    
    print(f"\nSUCCESS!")
    print(f"Interaction ID: {interaction_id}")
    print(f"Answer: {answer}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

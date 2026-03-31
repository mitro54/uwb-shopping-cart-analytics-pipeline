import os
import sys
from pathlib import Path

sys.path.append(str(Path.cwd()))

try:
    from agents.shared.memory.feedback_store import FeedbackStore
    from agents.shared.config import DATA_ROOT
    
    db_path = Path("agents/analytics/memory/feedback.sqlite")
    print(f"Testing FeedbackStore with DB: {db_path}")
    
    store = FeedbackStore(db_path)
    
    question = "Miten paljon ostoskärryt liikkuvat?"
    print(f"Finding similar good examples for: '{question}'...")
    
    examples = store.similar_good_examples(question)
    print(f"Found {len(examples)} examples.")
    
    for i, ex in enumerate(examples):
        print(f"Ex {i}: {ex.question[:50]}... (Score: {ex.similarity:.4f})")

    print("\nFinding similar bad examples...")
    bad_examples = store.similar_bad_examples(question)
    print(f"Found {len(bad_examples)} bad examples.")

    print("\nSuccess!")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

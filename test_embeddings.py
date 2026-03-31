import os
import sys
from pathlib import Path

# Lisätään projektin juuri PYTHONPATH-ympäristömuuttujaan
sys.path.append(str(Path.cwd()))

try:
    from langchain_ollama import OllamaEmbeddings
    from agents.shared.config import CONFIG
    import numpy as np

    print(f"Testing embeddings with model: {CONFIG.embedding_model}")
    print(f"Base URL: {CONFIG.ollama_base_url}")

    embeddings = OllamaEmbeddings(
        base_url=CONFIG.ollama_base_url,
        model=CONFIG.embedding_model,
    )

    test_text = "Mitä kuuluu?"
    print(f"Embedding text: '{test_text}'...")
    
    # Kokeillaan lyhyellä aikakatkaisulla jos mahdollista, mutta langchain_ollama ei suoraan tue sitä tässä
    vector = embeddings.embed_query(test_text)
    
    print(f"Success! Vector length: {len(vector)}")
    print(f"First 5 values: {vector[:5]}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

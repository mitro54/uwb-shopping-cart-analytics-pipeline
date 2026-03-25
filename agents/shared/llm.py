from __future__ import annotations

from langchain_ollama import ChatOllama
from agents.shared.config import CONFIG


def build_chat_ollama(model_name: str | None = None, temperature: float = 0.0) -> ChatOllama:
    model = model_name or CONFIG.orchestrator_model
    return ChatOllama(
        base_url=CONFIG.ollama_base_url,
        model=model,
        temperature=temperature,
    )

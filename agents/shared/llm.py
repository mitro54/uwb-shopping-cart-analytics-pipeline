"""
ByteBuddies UWB Dashboard analytiikka sovelluksen LLM-mallit.

Kirjoittaja: Toni Kiuru
""" 

from __future__ import annotations

from langchain_ollama import ChatOllama
from agents.shared.config import CONFIG


def build_chat_ollama(model_name: str | None = None, temperature: float = 0.0) -> ChatOllama:
    """
    Rakentaa ChatOllama-instanssin.
    
    Args:
        model_name: Mallin nimi
        temperature: Satunnaisuus (0.0 = deterministinen)
    
    Returns:
        ChatOllama-instanssi
    """
    model = model_name or CONFIG.orchestrator_model
    return ChatOllama(
        base_url=CONFIG.ollama_base_url,
        model=model,
        temperature=temperature,
    )

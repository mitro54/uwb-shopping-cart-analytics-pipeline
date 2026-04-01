"""
ByteBuddies UWB Dashboard analytiikka sovelluksen LLM-mallit.

Kirjoittaja: Toni Kiuru
""" 

from __future__ import annotations

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.shared.config import CONFIG


def build_chat_model(model_name: str | None = None, temperature: float = 0.0) -> ChatOllama | ChatGoogleGenerativeAI:
    """
    Rakentaa ChatModel-instanssin (Ollama tai pilvipohjainen Gemini varajärjestelmänä).
    
    Tämä funktio tarkkailee annettua `model_name`-parametria.
    Jos Ollama ei ole tavoitettavissa sovelluksen käynnistyessä, käyttöliittymä siirtää 
    agenttien `model_name`:n sisään 'gemini'-sanalla alkavan mallin nimen. Tällöin tämä 
    alkuperäisesti vain Ollamaa varten tehty funktio siirtyy automaattisesti käyttämään 
    Googlen pilvirajapintaa, saumattomana varajärjestelmänä.
    
    Args:
        model_name: Mallin nimi (jos 'gemini', käytetään pilveä)
        temperature: Satunnaisuus (0.0 = deterministinen)
    
    Returns:
        ChatOllama-instanssi tai varajärjestelmä Google Generative AI -instanssi
    """
    model = model_name or CONFIG.orchestrator_model
    
    if "gemini" in model.lower():
        api_key = CONFIG.gemini_api_key or "ODOTTAA_AVAINTA_KAYTTOLIITTYMASTA"
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )

    return ChatOllama(
        base_url=CONFIG.ollama_base_url,
        model=model,
        temperature=temperature,
    )

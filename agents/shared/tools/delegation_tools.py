"""
ByteBuddies UWB Dashboard analytiikka sovelluksen delegointityökalu.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations
from langchain_core.tools import tool
from agents.plotter.agent import PlotterAgent

@tool
def generate_visualization(instruction: str) -> str:
    """
    Kutsuu visualisointi-agenttia luomaan kuvaajan tai heatmapin.
    Anna ohjeeksi SQL-kysely ja haluttu visualisointityyppi.
    Esimerkki: 'Luo heatmap taulusta silver.abc sarakkeilla x ja y.'
    """
    plotter = PlotterAgent()
    return plotter.generate_plot(instruction)

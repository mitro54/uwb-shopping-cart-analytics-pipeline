"""
ByteBuddies UWB Dashboard analytiikka sovelluksen muistin checkpointing.

Tämä moduuli tarjoaa rajapinnan LLM-mallien antaman palautteen tallentamiseen ja hakemiseen.

Kirjoittaja: Toni Kiuru
"""

import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver


def build_checkpointer(db_path: Path) -> SqliteSaver:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)

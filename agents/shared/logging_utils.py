"""
ByteBuddies UWB Dashboard analytiikka sovelluksen lokitus.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Hakee loggerin nimellä.
    
    Args:
        name: Loggerin nimi
    
    Returns:
        Logger
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

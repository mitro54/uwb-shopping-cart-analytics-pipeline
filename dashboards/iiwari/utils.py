"""Jaetut apufunktiot iiwari-dashboardeille."""

import json
from agents.shared.config import CONFIG


def excluded_zones_sql(x_col: str = "x", y_col: str = "y", prefix: str = "AND NOT") -> str:
    """Rakentaa SQL-ehdon EXCLUDED_ZONES_JSON:sta.

    Koordinaatit .env:ssä metreinä -> muunnetaan cm:ksi (* 100).
    Palauttaa tyhjän merkkijonon jos zoneja ei ole määritelty.
    """
    try:
        zones = json.loads(CONFIG.excluded_zones_json)
    except (json.JSONDecodeError, TypeError):
        return ""

    parts = []
    for z in zones:
        x_min = int(float(z["x_min"]) * 100)
        x_max = int(float(z["x_max"]) * 100)
        y_min = int(float(z["y_min"]) * 100)
        y_max = int(float(z["y_max"]) * 100)
        parts.append(
            f"{prefix} ({x_col} >= {x_min} AND {x_col} <= {x_max}"
            f" AND {y_col} >= {y_min} AND {y_col} <= {y_max})"
        )

    return "\n".join(parts)

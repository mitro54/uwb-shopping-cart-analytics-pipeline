from __future__ import annotations

import json
import hashlib
from pathlib import Path
import duckdb

from agents.shared.config import CONFIG, AGENTS_ROOT
from agents.shared.logging_utils import get_logger

logger = get_logger(__name__)

SCHEMA_CACHE_PATH = AGENTS_ROOT / "schema" / "memory" / "schema_cache.json"


class SchemaRegistry:
    def __init__(self, duckdb_path: Path | None = None, cache_path: Path | None = None):
        self.duckdb_path = duckdb_path or CONFIG.duckdb_path
        self.cache_path = cache_path or SCHEMA_CACHE_PATH
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.duckdb_path), read_only=True)

    def discover(self) -> dict:
        conn = self._connect()
        try:
            tables = conn.execute("""
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name
            """).fetchall()

            schema_map: dict[str, dict] = {}
            for schema_name, table_name, table_type in tables:
                full_name = f"{schema_name}.{table_name}"
                columns = conn.execute(f"DESCRIBE {full_name}").fetchall()
                row_count = conn.execute(f"SELECT COUNT(*) FROM {full_name}").fetchone()[0]
                sample_rows = conn.execute(f"SELECT * FROM {full_name} LIMIT 2").fetchdf().to_dict(orient="records")
                schema_map[full_name] = {
                    "table_type": table_type,
                    "row_count": row_count,
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2],
                            "default": col[4] if len(col) > 4 else None,
                        }
                        for col in columns
                    ],
                    "sample_rows": sample_rows,
                }
            return schema_map
        finally:
            conn.close()

    def refresh(self) -> dict:
        schema = self.discover()
        payload = {
            "schema_hash": self._hash_schema(schema),
            "schema": schema,
        }
        self.cache_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        logger.info("Schema cache refreshed at %s", self.cache_path)
        return payload

    def load(self, refresh: bool = False) -> dict:
        if refresh or not self.cache_path.exists():
            return self.refresh()
        return json.loads(self.cache_path.read_text(encoding="utf-8"))

    def as_text(self, refresh: bool = False) -> str:
        payload = self.load(refresh=refresh)
        lines: list[str] = []
        for table_name, info in payload["schema"].items():
            col_text = ", ".join(f"{c['name']}({c['type']})" for c in info["columns"])
            lines.append(f"{table_name} [{info['table_type']}, {info['row_count']} rows]")
            lines.append(f"  columns: {col_text}")
        return "\n".join(lines)

    def current_hash(self, refresh: bool = False) -> str:
        payload = self.load(refresh=refresh)
        return payload["schema_hash"]

    @staticmethod
    def _hash_schema(schema: dict) -> str:
        raw = json.dumps(schema, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

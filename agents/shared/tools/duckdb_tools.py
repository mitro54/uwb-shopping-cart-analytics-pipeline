from __future__ import annotations

import re
import duckdb

from langchain_core.tools import tool
from agents.shared.config import CONFIG

WRITE_PATTERN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|COPY)\b", re.IGNORECASE)


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(CONFIG.duckdb_path), read_only=True)


@tool
def list_tables() -> str:
    """List available user tables and views from DuckDB."""
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
        """).fetchall()
        if not rows:
            return "No user tables or views found."
        return "\n".join(f"{s}.{t} [{tt}]" for s, t, tt in rows)
    finally:
        conn.close()


@tool
def describe_table(table_name: str) -> str:
    """Describe columns and types for a given table or view."""
    conn = _connect()
    try:
        rows = conn.execute(f"DESCRIBE {table_name}").fetchall()
        return "\n".join(f"{r[0]}: {r[1]}" for r in rows)
    except Exception as exc:
        return f"Error describing table {table_name}: {exc}"
    finally:
        conn.close()


@tool
def sample_rows(table_name: str, n: int = 5) -> str:
    """Return up to n sample rows from a table or view."""
    conn = _connect()
    try:
        df = conn.execute(f"SELECT * FROM {table_name} LIMIT {int(n)}").fetchdf()
        return df.to_string(index=False) if not df.empty else "No rows returned."
    except Exception as exc:
        return f"Error sampling rows from {table_name}: {exc}"
    finally:
        conn.close()


@tool
def get_row_count(table_name: str) -> str:
    """Return row count for a table or view."""
    conn = _connect()
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        return f"{table_name}: {count} rows"
    except Exception as exc:
        return f"Error counting rows in {table_name}: {exc}"
    finally:
        conn.close()


@tool
def get_column_stats(table_name: str, column_name: str) -> str:
    """Return basic stats for one column: nulls, distincts, min, max."""
    conn = _connect()
    try:
        sql = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT({column_name}) AS non_null_rows,
            COUNT(*) - COUNT({column_name}) AS null_rows,
            COUNT(DISTINCT {column_name}) AS distinct_values,
            MIN({column_name}) AS min_val,
            MAX({column_name}) AS max_val
        FROM {table_name}
        """
        df = conn.execute(sql).fetchdf()
        return df.to_string(index=False)
    except Exception as exc:
        return f"Error getting stats for {table_name}.{column_name}: {exc}"
    finally:
        conn.close()


@tool
def run_query(sql: str) -> str:
    """Execute a read-only SELECT query in DuckDB and return up to 100 rows."""
    if WRITE_PATTERN.search(sql):
        return "Rejected query: only read-only SELECT queries are allowed."

    conn = _connect()
    try:
        df = conn.execute(sql).fetchdf()
        if df.empty:
            return "Query succeeded but returned no rows."
        preview = df.head(100)
        suffix = f"\n\nPreview rows: {len(preview)}/{len(df)}" if len(df) > 100 else ""
        return preview.to_string(index=False) + suffix
    except Exception as exc:
        return f"SQL error: {exc}"
    finally:
        conn.close()


ALL_TOOLS = [
    list_tables,
    describe_table,
    sample_rows,
    get_row_count,
    get_column_stats,
    run_query,
]

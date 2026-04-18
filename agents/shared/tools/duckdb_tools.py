"""
ByteBuddies UWB Dashboard analytiikka sovelluksen DuckDB-työkalut.

Kirjoittaja: Toni Kiuru
"""

from __future__ import annotations

import re
import duckdb

from langchain_core.tools import tool
from agents.shared.config import CONFIG

WRITE_PATTERN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|COPY)\b", re.IGNORECASE)


def _connect() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(CONFIG.duckdb_path), read_only=True)
    # dbt on luonut näkymät suhteessa 'bytebuddies_dbt' kansioon (../data/...)
    dbt_path = CONFIG.duckdb_path.parent.parent.parent / "bytebuddies_dbt"
    conn.execute(f"SET FILE_SEARCH_PATH = '{dbt_path.as_posix()}'")
    return conn


@tool
def list_tables() -> str:
    """Listaa saatavilla olevat taulut ja näkymät DuckDB:stä."""
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
        """).fetchall()
        if not rows:
            return "Ei löytynyt tauluja tai näkymiä."
        return "\n".join(f"{s}.{t} [{tt}]" for s, t, tt in rows)
    finally:
        conn.close()


@tool
def describe_table(table_name: str) -> str:
    """Kuvailee taulun sarakkeet ja tyypit."""
    conn = _connect()
    try:
        rows = conn.execute(f"DESCRIBE {table_name}").fetchall()
        return "\n".join(f"{r[0]}: {r[1]}" for r in rows)
    except Exception as exc:
        return f"Virhe taulun kuvaamisessa {table_name}: {exc}"
    finally:
        conn.close()


@tool
def sample_rows(table_name: str, n: int = 5) -> str:
    """Palauttaa enintään n riviä taulusta tai näkymästä."""
    conn = _connect()
    try:
        df = conn.execute(f"SELECT * FROM {table_name} LIMIT {int(n)}").fetchdf()
        return df.to_string(index=False) if not df.empty else "No rows returned."
    except Exception as exc:
        return f"Virhe rivien hakemisessa taulusta {table_name}: {exc}"
    finally:
        conn.close()


@tool
def get_row_count(table_name: str) -> str:
    """Palauttaa rivimäärän taulusta tai näkymästä."""
    conn = _connect()
    try:
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        return f"{table_name}: {count} rows"
    except Exception as exc:
        return f"Virhe rivimäärän laskemisessa taulussa {table_name}: {exc}"
    finally:
        conn.close()


@tool
def get_column_stats(table_name: str, column_name: str) -> str:
    """Palauttaa tilastot sarakkeelle: nulls, distincts, min, max."""
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
        return f"Virhe tilastojen hakemisessa taulussa {table_name}.{column_name}: {exc}"
    finally:
        conn.close()


@tool
def run_query(sql: str) -> str:
    """Suorittaa vain luku -kyselyn DuckDB:ssä ja palauttaa enintään 100 riviä."""
    if WRITE_PATTERN.search(sql):
        return "Hylätty kysely: vain luku -kyselyt ovat sallittuja."

    conn = _connect()
    try:
        df = conn.execute(sql).fetchdf()
        if df.empty:
            return "Kysely onnistui, mutta ei palauttanut rivejä."
        preview = df.head(100)
        suffix = f"\n\nRivien esikatselu: {len(preview)}/{len(df)}" if len(df) > 100 else ""
        return preview.to_string(index=False) + suffix
    except Exception as exc:
        return f"SQL virhe: {exc}"
    finally:
        conn.close()


@tool
def refresh_schema() -> str:
    """Päivittää tietokannan rakenteen (skeeman) agentin muistiin. Käytä tätä, jos käyttäjä ilmoittaa muuttaneensa tietokantaa."""
    from agents.shared.schema_registry import SchemaRegistry
    registry = SchemaRegistry()
    try:
        registry.refresh()
        return "Skeema päivitetty onnistuneesti välimuistiin. Agentti näkee uuden rakenteen seuraavassa viestissä."
    except Exception as exc:
        return f"Skeeman päivitys epäonnistui: {exc}"


ALL_TOOLS = [
    list_tables,
    describe_table,
    sample_rows,
    get_row_count,
    get_column_stats,
    run_query,
    refresh_schema,
]

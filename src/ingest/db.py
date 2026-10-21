"""DuckDB connection and the immutable bronze schema (F02)."""

from __future__ import annotations

from pathlib import Path

import duckdb

DDL = """
CREATE TABLE IF NOT EXISTS bronze_records (
    run_id        TEXT,
    supplier_id   TEXT,
    source_file   TEXT,
    source_format TEXT,
    row_index     BIGINT,
    raw_payload   JSON,
    raw_sku       TEXT,
    raw_name      TEXT,
    raw_brand     TEXT,
    raw_category  TEXT,
    raw_size      TEXT,
    raw_material  TEXT,
    raw_pressure  TEXT,
    raw_lead_free TEXT
)
"""

# Manifest file inside data/raw/ is excluded from ingestion.
_IGNORED_PREFIXES = ("_", ".")


def connect(path: str | Path) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) the DuckDB database at ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the bronze schema if it does not exist (idempotent)."""
    conn.execute(DDL)

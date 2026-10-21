"""F05: offline checks for the AlloyDB SQL and loader (no cloud calls)."""

from __future__ import annotations

from pathlib import Path

from src.load.load_alloydb import build_embed_sql, build_upsert_sql

_SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def test_sql_files_contain_required_statements() -> None:
    extensions = (_SQL_DIR / "01_extensions.sql").read_text(encoding="utf-8")
    assert "create extension if not exists vector" in extensions
    assert "alloydb_scann" in extensions
    assert "google_ml_integration" in extensions
    assert "pg_trgm" in extensions

    schema = (_SQL_DIR / "02_schema.sql").read_text(encoding="utf-8")
    assert "create table if not exists products" in schema
    assert "vector(768)" in schema
    assert "generated always as (to_tsvector" in schema

    indexes = (_SQL_DIR / "03_indexes.sql").read_text(encoding="utf-8")
    assert "using scann" in indexes
    assert "using gin" in indexes


def test_build_upsert_sql_lists_the_canonical_columns() -> None:
    sql = build_upsert_sql()
    for column in ("sku", "search_text", "brand", "size_in", "lead_free"):
        assert column in sql
    assert "on conflict (sku) do update" in sql


def test_build_embed_sql_is_capped_and_idempotent() -> None:
    sql = build_embed_sql(50)
    assert "limit 50" in sql
    assert "where embedding is null" in sql
    # It only ever touches rows that still need an embedding.
    assert "update products" in sql

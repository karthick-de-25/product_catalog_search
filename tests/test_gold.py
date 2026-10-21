"""F04: gold catalog — canonical units, non-empty search_text, exact row preservation."""

from __future__ import annotations

from pathlib import Path

from src.enrichment.gold import build_search_text, materialize_gold
from src.generate.make_dirty_data import generate_all
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all
from src.quality.contracts import load_contracts
from src.quality.validate import run_quality

_REPO = Path(__file__).resolve().parents[1]
TOTAL_ROWS = 240


def _pipeline(tmp_path: Path):
    """Run data -> ingest -> quality -> gold in a temp DuckDB."""
    raw = tmp_path / "raw"
    generate_all(42, raw)
    conn = connect(tmp_path / "catalog.duckdb")
    init_schema(conn)
    ingest_all(conn, raw)
    run_quality(conn, load_contracts(_REPO / "contracts"), "run-1")
    materialize_gold(conn)
    return conn


def test_search_text_is_built_from_fields() -> None:
    gold = build_search_text(
        {
            "sku": "X-1",
            "name": "brass ball valve",
            "brand": "Watts",
            "category": "pipe",
            "size_in": 0.75,
            "material": "brass",
            "pressure_psi": 381,
            "lead_free": True,
        }
    )
    assert gold
    for token in ("X-1", "brass", "0.75 in", "381 psi", "lead free"):
        assert token in gold


def test_gold_matches_silver_with_canonical_units(tmp_path: Path) -> None:
    conn = _pipeline(tmp_path)

    silver = conn.execute("SELECT count(*) FROM silver_products").fetchone()[0]
    gold_rows = conn.execute("SELECT count(*) FROM gold_products").fetchone()[0]
    assert gold_rows == silver
    assert gold_rows == 197

    # Every gold row has a populated, unique search_text.
    empty = conn.execute(
        "SELECT count(*) FROM gold_products WHERE search_text IS NULL OR trim(search_text) = ''"
    ).fetchone()[0]
    assert empty == 0
    dupes = conn.execute(
        "SELECT count(*) FROM (SELECT sku FROM gold_products GROUP BY sku HAVING count(*) > 1)"
    ).fetchone()[0]
    assert dupes == 0

    # A raw '19 mm' size becomes ~0.748 inches in gold.
    probe = conn.execute(
        "SELECT sku FROM silver_products WHERE size_raw = '19 mm' LIMIT 1"
    ).fetchone()
    assert probe is not None
    size_in = conn.execute(
        "SELECT size_in FROM gold_products WHERE sku = ?", [probe[0]]
    ).fetchone()[0]
    assert size_in == round(19 / 25.4, 3)

    # Some sizes are unparseable -> NULL, but the row still lands in gold (unknown, not lost).
    nulls = conn.execute("SELECT count(*) FROM gold_products WHERE size_in IS NULL").fetchone()[0]
    assert nulls > 0
    conn.close()

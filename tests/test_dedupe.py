"""O03: dedupe — near-duplicate grouping, canonical pick, determinism, losers recorded."""

from __future__ import annotations

from pathlib import Path

from src.enrichment.dedupe import (
    dedupe_rows,
    materialize_deduped,
    names_are_near_duplicates,
    normalize_name_for_match,
)
from src.enrichment.gold import materialize_gold
from src.generate.make_dirty_data import generate_all
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all
from src.quality.contracts import load_contracts
from src.quality.validate import run_quality

_REPO = Path(__file__).resolve().parents[1]


def test_normalize_drops_supplier_tail() -> None:
    assert (
        normalize_name_for_match("1 in brass ball valves for acme valves")
        == "1 in brass ball valves"
    )
    assert "for" not in normalize_name_for_match("1 in brass ball valves for acme valves")


def test_near_duplicate_detection() -> None:
    assert names_are_near_duplicates(
        "1 in brass ball valves for acme valves",
        "1 in brass ball valves for northwind supply",
    )
    assert not names_are_near_duplicates("1 in brass ball valves", "0.75 in pvc pipe")


def test_merge_picks_canonical_and_records_losers() -> None:
    rows = [
        {
            "sku": "A-1",
            "supplier_id": "acme",
            "name": "1 in brass ball valves for acme valves",
            "brand": "acme",
            "category": "ball_valves",
            "size_in": 1.0,
            "material": "brass",
            "pressure_psi": 100,
            "lead_free": True,
            "search_text": "x",
        },
        {
            "sku": "B-2",
            "supplier_id": "nw",
            "name": "1 in brass ball valves for northwind supply",
            "brand": "northwind",
            "category": "ball_valves",
            "size_in": 1.0,
            "material": "brass",
            "pressure_psi": 100,
            "lead_free": True,
            "search_text": "y",
        },
        {
            "sku": "C-3",
            "supplier_id": "pac",
            "name": "0.75 in pvc pipe for pacific pipe",
            "brand": "pacific",
            "category": "pipe",
            "size_in": 0.75,
            "material": "pvc",
            "pressure_psi": 150,
            "lead_free": False,
            "search_text": "z",
        },
    ]

    merged, stats = dedupe_rows(rows)

    assert stats == {"gold_rows": 3, "deduped_rows": 2, "absorbed_skus": 1}
    assert merged[0]["sku"] == "A-1"  # canonical (tie broken by lowest SKU)
    assert merged[0]["merged_skus"] == "B-2"
    assert merged[1]["sku"] == "C-3"
    assert merged[1]["merged_skus"] == ""

    # determinism
    merged_again, _ = dedupe_rows(rows)
    assert merged == merged_again


def test_materialize_deduped_on_full_catalog(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    generate_all(42, raw)
    conn = connect(tmp_path / "catalog.duckdb")
    init_schema(conn)
    ingest_all(conn, raw)
    run_quality(conn, load_contracts(_REPO / "contracts"), "run-1")
    materialize_gold(conn)
    gold = conn.execute("select count(*) from gold_products").fetchone()[0]

    stats = materialize_deduped(conn)

    assert gold == stats["gold_rows"]
    assert stats["deduped_rows"] < gold  # cross-supplier near-duplicates exist
    assert stats["absorbed_skus"] == gold - stats["deduped_rows"]

    # every absorbed SKU is recorded somewhere, and all rows are accounted for
    joins = sum(
        conn.execute(
            "select (select count(*) from gold_deduped where merged_skus like ?)",
            [f"%{sku}%"],
        ).fetchone()[0]
        for sku in [
            r[0] for r in conn.execute("select sku from gold_products order by sku").fetchall()
        ]
    )
    assert joins == gold - stats["deduped_rows"]  # each loser appears exactly once

    # idempotent + deterministic: re-running produces the same table
    materialize_deduped(conn)
    assert conn.execute("select count(*) from gold_deduped").fetchone()[0] == stats["deduped_rows"]
    conn.close()

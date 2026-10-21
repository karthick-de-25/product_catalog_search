"""O01: per-supplier quality scorecard — reconciliation, ranges, and trend."""

from __future__ import annotations

from pathlib import Path

from src.generate.make_dirty_data import generate_all
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all
from src.quality.contracts import load_contracts
from src.quality.scorecard import compute_scorecards
from src.quality.validate import run_quality

_REPO = Path(__file__).resolve().parents[1]


def _pipeline(tmp_path: Path, run_id: str):
    raw = tmp_path / "raw"
    generate_all(42, raw)
    conn = connect(tmp_path / "catalog.duckdb")
    init_schema(conn)
    ingest_all(conn, raw)
    run_quality(conn, load_contracts(_REPO / "contracts"), run_id)
    return conn


def test_scorecard_reconciles_and_ranges(tmp_path: Path) -> None:
    conn = _pipeline(tmp_path, "run-1")
    cards = compute_scorecards(conn)

    assert {card.supplier_id for card in cards} == {
        "acme_valves",
        "northwind_supply",
        "pacific_pipe",
    }

    # supplier totals reconcile with the quality tables
    for card in cards:
        bronze = conn.execute(
            "select count(*) from bronze_records where supplier_id = ?", [card.supplier_id]
        ).fetchone()[0]
        silver = conn.execute(
            "select count(*) from silver_products where supplier_id = ?", [card.supplier_id]
        ).fetchone()[0]
        assert card.bronze == bronze
        assert card.silver == silver
        assert card.silver + card.quarantine == card.bronze

    # dirty feed => no supplier is 100% complete or perfectly valid
    assert all(card.completeness < 1.0 for card in cards)
    assert all(card.validity < 1.0 for card in cards)
    assert all(0.0 <= card.score <= 100.0 for card in cards)
    # and at least one supplier has missing-required + duplicate issues
    assert any(card.missing_required > 0 for card in cards)
    assert any(card.duplicate_sku > 0 for card in cards)
    conn.close()


def test_scorecard_appends_history_for_trend(tmp_path: Path) -> None:
    conn = _pipeline(tmp_path, "run-1")
    compute_scorecards(conn)
    compute_scorecards(conn)

    rows = conn.execute(
        "select supplier_id, count(*) from supplier_scorecards group by 1 order by 1"
    ).fetchall()
    assert {supplier for supplier, _ in rows} == {"acme_valves", "northwind_supply", "pacific_pipe"}
    assert all(count == 2 for _, count in rows)  # two runs => trend is visible
    conn.close()

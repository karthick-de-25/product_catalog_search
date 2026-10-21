"""O04: golden-set builder and metric math — offline, deterministic."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.enrichment.gold import materialize_gold
from src.eval.golden import build_golden_set, mrr, ndcg_at_k, recall_at_k
from src.generate.make_dirty_data import generate_all
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all
from src.quality.contracts import load_contracts
from src.quality.validate import run_quality

_REPO = Path(__file__).resolve().parents[1]


def test_metrics_have_hand_computed_values() -> None:
    relevant = frozenset({"A", "B", "C"})
    retrieved = ["A", "X", "B", "Y", "Z"]

    assert recall_at_k(relevant, retrieved, k=3) == 2 / 3
    assert recall_at_k(relevant, retrieved, k=10) == 2 / 3

    assert mrr(relevant, ["X", "A"]) == 1 / 2
    assert mrr(relevant, ["X", "Y", "Z"]) == 0.0

    # dcg = A@1 (1) + B@3 (1/log2(4)) = 1.5; idcg = 1 + 1/log2(3) + 1/log2(4)
    expected = 1.5 / (1 + 1 / math.log2(3) + 0.5)
    assert ndcg_at_k(relevant, retrieved, k=3) == pytest.approx(expected)


def test_build_golden_set_is_deterministic_and_consistent(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    generate_all(42, raw)
    conn = connect(tmp_path / "catalog.duckdb")
    init_schema(conn)
    ingest_all(conn, raw)
    run_quality(conn, load_contracts(_REPO / "contracts"), "run-1")
    materialize_gold(conn)

    first = build_golden_set(conn, seed=42, count=8, table_name="gold_products")
    second = build_golden_set(conn, seed=42, count=8, table_name="gold_products")
    assert first == second  # deterministic

    all_skus = {row[0] for row in conn.execute("select sku from gold_products").fetchall()}
    queries = {item.query for item in first}
    assert len(first) == 8 + 5 + 3  # 8 entity + 5 size + 3 sku queries
    assert all(item.relevant <= all_skus for item in first)  # relevance is real
    assert all(item.relevant for item in first)
    assert all("_" not in query for query in queries)
    assert "brass ball valves" in queries
    conn.close()

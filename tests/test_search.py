"""F06: hybrid search — routing and RRF fusion are pure and tested offline."""

from __future__ import annotations

from pathlib import Path

from src.search.hybrid_search import route_query, rrf_merge

_SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def test_route_query_distinguishes_sku_from_text() -> None:
    assert route_query("ACME-0001") == "sku"
    assert route_query("acme-0001") == "sku"  # case-insensitive
    assert route_query("NORT-0057") == "sku"
    assert route_query("brass ball valve lead free") == "hybrid"
    assert route_query("3/4 brass ball valve") == "hybrid"
    assert route_query("1.5 in pvc pipe") == "hybrid"


def test_rrf_merge_ranks_overlapping_hits_first() -> None:
    vec = [1, 2, 3, 4]
    kw = [2, 3, 5]
    merged = rrf_merge(vec, kw)

    assert [item_id for item_id, _ in merged] == [2, 3, 1, 5, 4]
    # a product found by both retrievers outranks one found by a single retriever
    assert merged[0][1] > merged[2][1]


def test_rrf_merge_is_deterministic_on_ties() -> None:
    # id 1 and id 2 have identical fused scores; first appearance (vec) wins.
    assert [item_id for item_id, _ in rrf_merge([1, 2], [2, 1])] == [1, 2]


def test_rrf_merge_respects_limit() -> None:
    assert [item_id for item_id, _ in rrf_merge([1, 2, 3], [4, 5], limit=2)] == [1, 4]


def test_hybrid_sql_file_uses_reciprocal_rank_fusion() -> None:
    sql = (_SQL_DIR / "04_hybrid_search.sql").read_text(encoding="utf-8")
    assert "full outer join" in sql
    assert "1.0 / (60.0" in sql
    assert "%(q)s" in sql and "%(cat)s" in sql and "%(limit)s" in sql

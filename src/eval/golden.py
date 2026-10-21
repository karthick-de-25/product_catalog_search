"""Evaluation harness — golden queries, metrics, and the live comparison (O04).

Entry point: ``python -m src.eval.golden`` (wired to ``make eval``).

- :func:`build_golden_set` derives a deterministic query set from the catalog
  (material+category, size-scoped, exact-SKU) with relevant SKUs as ground truth.
- :func:`recall_at_k`, :func:`mrr`, :func:`ndcg_at_k` are pure and unit-tested offline.
- :func:`evaluate_live` runs keyword / vector / hybrid over the golden set against AlloyDB.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from src.config import get_settings
from src.load.apply_sql import connect_alloydb
from src.search.hybrid_search import search_hybrid, search_keyword, search_vector

_RUNNERS = {"keyword": search_keyword, "vector": search_vector, "hybrid": search_hybrid}


@dataclass(frozen=True)
class GoldenQuery:
    query: str
    relevant: frozenset[str]
    kind: str


def recall_at_k(relevant: frozenset[str], retrieved: list[str], k: int = 10) -> float:
    """Fraction of relevant SKUs found in the top ``k``."""
    if not relevant:
        return 1.0
    hits = sum(1 for sku in retrieved[:k] if sku in relevant)
    return hits / len(relevant)


def mrr(relevant: frozenset[str], retrieved: list[str]) -> float:
    """Inverse of the rank of the first relevant result; 0 when none is retrieved."""
    for rank, sku in enumerate(retrieved, start=1):
        if sku in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(relevant: frozenset[str], retrieved: list[str], k: int = 10) -> float:
    """NDCG with binary relevance — penalizes relevant results ranked too low."""
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, sku in enumerate(retrieved[:k], start=1)
        if sku in relevant
    )
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(k, len(relevant)) + 1))
    return dcg / ideal if ideal else 0.0


def build_golden_set(conn, seed: int = 42, count: int = 30, table_name: str = "products"):
    """Derive a deterministic golden query set from a catalog table.

    Relevance is defined structurally: a material+category query is relevant for every
    product with that material+category; a size-scoped query for products of that exact
    size; an SKU query for that SKU.
    """
    rows = conn.execute(
        f"select sku, material, category, size_in from {table_name} order by sku"
    ).fetchall()
    rng = random.Random(seed)

    by_combo: dict[tuple[str, str], list[str]] = {}
    by_triplet: dict[tuple[str, str, float], list[str]] = {}
    for sku, material, category, size in rows:
        by_combo.setdefault((material, category), []).append(sku)
        if size is not None:  # unknown sizes can't anchor a size-scoped query
            by_triplet.setdefault((material, category, float(size)), []).append(sku)

    golden: list[GoldenQuery] = []
    for material, category in sorted(by_combo)[:count]:
        golden.append(
            GoldenQuery(
                query=f"{material} {category.replace('_', ' ')}",
                relevant=frozenset(by_combo[(material, category)]),
                kind="entity",
            )
        )
    for material, category, size in rng.sample(sorted(by_triplet), min(5, len(by_triplet))):
        golden.append(
            GoldenQuery(
                query=f"{float(size):g} in {material} {category.replace('_', ' ')}",
                relevant=frozenset(by_triplet[(material, category, size)]),
                kind="size",
            )
        )
    for sku in [row[0] for row in rows[:3]]:
        golden.append(GoldenQuery(query=sku, relevant=frozenset({sku}), kind="sku"))
    return golden


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def evaluate_live(conn, golden: list[GoldenQuery], k: int = 10, limit: int = 25):
    """Run every retriever over the golden set and aggregate the three metrics."""
    report: dict[str, dict[str, float]] = {}
    for method, runner in _RUNNERS.items():
        recalls: list[float] = []
        mrrs: list[float] = []
        ndcgs: list[float] = []
        for item in golden:
            rows = runner(conn, item.query, limit=limit)
            retrieved = [row[0] for row in rows]
            recalls.append(recall_at_k(item.relevant, retrieved, k))
            mrrs.append(mrr(item.relevant, retrieved))
            ndcgs.append(ndcg_at_k(item.relevant, retrieved, k))
        report[method] = {
            f"recall@{k}": _average(recalls),
            "mrr": _average(mrrs),
            f"ndcg@{k}": _average(ndcgs),
        }
    return report


def main() -> None:
    settings = get_settings()
    conn = connect_alloydb(settings)
    golden = build_golden_set(conn, seed=settings.seed)
    report = evaluate_live(conn, golden)

    k = 10
    header = f"{'method':<10} {'recall@{0}'.format(k):>10} {'mrr':>8} {'ndcg@{0}'.format(k):>10}"
    print(header)
    for method, metrics in report.items():
        print(
            f"{method:<10} {metrics[f'recall@{k}']:>10.4f} "
            f"{metrics['mrr']:>8.4f} {metrics[f'ndcg@{k}']:>10.4f}"
        )
    print(
        f"\n{len(golden)} golden queries "
        f"({sum(1 for g in golden if g.kind == 'entity')} entity, "
        f"{sum(1 for g in golden if g.kind == 'size')} size, "
        f"{sum(1 for g in golden if g.kind == 'sku')} sku)"
    )
    conn.close()


if __name__ == "__main__":
    main()

"""Hybrid search: routing and Reciprocal Rank Fusion (F06).

Entry point: ``python -m src.search.hybrid_search [QUERY]`` (wired to ``make search``).

- :func:`route_query` and :func:`rrf_merge` are pure and unit-tested offline.
- The ``*_search`` functions run read-only queries against AlloyDB through the Auth Proxy
  (they require ``ENABLE_CLOUD=true``; hybrid queries call Vertex AI once per query for the
  query embedding).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from src.config import get_settings
from src.load.apply_sql import connect_alloydb

SKU_PATTERN = re.compile(r"^[A-Z]{2,5}-\d{3,6}$")
RRF_K = 60
DEFAULT_QUERY = "brass ball valve lead free"

_SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def route_query(query: str) -> str:
    """Return ``"sku"`` for part-number-like queries, else ``"hybrid"``."""
    normalized = query.strip().upper()
    return "sku" if SKU_PATTERN.fullmatch(normalized) else "hybrid"


def rrf_merge(
    vec_ranked: list[int],
    kw_ranked: list[int],
    *,
    k: int = RRF_K,
    limit: int | None = None,
) -> list[tuple[int, float]]:
    """Fuse two 1-based ranked id lists with Reciprocal Rank Fusion.

    ``score = sum(1 / (k + rank))`` across both lists; ties break by first appearance so the
    result is deterministic.
    """
    scores: dict[int, float] = {}
    order: list[int] = []
    for ranked in (vec_ranked, kw_ranked):
        for rank, item_id in enumerate(ranked, start=1):
            if item_id not in scores:
                scores[item_id] = 0.0
                order.append(item_id)
            scores[item_id] += 1.0 / (k + rank)

    merged = sorted(order, key=lambda item_id: (-scores[item_id], order.index(item_id)))
    if limit is not None:
        merged = merged[:limit]
    return [(item_id, round(scores[item_id], 6)) for item_id in merged]


def _hybrid_sql() -> str:
    return (_SQL_DIR / "04_hybrid_search.sql").read_text(encoding="utf-8")


_RESULT_SELECT = (
    "select p.sku, p.name, p.brand, p.category, p.size_in, p.pressure_psi, p.lead_free, "
)


def search_hybrid(conn, query: str, category: str | None = None, limit: int = 10):
    """Vector + keyword fused with RRF (the canonical query in sql/04_hybrid_search.sql)."""
    params = {"q": query, "cat": category, "limit": limit}
    return conn.execute(_hybrid_sql(), params).fetchall()


def search_keyword(conn, query: str, category: str | None = None, limit: int = 10):
    """Keyword-only path (baseline for the demo's side-by-side comparison)."""
    sql = (
        _RESULT_SELECT + "round(ts_rank_cd(tsv, plainto_tsquery('english', %(q)s))::numeric, 6) "
        "as score from products p "
        "where p.tsv @@ plainto_tsquery('english', %(q)s) "
        "and (%(cat)s::text is null or p.category = %(cat)s) "
        "order by score desc "
        "limit %(limit)s"
    )
    return conn.execute(sql, {"q": query, "cat": category, "limit": limit}).fetchall()


def search_vector(conn, query: str, category: str | None = None, limit: int = 10):
    """Vector-only path (baseline for the demo's side-by-side comparison)."""
    sql = (
        _RESULT_SELECT + "round((1.0 / (1.0 + (p.embedding <=> "
        "embedding('text-embedding-005', %(q)s)::vector)))::numeric, 6) as score "
        "from products p "
        "where %(cat)s::text is null or p.category = %(cat)s "
        "order by p.embedding <=> embedding('text-embedding-005', %(q)s)::vector "
        "limit %(limit)s"
    )
    return conn.execute(sql, {"q": query, "cat": category, "limit": limit}).fetchall()


def _print_results(title: str, rows) -> None:
    print(f"\n{title}")
    if not rows:
        print("  (no results)")
        return
    for row in rows:
        sku, name, brand, category, size, pressure, lead_free, score = row
        flag = "LF" if lead_free else ("?" if lead_free is None else "")
        print(
            f"  {sku:<10} {float(score):.4f} | {name[:48]:<48} | "
            f"{str(brand)[:14]:<14} {category[:12]:<12} {size} in {pressure} psi {flag}"
        )


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    if not query.strip():
        query = DEFAULT_QUERY
    settings = get_settings()
    conn = connect_alloydb(settings)

    route = route_query(query)
    print(f"query: {query!r} -> route: {route}")

    if route == "sku":
        rows = conn.execute(
            "select sku, name, brand, category, size_in, pressure_psi, lead_free, "
            "0.0 as score from products where sku = upper(%s) limit %s",
            [query, 10],
        ).fetchall()
        _print_results(f"exact SKU lookup ({query})", rows)
    else:
        _print_results("keyword-only", search_keyword(conn, query))
        _print_results("vector-only", search_vector(conn, query))
        _print_results("hybrid (RRF)", search_hybrid(conn, query))
    conn.close()


if __name__ == "__main__":
    main()

"""Near-duplicate deduplication for the gold catalog (O03).

Entry point: ``python -m src.enrichment.dedupe`` (wired to ``make dedupe``). Fully offline.

Deterministic merge: rows with the same ``(material, category, size_in)`` whose normalized
names are similar enough (RapidFuzz token-sort ratio) are collapsed to one canonical product.
Absorbed SKUs are recorded in ``merged_skus`` — CONTEXT invariant 3: the loser is recorded,
never erased.
"""

from __future__ import annotations

import re

import duckdb
import pandas as pd
from rapidfuzz import fuzz

from src.config import get_settings
from src.ingest.db import connect

DEDUPED_DDL = """
create table if not exists gold_deduped (
    sku text, supplier_id text, name text, brand text, category text,
    size_in double, material text, pressure_psi integer, lead_free boolean,
    search_text text, merged_skus text
)
"""

# Name tail we deliberately ignore when matching: "… for acme valves".
_FOR_SUPPLIER = re.compile(r"\s+for\s+[\w\s]+$")
_SIMILARITY_THRESHOLD = 88
_BATCH_SIZE = 5_000  # rows held before a bulk append (see materialize_deduped)

GOLD_DEDUPED_COLUMNS = (
    "sku",
    "supplier_id",
    "name",
    "brand",
    "category",
    "size_in",
    "material",
    "pressure_psi",
    "lead_free",
    "search_text",
    "merged_skus",
)

_COLUMNS = (
    "sku",
    "supplier_id",
    "name",
    "brand",
    "category",
    "size_in",
    "material",
    "pressure_psi",
    "lead_free",
    "search_text",
)


def normalize_name_for_match(name: str) -> str:
    """Lowercase name without its 'for <supplier>' tail (the differentiator to ignore)."""
    return _FOR_SUPPLIER.sub("", name.strip().lower())


def names_are_near_duplicates(name_a: str, name_b: str) -> bool:
    """Token-sort ratio of the normalized names, above the similarity threshold."""
    normalized_a = normalize_name_for_match(name_a)
    normalized_b = normalize_name_for_match(name_b)
    return fuzz.token_sort_ratio(normalized_a, normalized_b) >= _SIMILARITY_THRESHOLD


def _completeness(row: dict[str, object]) -> int:
    return sum(
        1
        for key in ("name", "brand", "pressure_psi", "lead_free")
        if row.get(key) not in (None, "")
    )


def dedupe_rows(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Collapse near-duplicates. Deterministic: blocks and rows in sorted order, each row
    compared against the first (canonical) member of each candidate group (star topology, so
    no re-merging of an already-merged row)."""
    blocks: dict[tuple[object, object, object], list[dict[str, object]]] = {}
    for row in rows:
        blocks.setdefault((row["material"], row["category"], row["size_in"]), []).append(row)

    merged: list[dict[str, object]] = []
    absorbed = 0
    for block_key in sorted(blocks, key=lambda key: (str(key[0]), str(key[1]), str(key[2]))):
        groups: list[list[dict[str, object]]] = []
        for row in sorted(blocks[block_key], key=lambda r: str(r["sku"])):
            target = next(
                (
                    group
                    for group in groups
                    if names_are_near_duplicates(str(group[0]["name"]), str(row["name"]))
                ),
                None,
            )
            if target is None:
                groups.append([row])
            else:
                target.append(row)

        for group in groups:
            canonical = min(group, key=lambda r: (-_completeness(r), str(r["sku"])))
            losers = sorted(str(r["sku"]) for r in group if r["sku"] != canonical["sku"])
            canonical["merged_skus"] = ", ".join(losers)
            merged.append(canonical)
            absorbed += len(losers)

    merged.sort(key=lambda r: str(r["sku"]))
    return merged, {"gold_rows": len(rows), "deduped_rows": len(merged), "absorbed_skus": absorbed}


def materialize_deduped(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Rebuild ``gold_deduped`` from ``gold_products`` (idempotent)."""
    conn.execute(DEDUPED_DDL)
    conn.execute("delete from gold_deduped")
    rows = [
        dict(zip(_COLUMNS, row))
        for row in conn.execute(
            f"select {', '.join(_COLUMNS)} from gold_products order by sku"
        ).fetchall()
    ]
    merged, stats = dedupe_rows(rows)
    batch: list[tuple[object, ...]] = []
    for row in merged:
        batch.append(
            (
                row["sku"],
                row["supplier_id"],
                row["name"],
                row["brand"],
                row["category"],
                row["size_in"],
                row["material"],
                row["pressure_psi"],
                row["lead_free"],
                row["search_text"],
                row["merged_skus"],
            )
        )
        if len(batch) >= _BATCH_SIZE:  # bulk append: same table/rows, faster at scale
            conn.append("gold_deduped", pd.DataFrame(batch, columns=GOLD_DEDUPED_COLUMNS))
            batch = []
    if batch:
        conn.append("gold_deduped", pd.DataFrame(batch, columns=GOLD_DEDUPED_COLUMNS))
    return stats


def main() -> None:
    settings = get_settings()
    conn = connect(settings.duckdb_path)
    exists = conn.execute(
        "select count(*) from information_schema.tables where table_name = 'gold_products'"
    ).fetchone()[0]
    if not exists:
        print("gold_products missing — run 'make gold' first")
        conn.close()
        return
    stats = materialize_deduped(conn)
    print(
        f"gold_products {stats['gold_rows']} -> gold_deduped {stats['deduped_rows']} "
        f"(absorbed {stats['absorbed_skus']} duplicate SKUs)"
    )
    conn.close()


if __name__ == "__main__":
    main()

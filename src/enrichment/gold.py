"""Materialize the clean, searchable gold catalog from silver (F04).

Entry point: ``python -m src.enrichment.gold`` (wired to ``make gold``).

Reads ``silver_products``, normalizes each row to the canonical model, builds a
``search_text`` for indexing, and writes ``gold_products`` — keeping raw values available in
``silver_products`` for reference.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from src.config import get_settings
from src.enrichment.normalize import normalize_row
from src.ingest.db import connect

GOLD_DDL = """
CREATE TABLE IF NOT EXISTS gold_products (
    sku TEXT, supplier_id TEXT, name TEXT, brand TEXT, category TEXT,
    size_in DOUBLE, material TEXT, pressure_psi INTEGER,
    lead_free BOOLEAN, search_text TEXT
)
"""

SILVER_COLUMNS = (
    "sku",
    "supplier_id",
    "name",
    "brand_raw",
    "category_raw",
    "size_raw",
    "material_raw",
    "pressure_raw",
    "lead_free_raw",
)


def build_search_text(gold: dict[str, object]) -> str:
    """Concatenate the fields someone might search for; never empty (sku + name exist).

    Underscores are replaced with spaces so the English full-text tokenizer sees real words
    (``ball_valves`` -> ``ball valves``) — keyword search would otherwise return nothing.
    """
    pieces = [
        str(gold["sku"]),
        str(gold["name"]),
        str(gold["brand"]),
        str(gold["category"]),
        f"{float(gold['size_in']):g} in" if gold["size_in"] is not None else "",
        str(gold["material"]),
        f"{int(gold['pressure_psi'])} psi" if gold["pressure_psi"] is not None else "",
        "lead free" if gold["lead_free"] is True else "",
    ]
    return " ".join(piece for piece in pieces if piece).replace("_", " ")


@dataclass
class GoldRun:
    silver_rows: int
    gold_rows: int
    silver_size_raw: int  # silver rows that shipped a size string
    gold_size_known: int  # gold rows with a parsed size_in


def materialize_gold(conn: duckdb.DuckDBPyConnection) -> GoldRun:
    """Rebuild ``gold_products`` from ``silver_products`` (idempotent)."""
    conn.execute(GOLD_DDL)
    conn.execute("DELETE FROM gold_products")

    rows = conn.execute(
        f"SELECT {', '.join(SILVER_COLUMNS)} FROM silver_products ORDER BY sku"
    ).fetchall()

    gold_rows = size_known = 0
    for row in rows:
        gold = normalize_row(dict(zip(SILVER_COLUMNS, row)))
        gold["search_text"] = build_search_text(gold)
        conn.execute(
            "INSERT INTO gold_products (sku, supplier_id, name, brand, category, size_in, "
            "material, pressure_psi, lead_free, search_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                gold["sku"],
                gold["supplier_id"],
                gold["name"],
                gold["brand"],
                gold["category"],
                gold["size_in"],
                gold["material"],
                gold["pressure_psi"],
                gold["lead_free"],
                gold["search_text"],
            ),
        )
        gold_rows += 1
        if gold["size_in"] is not None:
            size_known += 1

    silver_size_raw = conn.execute(
        "SELECT count(*) FROM silver_products WHERE size_raw <> ''"
    ).fetchone()[0]

    return GoldRun(
        silver_rows=len(rows),
        gold_rows=gold_rows,
        silver_size_raw=silver_size_raw,
        gold_size_known=size_known,
    )


def _table_exists(conn: duckdb.DuckDBPyConnection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table]
        ).fetchone()[0]
        > 0
    )


def main() -> None:
    settings = get_settings()
    conn = connect(settings.duckdb_path)
    if not _table_exists(conn, "silver_products"):
        print("silver_products missing — run 'make data && make ingest && make quality' first")
        conn.close()
        return

    run = materialize_gold(conn)

    silver_pct = run.silver_size_raw / run.silver_rows * 100 if run.silver_rows else 0.0
    gold_pct = run.gold_size_known / run.gold_rows * 100 if run.gold_rows else 0.0
    print(f"gold_products: {run.gold_rows} rows (from {run.silver_rows} silver)")
    print(f"size completeness: silver {silver_pct:.1f}% -> gold {gold_pct:.1f}%")
    conn.close()


if __name__ == "__main__":
    main()

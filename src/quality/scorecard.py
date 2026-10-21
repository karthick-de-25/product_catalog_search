"""Per-supplier quality scorecard with run history (optional feature O01).

Entry point: ``python -m src.quality.scorecard`` (wired to ``make scorecard``).

Each run appends one row per supplier to ``supplier_scorecards`` (keyed by ``run_id``), so
re-running builds a trend. Pure local DuckDB — no cloud.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

from src.config import get_settings
from src.ingest.db import connect, init_schema

SCORECARD_DDL = """
create table if not exists supplier_scorecards (
    run_id           text,
    supplier_id      text,
    bronze           integer,
    silver           integer,
    quarantine       integer,
    missing_required integer,
    type_mismatch    integer,
    out_of_range     integer,
    duplicate_sku    integer,
    completeness     double,
    validity         double,
    score            double,
    scored_at        timestamp
)
"""

# Attributes measured for completeness on silver rows (raw values still present).
_COMPLETENESS_ATTRS = (
    "sku",
    "name",
    "brand_raw",
    "category_raw",
    "size_raw",
    "material_raw",
    "pressure_raw",
    "lead_free_raw",
)

_REASON_COLUMNS = ("missing_required", "type_mismatch", "out_of_range", "duplicate_sku")


@dataclass
class ScorecardRow:
    supplier_id: str
    bronze: int
    silver: int
    quarantine: int
    missing_required: int
    type_mismatch: int
    out_of_range: int
    duplicate_sku: int
    completeness: float
    validity: float
    score: float


def compute_scorecards(conn: duckdb.DuckDBPyConnection) -> list[ScorecardRow]:
    """Compute one scorecard per supplier and store it (appending to history)."""
    conn.execute(SCORECARD_DDL)

    bronze_by_supplier = dict(
        conn.execute("select supplier_id, count(*) from bronze_records group by 1").fetchall()
    )
    silver_rows = conn.execute(
        f"select supplier_id, {', '.join(_COMPLETENESS_ATTRS)} from silver_products"
    ).fetchall()
    quarantine_by_supplier: dict[str, dict[str, int]] = {}
    for supplier_id, reason_code, count in conn.execute(
        "select supplier_id, reason_code, count(*) from quarantine_records group by 1, 2"
    ).fetchall():
        quarantine_by_supplier.setdefault(supplier_id, {})[reason_code] = count

    per_supplier: dict[str, list[tuple]] = {}
    for row in silver_rows:
        per_supplier.setdefault(row[0], []).append(row[1:])

    run_id = datetime.now(timezone.utc).isoformat()
    scored_at = datetime.now(timezone.utc)

    result: list[ScorecardRow] = []
    for supplier_id in sorted(bronze_by_supplier):
        silver = len(per_supplier.get(supplier_id, []))
        bronze = bronze_by_supplier[supplier_id]
        codes = quarantine_by_supplier.get(supplier_id, {})
        quarantine = sum(codes.values())

        cells = silver * len(_COMPLETENESS_ATTRS)
        non_empty = sum(
            1
            for row in per_supplier.get(supplier_id, [])
            for cell in row
            if str(cell or "").strip()
        )
        completeness = round(non_empty / cells, 4) if cells else 0.0
        validity = round(silver / bronze, 4) if bronze else 0.0
        score = round(100 * (0.5 * completeness + 0.5 * validity), 1)

        card = ScorecardRow(
            supplier_id=supplier_id,
            bronze=bronze,
            silver=silver,
            quarantine=quarantine,
            missing_required=codes.get("MISSING_REQUIRED", 0),
            type_mismatch=codes.get("TYPE_MISMATCH", 0),
            out_of_range=codes.get("OUT_OF_RANGE", 0),
            duplicate_sku=codes.get("DUPLICATE_SKU", 0),
            completeness=completeness,
            validity=validity,
            score=score,
        )
        conn.execute(
            "insert into supplier_scorecards (run_id, supplier_id, bronze, silver, "
            "quarantine, missing_required, type_mismatch, out_of_range, duplicate_sku, "
            "completeness, validity, score, scored_at) "
            "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                card.supplier_id,
                card.bronze,
                card.silver,
                card.quarantine,
                card.missing_required,
                card.type_mismatch,
                card.out_of_range,
                card.duplicate_sku,
                card.completeness,
                card.validity,
                card.score,
                scored_at,
            ),
        )
        result.append(card)
    return result


def main() -> None:
    settings = get_settings()
    conn = connect(settings.duckdb_path)
    init_schema(conn)
    cards = compute_scorecards(conn)
    if not cards:
        print("no bronze rows — run 'make data && make ingest && make quality' first")
        conn.close()
        return

    header = (
        f"{'supplier':<18} {'bronze':>7} {'silver':>7} {'quar':>6} "
        f"{'missing':>8} {'dupe':>5} {'comp%':>7} {'valid%':>8} {'score':>6}"
    )
    print(header)
    for card in cards:
        print(
            f"{card.supplier_id:<18} {card.bronze:>7} {card.silver:>7} {card.quarantine:>6} "
            f"{card.missing_required:>8} {card.duplicate_sku:>5} "
            f"{card.completeness * 100:>6.1f}% {card.validity * 100:>7.1f}% {card.score:>6.1f}"
        )
    print("\nhistory rows:", conn.execute("select count(*) from supplier_scorecards").fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()

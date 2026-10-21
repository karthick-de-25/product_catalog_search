"""Quality gate: bronze → silver_products + quarantine_records (F03).

Entry point: ``python -m src.quality.validate`` (wired to ``make quality``).

Every bronze row goes to exactly one output table, preserving the invariant
``bronze = silver + quarantine``. Quarantined rows carry one primary reason code, the field
at fault, and the original raw payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

from src.config import get_settings
from src.errors import ContractError, DataQualityError
from src.ingest.db import connect, init_schema
from src.quality.contracts import SupplierContract, load_contracts
from src.quality.rules import as_text, check_row, resolve_value

SILVER_DDL = """
CREATE TABLE IF NOT EXISTS silver_products (
    run_id TEXT, supplier_id TEXT, source_file TEXT,
    sku TEXT, name TEXT,
    brand_raw TEXT, category_raw TEXT, size_raw TEXT, material_raw TEXT,
    pressure_raw TEXT, lead_free_raw TEXT
)
"""

QUARANTINE_DDL = """
CREATE TABLE IF NOT EXISTS quarantine_records (
    run_id TEXT, supplier_id TEXT, source_file TEXT, row_index BIGINT,
    sku TEXT, field TEXT, reason_code TEXT, detail TEXT, raw_payload JSON
)
"""

# Logical silver columns in insert order (mapped through the contract's field names).
SILVER_FIELDS = (
    "sku",
    "name",
    "brand",
    "category",
    "size_raw",
    "material",
    "pressure_psi",
    "lead_free",
)


@dataclass
class QualityRun:
    bronze: int
    silver: int
    quarantine: int
    by_supplier: dict[str, dict[str, int]]


def _silver_values(contract: SupplierContract, payload: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        as_text(resolve_value(payload, contract.mapping[field])).strip() for field in SILVER_FIELDS
    )


def run_quality(
    conn: duckdb.DuckDBPyConnection,
    contracts: dict[str, SupplierContract],
    run_id: str,
) -> QualityRun:
    """Validate every bronze row, writing silver and quarantine (idempotent per run)."""
    conn.execute(SILVER_DDL)
    conn.execute(QUARANTINE_DDL)
    conn.execute("DELETE FROM silver_products")
    conn.execute("DELETE FROM quarantine_records")

    rows = conn.execute(
        "SELECT source_file, supplier_id, row_index, cast(raw_payload AS VARCHAR) "
        "FROM bronze_records ORDER BY supplier_id, row_index"
    ).fetchall()

    silver = quarantine = 0
    by_supplier: dict[str, dict[str, int]] = {}
    seen: set[str] = set()
    current_supplier: str | None = None

    for source_file, supplier, row_index, payload_text in rows:
        if supplier != current_supplier:
            current_supplier = supplier
            seen = set()
        contract = contracts.get(supplier)
        if contract is None:
            raise ContractError(f"no contract for supplier {supplier!r}")
        payload = json.loads(payload_text)

        stats = by_supplier.setdefault(supplier, {"bronze": 0, "silver": 0, "quarantine": 0})
        stats["bronze"] += 1

        finding = check_row(contract, payload, seen)
        if finding is not None:
            sku = as_text(resolve_value(payload, contract.mapping["sku"])).strip()
            conn.execute(
                "INSERT INTO quarantine_records "
                "(run_id, supplier_id, source_file, row_index, sku, field, reason_code, "
                "detail, raw_payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    supplier,
                    source_file,
                    row_index,
                    sku,
                    finding.field,
                    finding.reason.value,
                    finding.detail,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            quarantine += 1
            stats["quarantine"] += 1
        else:
            values = _silver_values(contract, payload)
            conn.execute(
                "INSERT INTO silver_products "
                "(run_id, supplier_id, source_file, sku, name, brand_raw, category_raw, "
                "size_raw, material_raw, pressure_raw, lead_free_raw) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, supplier, source_file, *values),
            )
            silver += 1
            stats["silver"] += 1

    return QualityRun(
        bronze=len(rows), silver=silver, quarantine=quarantine, by_supplier=by_supplier
    )


def main() -> None:
    settings = get_settings()
    contracts = load_contracts(settings.contracts_dir)
    conn = connect(settings.duckdb_path)
    init_schema(conn)

    run = run_quality(conn, contracts, datetime.now(timezone.utc).isoformat())

    if run.bronze == 0:
        print("no bronze rows — run 'make data && make ingest' first")
        conn.close()
        return

    print(f"{'supplier':<18} {'bronze':>7} {'silver':>7} {'quarantine':>11}")
    for supplier, stats in sorted(run.by_supplier.items()):
        print(f"{supplier:<18} {stats['bronze']:>7} {stats['silver']:>7} {stats['quarantine']:>11}")
    print("-" * 46)
    print(f"{'total':<18} {run.bronze:>7} {run.silver:>7} {run.quarantine:>11}")

    if run.bronze != run.silver + run.quarantine:
        raise DataQualityError(
            "reconciliation failed",
            bronze=run.bronze,
            silver=run.silver,
            quarantine=run.quarantine,
        )
    print(
        f"reconciliation: bronze {run.bronze} = silver {run.silver} + quarantine {run.quarantine} ✓"
    )
    conn.close()


if __name__ == "__main__":
    main()

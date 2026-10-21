"""F03: data quality — contracts, rule emission, and exact reconciliation."""

from __future__ import annotations

from pathlib import Path

from src.errors import ReasonCode
from src.generate.make_dirty_data import generate_all
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all
from src.quality.contracts import SupplierContract, load_contracts
from src.quality.rules import check_row, resolve_value
from src.quality.validate import run_quality

_REPO = Path(__file__).resolve().parents[1]
TOTAL_ROWS = 240


def _contracts() -> dict[str, SupplierContract]:
    return load_contracts(_REPO / "contracts")


def test_contracts_load_for_all_suppliers() -> None:
    contracts = _contracts()
    assert set(contracts) == {"acme_valves", "northwind_supply", "pacific_pipe"}

    acme = contracts["acme_valves"]
    assert acme.required == ["sku", "name", "brand", "category", "material"]

    # Nested JSON paths resolve.
    nw = contracts["northwind_supply"]
    payload = {"id": "N-1", "attributes": {"size": "19 mm", "material": "pvc"}}
    assert resolve_value(payload, nw.mapping["size_raw"]) == "19 mm"
    assert resolve_value(payload, nw.mapping["material"]) == "pvc"


def test_each_reason_code_is_emitted() -> None:
    acme = _contracts()["acme_valves"]
    good = {
        "sku": "A-1",
        "name": "brass ball valve",
        "brand": "Watts",
        "category": "pipe",
        "size": "0.75 in",
        "material": "brass",
        "pressure": "381",
        "lead_free": "True",
    }

    assert check_row(acme, {**good, "name": ""}, set()).reason is ReasonCode.MISSING_REQUIRED
    assert check_row(acme, {**good, "pressure": "high"}, set()).reason is ReasonCode.TYPE_MISMATCH
    assert (
        check_row(acme, {**good, "category": "widgets"}, set()).reason is ReasonCode.TYPE_MISMATCH
    )
    assert check_row(acme, {**good, "pressure": "99999"}, set()).reason is ReasonCode.OUT_OF_RANGE
    assert check_row(acme, good, {"A-1"}).reason is ReasonCode.DUPLICATE_SKU
    assert check_row(acme, good, set()) is None


def test_reconciliation_bronze_equals_silver_plus_quarantine(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    generate_all(42, raw)
    conn = connect(tmp_path / "catalog.duckdb")
    init_schema(conn)
    ingest_all(conn, raw)

    run = run_quality(conn, load_contracts(_REPO / "contracts"), "run-1")

    assert run.bronze == TOTAL_ROWS
    assert run.silver + run.quarantine == run.bronze
    assert run.quarantine > 0 and run.silver > 0

    # Every quarantine row carries a closed reason code.
    codes = {
        row[0]
        for row in conn.execute("SELECT DISTINCT reason_code FROM quarantine_records").fetchall()
    }
    assert codes <= {code.value for code in ReasonCode}

    # Silver keeps raw values untouched (normalization is F04's job).
    sample = conn.execute(
        "SELECT brand_raw, size_raw FROM silver_products WHERE brand_raw <> '' LIMIT 1"
    ).fetchone()
    assert sample is not None and sample[0]  # a raw brand string survived in silver
    conn.close()

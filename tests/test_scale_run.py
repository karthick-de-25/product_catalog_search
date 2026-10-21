"""S04 slice 2 — offline scale run: reconciliation, stages, dedupe ground truth."""

from __future__ import annotations

from pathlib import Path

from src.config import Settings
from src.scale.run_scale import REPORT_NAME, run_scale


def test_scale_run_reconciles_exactly_and_verifies_clusters(tmp_path: Path) -> None:
    settings = Settings(seed=42, scale_tier="1k", scale_dir=tmp_path)
    settings.contracts_dir = Path("contracts")  # baseline demo contracts

    report = run_scale(settings)

    # Reconciliation is exact: bronze = silver + quarantine.
    reconciliation = report.reconciliation
    assert reconciliation["bronze"] == 1_000
    assert reconciliation["exact"] is True
    assert reconciliation["silver"] + reconciliation["quarantine"] == reconciliation["bronze"]
    assert reconciliation["silver"] > 0 and reconciliation["quarantine"] > 0

    # All pipeline stages ran and every one is timed.
    stage_names = [stage["stage"] for stage in report.stages]
    assert stage_names == ["generate", "ingest", "quality", "gold", "dedupe", "embed"]
    assert all(stage["seconds"] >= 0 for stage in report.stages)

    # Every ground-truth duplicate cluster collapsed into one deduped row.
    assert report.clusters["ok"] is True
    assert report.clusters["verified"] == report.clusters["clusters"] > 0

    # Dedupe actually merged something across the 100 suppliers.
    conn = __import__("duckdb").connect(tmp_path / "catalog.duckdb", read_only=True)
    gold = conn.execute("SELECT count(*) FROM gold_products").fetchone()[0]
    deduped = conn.execute("SELECT count(*) FROM gold_deduped").fetchone()[0]
    assert deduped < gold
    conn.close()

    # The report file exists and is machine-checkable JSON.
    report_payload = (tmp_path / REPORT_NAME).read_text()
    assert '"exact": true' in report_payload
    assert '"stages"' in report_payload

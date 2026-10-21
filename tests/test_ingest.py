"""F02: bronze ingestion — counts reconcile with the manifest, loads are idempotent."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

from src.generate.make_dirty_data import generate_all
from src.generate.manifest import write_manifest
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all

TOTAL_ROWS = 240  # 100 + 80 + 60 for SEED=42


def _seed_raw_dir(root: Path) -> Path:
    raw = root / "raw"
    entries = generate_all(42, raw)
    write_manifest(42, entries, raw)
    return raw


def _load(raw: Path, db_path: Path) -> duckdb.DuckDBPyConnection:
    conn = connect(db_path)
    init_schema(conn)
    ingest_all(conn, raw)
    return conn


def test_bronze_counts_match_manifest(tmp_path: Path) -> None:
    raw = _seed_raw_dir(tmp_path)
    conn = _load(raw, tmp_path / "catalog.duckdb")

    assert conn.execute("SELECT count(*) FROM bronze_records").fetchone()[0] == TOTAL_ROWS

    manifest = json.loads((raw / "_manifest.json").read_text(encoding="utf-8"))
    per_file = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT source_file, count(*) FROM bronze_records GROUP BY source_file"
        ).fetchall()
    }
    for entry in manifest["files"]:
        assert per_file[entry["name"]] == entry["rows"]
    conn.close()


def test_ingest_is_idempotent(tmp_path: Path) -> None:
    raw = _seed_raw_dir(tmp_path)
    conn = connect(tmp_path / "catalog.duckdb")
    init_schema(conn)

    ingest_all(conn, raw)
    ingest_all(conn, raw)

    assert conn.execute("SELECT count(*) FROM bronze_records").fetchone()[0] == TOTAL_ROWS
    conn.close()


def test_raw_payload_round_trips(tmp_path: Path) -> None:
    raw = _seed_raw_dir(tmp_path)
    conn = _load(raw, tmp_path / "catalog.duckdb")

    def stored_json(file: str) -> object:
        """The stored raw_payload (DuckDB returns JSON columns as text)."""
        result = conn.execute(
            "SELECT raw_payload FROM bronze_records WHERE source_file = ? AND row_index = 0",
            [file],
        ).fetchone()
        assert result is not None
        return json.loads(result[0])

    # CSV: payload parses back to the source row verbatim.
    with (raw / "acme_valves.csv").open(newline="", encoding="utf-8") as handle:
        source_row = dict(next(csv.DictReader(handle)))
    assert stored_json("acme_valves.csv") == source_row

    # JSON: payload parses back to the source item verbatim (nested attributes included).
    source_item = json.loads((raw / "northwind_supply.json").read_text(encoding="utf-8"))[0]
    assert stored_json("northwind_supply.json") == source_item

    # XML: payload holds partNo + every child element's text.
    part = ET.parse(raw / "pacific_pipe.xml").getroot().findall("part")[0]
    payload = stored_json("pacific_pipe.xml")
    expected = {"partNo": part.get("partNo"), **{c.tag: (c.text or "") for c in part}}
    assert payload == expected
    conn.close()

"""Load raw supplier feeds into DuckDB bronze (F02).

Entry point: ``python -m src.ingest.load_bronze`` (wired to ``make ingest``).

Values are stored **exactly as delivered** — bronze is not cleaned or typed here.
Idempotency: each file is deleted-then-inserted by ``source_file``, so re-running
``make ingest`` never duplicates rows.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb
import pandas as pd

from src.config import get_settings
from src.ingest.db import _IGNORED_PREFIXES, connect, init_schema

RAW_KEYS = (
    "raw_sku",
    "raw_name",
    "raw_brand",
    "raw_category",
    "raw_size",
    "raw_material",
    "raw_pressure",
    "raw_lead_free",
)


@dataclass
class LoadedFile:
    """Bronze load result for one feed."""

    source_file: str
    source_format: str
    rows: int


def _records_csv(path: Path) -> list[tuple[dict[str, object], list[str]]]:
    """CSV feed → (payload, raw_* values by RAW_KEYS order)."""
    records: list[tuple[dict[str, object], list[str]]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            payload = {key: value for key, value in row.items()}
            raw = [
                row.get(field, "")
                for field in (
                    "sku",
                    "name",
                    "brand",
                    "category",
                    "size",
                    "material",
                    "pressure",
                    "lead_free",
                )
            ]
            records.append((payload, raw))
    return records


def _records_json(path: Path) -> list[tuple[dict[str, object], list[str]]]:
    """JSON feed → (payload, raw_* values)."""
    records: list[tuple[dict[str, object], list[str]]] = []
    for item in json.loads(path.read_text(encoding="utf-8")):
        attrs = item.get("attributes", {})
        payload = {key: value for key, value in item.items()}
        raw = [
            str(item.get("id", "")),
            str(item.get("title", "")),
            str(item.get("vendor", "")),
            str(item.get("category", "")),
            str(attrs.get("size", "")),
            str(attrs.get("material", "")),
            str(attrs.get("pressure", "")),
            str(item.get("lead_free", "")),
        ]
        records.append((payload, raw))
    return records


def _records_xml(path: Path) -> list[tuple[dict[str, object], list[str]]]:
    """XML feed → (payload built from element, raw_* values)."""
    records: list[tuple[dict[str, object], list[str]]] = []
    root = ET.parse(path).getroot()
    for part in root.findall("part"):
        payload = {
            "partNo": part.get("partNo", ""),
            "product": part.get("product", ""),
            **{child.tag: (child.text or "") for child in part},
        }
        texts = {child.tag: (child.text or "") for child in part}
        raw = [
            part.get("partNo", ""),
            part.get("product", ""),
            texts.get("brand", ""),
            texts.get("category", ""),
            texts.get("size", ""),
            texts.get("material", ""),
            texts.get("pressure", ""),
            texts.get("lead_free", ""),
        ]
        records.append((payload, raw))
    return records


_RECORD_READERS = {"csv": _records_csv, "json": _records_json, "xml": _records_xml}


def ingest_file(
    conn: duckdb.DuckDBPyConnection, path: Path, run_id: str, supplier_id: str
) -> LoadedFile:
    """Load one feed into bronze (idempotent per ``source_file``)."""
    fmt = path.suffix[1:]
    records = _RECORD_READERS[fmt](path)
    conn.execute("DELETE FROM bronze_records WHERE source_file = ?", [path.name])
    # Bulk append — per-row ``executemany`` is ~1000x slower at scale (S04 finding).
    columns = [
        "run_id",
        "supplier_id",
        "source_file",
        "source_format",
        "row_index",
        "raw_payload",
        *RAW_KEYS,
    ]
    df = pd.DataFrame(
        [
            (run_id, supplier_id, path.name, fmt, index, json.dumps(payload, sort_keys=True), *raw)
            for index, (payload, raw) in enumerate(records)
        ],
        columns=columns,
    )
    conn.append("bronze_records", df)
    return LoadedFile(path.name, fmt, len(records))


def ingest_all(conn: duckdb.DuckDBPyConnection, raw_dir: Path) -> list[LoadedFile]:
    """Load every feed under ``raw_dir`` (excluding the manifest) into bronze."""
    run_id = datetime.now(timezone.utc).isoformat()
    loaded: list[LoadedFile] = []
    for path in sorted(raw_dir.iterdir()):
        fmt = path.suffix[1:]
        if fmt not in _RECORD_READERS or path.name.startswith(_IGNORED_PREFIXES):
            continue
        loaded.append(ingest_file(conn, path, run_id, path.stem))
    return loaded


def main() -> None:
    settings = get_settings()
    conn = connect(settings.duckdb_path)
    init_schema(conn)
    loaded = ingest_all(conn, settings.raw_dir)
    for info in loaded:
        print(f"  {info.source_file}: {info.rows} rows -> bronze_records")
    total = sum(info.rows for info in loaded)
    print(f"loaded {len(loaded)} feeds, {total} rows total")
    conn.close()


if __name__ == "__main__":
    main()

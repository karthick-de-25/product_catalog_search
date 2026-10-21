"""Generate the three synthetic dirty supplier feeds and a defect manifest (F01).

Entry point: ``python -m src.generate.make_dirty_data`` (wired to ``make data``).
All output is deterministic for a fixed ``SEED``.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path
from xml.etree import ElementTree as ET

from src.config import get_settings
from src.generate import defects
from src.generate.catalog_seed import clean_products
from src.generate.manifest import FileManifest, write_manifest

Row = dict[str, object]

# (file stem, format, row count per supplier)
SPECS = (
    ("acme_valves", "csv", 100),
    ("northwind_supply", "json", 80),
    ("pacific_pipe", "xml", 60),
)


def _to_csv_row(row: Row) -> dict[str, str]:
    return {
        "sku": str(row["sku"]),
        "name": str(row.get("name", "")),
        "brand": str(row.get("brand", "")),
        "category": str(row.get("category", "")),
        "size": str(row.get("size_raw", "")),
        "material": str(row.get("material", "")),
        "pressure": str(row.get("pressure_psi", "")),
        "lead_free": str(row["lead_free"]) if row.get("lead_free") is not None else "",
    }


def _to_json_row(row: Row) -> dict[str, object]:
    return {
        "id": str(row["sku"]),
        "title": str(row.get("name", "")),
        "vendor": str(row.get("brand", "")),
        "attributes": {
            "size": str(row.get("size_raw", "")),
            "material": str(row.get("material", "")),
            "pressure": str(row.get("pressure_psi", "")),
        },
        "lead_free": row.get("lead_free"),
        "category": row.get("category"),
        "description": row.get("description"),
    }


def _write_csv(path: Path, rows: list[Row]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_to_csv_row(rows[0])))
        writer.writeheader()
        writer.writerows(_to_csv_row(row) for row in rows)


def _write_json(path: Path, rows: list[Row]) -> None:
    payload = [_to_json_row(row) for row in rows]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_xml(path: Path, rows: list[Row]) -> None:
    root = ET.Element("supplier")
    for row in rows:
        part = ET.SubElement(root, "part")
        part.set("partNo", str(row["sku"]))
        part.set("product", str(row.get("name", "")))
        for key, source in (
            ("brand", "brand"),
            ("category", "category"),
            ("material", "material"),
            ("pressure", "pressure_psi"),
            ("lead_free", "lead_free"),
        ):
            value = row.get(source)
            ET.SubElement(part, key).text = str(value) if value is not None else ""
        ET.SubElement(part, "size").text = str(row.get("size_raw", ""))
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


_WRITERS = {"csv": _write_csv, "json": _write_json, "xml": _write_xml}


def count_rows(path: Path) -> int:
    """Row count of a generated feed, independent of the manifest (used by tests)."""
    if path.suffix == ".csv":
        return sum(1 for _ in path.open(encoding="utf-8")) - 1  # minus header
    if path.suffix == ".json":
        return len(json.loads(path.read_text(encoding="utf-8")))
    root = ET.parse(path).getroot()
    return len(root.findall("part"))


def generate_feed(stem: str, fmt: str, count: int, seed: int, out_dir: Path) -> FileManifest:
    """Build one dirty feed, write it, and record its manifest entry."""
    feed_seed = seed * 100 + SPECS.index((stem, fmt, count))
    base = clean_products(feed_seed, count, stem)
    rng = random.Random(feed_seed)

    defect_counts = {
        "units": defects.inject_units(base, rng),
        "missing_required": defects.inject_missing_required(base, rng),
        "brand_variant": defects.inject_brand_variants(base, rng),
        "duplicate_sku": defects.inject_duplicate_skus(base, rng),
        "bad_numeric": defects.inject_bad_numbers(base, rng),
    }

    path = out_dir / f"{stem}.{fmt}"
    _WRITERS[fmt](path, base)
    return FileManifest(
        name=path.name,
        rows=len(base),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        defects=defect_counts,
    )


def generate_all(seed: int, out_dir: Path) -> list[FileManifest]:
    """Generate every feed. Returns the manifest entries (caller writes ``_manifest.json``)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    return [generate_feed(stem, fmt, count, seed, out_dir) for stem, fmt, count in SPECS]


def main() -> None:
    settings = get_settings()
    entries = generate_all(settings.seed, settings.raw_dir)
    manifest = write_manifest(settings.seed, entries, settings.raw_dir)
    print(f"generated {len(entries)} feeds into {settings.raw_dir}")
    for entry in entries:
        print(f"  {entry.name}: {entry.rows} rows, defects={entry.defects}")
    print(f"manifest: {manifest}")


if __name__ == "__main__":
    main()

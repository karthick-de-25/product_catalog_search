"""F01: dirty feed generation — deterministic, defective, and manifest-accurate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.generate.make_dirty_data import SPECS, count_rows, generate_all
from src.generate.manifest import write_manifest


def _file_hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.name != "_manifest.json"
    }


def test_same_seed_is_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"

    generate_all(42, first)
    generate_all(42, second)

    assert _file_hashes(first) == _file_hashes(second)
    assert len(_file_hashes(first)) == len(SPECS)


def test_different_seed_changes_output(tmp_path: Path) -> None:
    different = tmp_path / "b"

    generate_all(42, tmp_path / "a")
    generate_all(43, different)

    assert _file_hashes(tmp_path / "a") != _file_hashes(different)


def test_every_defect_kind_is_injected(tmp_path: Path) -> None:
    entries = generate_all(7, tmp_path)

    totals = {
        kind: sum(entry.defects.get(kind, 0) for entry in entries)
        for kind in ("units", "missing_required", "brand_variant", "duplicate_sku", "bad_numeric")
    }
    assert all(count > 0 for count in totals.values()), totals


def test_manifest_matches_actual_files(tmp_path: Path) -> None:
    entries = generate_all(7, tmp_path)
    write_manifest(7, entries, tmp_path)

    manifest = json.loads((tmp_path / "_manifest.json").read_text(encoding="utf-8"))

    assert manifest["seed"] == 7
    for entry in manifest["files"]:
        path = tmp_path / entry["name"]
        assert count_rows(path) == entry["rows"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

"""Defect manifest writer (F01, slice 2).

``data/raw/_manifest.json`` records the seed, per-file row counts, file hashes, and defect
counts so the quality layer (F03) can reconcile ``bronze = silver + quarantine`` and prove
defects were actually injected.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class FileManifest:
    """One generated feed in the manifest."""

    name: str
    rows: int
    sha256: str
    defects: dict[str, int]


def write_manifest(seed: int, entries: list[FileManifest], out_dir: Path) -> Path:
    """Write ``_manifest.json`` and return its path."""
    payload = {
        "seed": seed,
        "total_rows": sum(entry.rows for entry in entries),
        "files": [asdict(entry) for entry in entries],
    }
    path = out_dir / "_manifest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path

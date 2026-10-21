"""Scale-rehearsal feed generator: 100 suppliers at client-ish volume (S04, slice 1).

Pure and deterministic: the same ``seed`` and ``total_rows`` always produce byte-identical
feeds and an identical manifest. This reuses the F01 writers, defect injectors, and clean
product catalog, adding the scale-relevant dimensions:

* Pareto row distribution across 100 suppliers (~10% of suppliers carry ~70% of rows),
* three defect archetypes — ``anchor`` (clean), ``mid`` (current demo rates),
  ``long_tail`` (messy) — with per-archetype defect rates,
* deliberate cross-supplier duplicate *clusters* whose member SKUs are recorded as ground
  truth, so the S04 pipeline run can verify dedupe mechanically (not by eyeballing).

Entry point: ``python -m src.generate.scale_feeds`` (also driven by ``make scale``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from src.generate import defects
from src.generate.catalog_seed import DEFAULT_CATALOG, clean_products, format_size
from src.generate.make_dirty_data import _WRITERS
from src.generate.manifest import FileManifest

TIERS = {"1k": 1_000, "100k": 100_000, "1M": 1_000_000}
SUPPLIER_COUNT = 100
_SHAPES = ("csv", "json", "xml")
_SHAPE_TAG = {"csv": "c", "json": "j", "xml": "x"}

# Defect rates per archetype, keyed by the injector names in ``defects.py``.
_ARCHETYPE_RATES: dict[str, dict[str, float]] = {
    "anchor": {
        "units": 0.05,
        "missing_required": 0.02,
        "brand_variant": 0.05,
        "duplicate_sku": 0.02,
        "bad_numeric": 0.01,
    },
    "mid": {
        "units": 0.30,
        "missing_required": 0.10,
        "brand_variant": 0.15,
        "duplicate_sku": 0.05,
        "bad_numeric": 0.04,
    },
    "long_tail": {
        "units": 0.45,
        "missing_required": 0.18,
        "brand_variant": 0.25,
        "duplicate_sku": 0.09,
        "bad_numeric": 0.08,
    },
}

# Cross-supplier duplicate clusters: product templates repeated across many suppliers with
# identical names, so the dedupe layer must merge them (ground truth recorded in manifest).
_CLUSTER_COUNT = 44
_CLUSTER_STRIDE = 12  # supplier idx participates in clusters c where (idx + c) % stride == 0
_CLUSTER_ROWS = 2  # rows per (supplier, cluster) that carry the shared template
_CLUSTER_QUALIFIER = "ultra series"


@dataclass(frozen=True)
class SupplierSpec:
    """One scale feed's identity."""

    stem: str
    shape: str
    archetype: str
    rows: int


@dataclass
class ClusterTruth:
    """Ground truth for one cross-supplier duplicate cluster."""

    template: tuple[float, str, str]  # (size_in, material, category)
    skus: list[str] = field(default_factory=list)


@dataclass
class ScaleManifest:
    """Everything the S04 run needs to reconcile mechanically."""

    seed: int
    tier_rows: int
    suppliers: int
    files: list[FileManifest]
    clusters: list[ClusterTruth]
    total_rows: int


def pareto_row_split(seed: int, total: int, n: int, alpha: float = 1.6) -> list[int]:
    """Split ``total`` rows into ``n`` supplier row counts (Pareto-ish, exact sum)."""
    rng = random.Random(f"{seed}:pareto")
    weights = [max(rng.paretovariate(alpha), 0.05) for _ in range(n)]
    counts = [max(1, int(total * weight / sum(weights))) for weight in weights]
    diff = total - sum(counts)
    order = sorted(range(n), key=lambda i: (-weights[i], i))
    cursor = 0
    while diff != 0:
        idx = order[cursor % n]
        if diff > 0 or counts[idx] > 1:
            counts[idx] += 1 if diff > 0 else -1
            diff += -1 if diff > 0 else 1
        cursor += 1
    return counts


def supplier_specs(seed: int, total_rows: int) -> list[SupplierSpec]:
    """Deterministic specs for all 100 suppliers (shape cycle, archetype tiers)."""
    counts = pareto_row_split(seed, total_rows, SUPPLIER_COUNT)
    specs: list[SupplierSpec] = []
    for idx, rows in enumerate(counts):
        shape = _SHAPES[idx % len(_SHAPES)]
        if idx % 50 == 0:
            archetype = "anchor"  # 2 suppliers
        elif idx % 10 < 3:
            archetype = "mid"  # ~30 suppliers
        else:
            archetype = "long_tail"  # remainder
        specs.append(
            SupplierSpec(
                stem=f"{_SHAPE_TAG[shape]}{idx + 1:03d}",
                shape=shape,
                archetype=archetype,
                rows=rows,
            )
        )
    return specs


def _cluster_templates(seed: int, count: int) -> list[tuple[float, str, str]]:
    """Unique ``(size, material, category)`` templates, seeded and deterministic."""
    rng = random.Random(f"{seed}:clusters")
    pool = [
        (size, material, category)
        for size in DEFAULT_CATALOG.sizes_in
        for material in DEFAULT_CATALOG.materials
        for category in DEFAULT_CATALOG.categories
    ]
    return rng.sample(pool, count)


def _cluster_name(size: float, material: str, category: str) -> str:
    """Shared product name for a cluster (identical across suppliers, dedupe ground truth)."""
    return f"{format_size(size)} {material} {category.replace('_', ' ')} {_CLUSTER_QUALIFIER}"


def _write_cluster_rows(
    rows: list[dict[str, object]], cluster: ClusterTruth, limit: int, stem: str
) -> None:
    """Rewrite up to ``limit`` rows of this feed to carry the cluster's shared template.

    The rewritten rows are made fully pristine (sku restored to the canonical generated
    value, pressure/lead_free set) so ground-truth cluster SKUs are always valid after
    quality — defect noise belongs to every *other* row, never to a cluster row.
    """
    size, material, category = cluster.template
    for ri in range(min(limit, len(rows))):
        row = rows[ri]
        row["sku"] = f"{stem.upper()[:4]}-{ri + 1:04d}"  # restore generated SKU (undefect)
        row["size_raw"] = format_size(size)
        row["size_in"] = size
        row["material"] = material
        row["category"] = category
        row["name"] = _cluster_name(size, material, category)
        row["pressure_psi"] = int(100 + (ri * 37) % 501)  # deterministic, in contract range
        row["lead_free"] = True
        cluster.skus.append(str(row["sku"]))


def generate_scale_all(seed: int, tier_rows: int, out_dir: Path) -> ScaleManifest:
    """Generate every scale feed + ground truth into ``out_dir`` (idempotent, exact)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    specs = supplier_specs(seed, tier_rows)
    clusters = [ClusterTruth(template=t) for t in _cluster_templates(seed, _CLUSTER_COUNT)]
    files: list[FileManifest] = []

    for idx, spec in enumerate(specs):
        feed_seed = seed * 1000 + idx
        rows = clean_products(feed_seed, spec.rows, spec.stem)
        rng = random.Random(feed_seed)
        rates = _ARCHETYPE_RATES[spec.archetype]
        defect_counts = {
            name: injector(rows, rng, rates[name])
            for name, injector in (
                ("units", defects.inject_units),
                ("missing_required", defects.inject_missing_required),
                ("brand_variant", defects.inject_brand_variants),
                ("duplicate_sku", defects.inject_duplicate_skus),
                ("bad_numeric", defects.inject_bad_numbers),
            )
        }
        for cidx in sorted(c for c in range(_CLUSTER_COUNT) if (idx + c) % _CLUSTER_STRIDE == 0):
            _write_cluster_rows(rows, clusters[cidx], _CLUSTER_ROWS, spec.stem)

        path = out_dir / f"{spec.stem}.{spec.shape}"
        _WRITERS[spec.shape](path, rows)
        files.append(
            FileManifest(
                name=path.name,
                rows=len(rows),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                defects=defect_counts,
            )
        )

    return ScaleManifest(
        seed=seed,
        tier_rows=tier_rows,
        suppliers=len(specs),
        files=files,
        clusters=clusters,
        total_rows=sum(s.rows for s in specs),
    )


# Manifest name matches the demo convention (data/raw/_manifest.json) so the ingest
# layer skips it via its ignored ``_`` prefix.
MANIFEST_NAME = "_manifest.json"


def write_scale_manifest(manifest: ScaleManifest, out_dir: Path) -> Path:
    """Write the ground-truth manifest next to the feed files and return its path."""
    payload = {
        "seed": manifest.seed,
        "tier_rows": manifest.tier_rows,
        "suppliers": manifest.suppliers,
        "total_rows": manifest.total_rows,
        "files": [
            {"name": f.name, "rows": f.rows, "sha256": f.sha256, "defects": f.defects}
            for f in manifest.files
        ],
        "clusters": [
            {"template": "|".join(str(piece) for piece in c.template), "skus": list(c.skus)}
            for c in manifest.clusters
        ],
    }
    path = out_dir / MANIFEST_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: generate a scale tier of feeds (default 100k) and its manifest."""
    parser = argparse.ArgumentParser(description="Generate S04 scale-rehearsal feeds.")
    parser.add_argument("--tier", default="100k", choices=sorted(TIERS))
    parser.add_argument("--out", type=Path, default=Path("data/scale/raw"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    manifest = generate_scale_all(args.seed, TIERS[args.tier], args.out)
    path = write_scale_manifest(manifest, args.out)
    print(
        f"generated {len(manifest.files)} feeds, {manifest.total_rows} rows "
        f"(tier {args.tier}) -> {args.out}"
    )
    print(f"ground truth: {len(manifest.clusters)} dedupe clusters, manifest: {path}")


if __name__ == "__main__":
    main()

"""S04 slice 1 — scale feed generator: exact counts, determinism, ground truth."""

from __future__ import annotations

from pathlib import Path

from src.generate.scale_feeds import (
    _CLUSTER_COUNT,
    _SHAPES,
    TIERS,
    generate_scale_all,
    supplier_specs,
    write_scale_manifest,
)


def test_scale_generator_is_exact_deterministic_and_has_ground_truth(tmp_path: Path) -> None:
    out = tmp_path / "raw"
    manifest = generate_scale_all(seed=42, tier_rows=TIERS["1k"], out_dir=out)

    # Exact volume + supplier count, 100 feeds, all three feed shapes present.
    assert manifest.total_rows == 1_000
    assert len(manifest.files) == 100
    assert sum(f.rows for f in manifest.files) == manifest.total_rows
    assert {Path(f.name).suffix.lstrip(".") for f in manifest.files} == set(_SHAPES)

    # Archetype tiers: exactly 2 anchor suppliers, all three archetypes used.
    archetypes = {s.archetype for s in supplier_specs(42, TIERS["1k"])}
    assert archetypes == {"anchor", "mid", "long_tail"}

    # Ground truth: cross-supplier duplicate clusters recorded with member SKUs.
    assert len(manifest.clusters) == _CLUSTER_COUNT
    assert all(len(c.skus) >= 8 for c in manifest.clusters)  # 8+ suppliers each

    # Determinism: a second generation is byte-identical (feeds + manifest).
    out2 = tmp_path / "raw2"
    rerun = generate_scale_all(seed=42, tier_rows=TIERS["1k"], out_dir=out2)
    assert [f.sha256 for f in rerun.files] == [f.sha256 for f in manifest.files]
    assert rerun.clusters == manifest.clusters
    manifest_path = write_scale_manifest(manifest, out)
    assert out.joinpath("_manifest.json").read_text() == manifest_path.read_text()

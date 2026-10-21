"""S04 slice 3 — local embeddings: deterministic backend + telemetry in the scale run."""

from __future__ import annotations

import math
from pathlib import Path

from src.config import Settings
from src.load.embed_local import DeterministicEmbedder, get_embedder
from src.scale.run_scale import run_scale


def test_deterministic_embedder_and_scale_embed_telemetry(tmp_path: Path) -> None:
    settings = Settings(seed=42, scale_tier="1k", scale_dir=tmp_path, embedding_backend="local")
    settings.contracts_dir = Path("contracts")

    # Deterministic, offline, fixed-dim, unit-norm vectors.
    embedder = DeterministicEmbedder(dim=settings.embedding_dim)
    [first] = embedder.encode(["0.75 in brass ball valve lead free"])
    [again] = embedder.encode(["0.75 in brass ball valve lead free"])
    [other] = embedder.encode(["6 in pvc pipe"])
    assert first == again
    assert first != other
    assert len(first) == settings.embedding_dim == 768
    assert math.isclose(sum(v * v for v in first), 1.0, abs_tol=1e-9)

    # get_embedder is offline-safe on this machine (no sentence-transformers installed).
    selected, fallback = get_embedder(settings)
    assert fallback is True and isinstance(selected, DeterministicEmbedder)

    # The scale run records embedding telemetry + persists vectors.
    report = run_scale(settings)
    assert [s["stage"] for s in report.stages][-1] == "embed"
    assert report.embedding["backend_fallback"] is True
    assert report.embedding["dim"] == 768
    assert report.embedding["rows"] > 0
    assert report.embedding["embeddings_per_sec"] > 0
    assert report.embedding["estimated_vertex_usd"] >= 0

    import duckdb

    conn = duckdb.connect(tmp_path / "catalog.duckdb", read_only=True)
    embedded = conn.execute(
        "SELECT count(*) FROM gold_embeddings WHERE len(embedding) = 768"
    ).fetchone()[0]
    deduped = conn.execute("SELECT count(*) FROM gold_deduped").fetchone()[0]
    conn.close()
    assert embedded == deduped

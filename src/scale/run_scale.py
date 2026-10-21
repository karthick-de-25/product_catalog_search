"""S04 scale rehearsal: run the whole local pipeline at volume with telemetry (slice 2).

Entry point: ``make scale`` -> ``python -m src.scale.run_scale``.

Fully offline. Feeds land in ``data/scale/raw`` and the database is
``data/scale/catalog.duckdb`` — the demo DB (``data/catalog.duckdb``) is never touched.
Produces a machine-checkable ``data/scale/report.json``: per-stage wall time, the exact
``bronze = silver + quarantine`` reconciliation, and dedupe-cluster ground-truth verification.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from src.config import Settings, get_settings
from src.enrichment.dedupe import materialize_deduped
from src.enrichment.gold import materialize_gold
from src.generate.scale_feeds import (
    TIERS,
    ClusterTruth,
    generate_scale_all,
    supplier_specs,
    write_scale_manifest,
)
from src.ingest.db import connect, init_schema
from src.ingest.load_bronze import ingest_all
from src.load.embed_local import get_embedder
from src.quality.contracts import SupplierContract, load_contracts
from src.quality.validate import run_quality

REPORT_NAME = "report.json"
_EMBED_CHUNK = 2_000  # embedding rows per chunk (memory guard at 100k-tier)


@dataclass
class ScaleReport:
    """Machine-checkable outcome of one scale rehearsal."""

    schema_version: int
    seed: int
    tier_rows: int
    stages: list[dict[str, object]] = field(default_factory=list)
    reconciliation: dict[str, object] = field(default_factory=dict)
    clusters: dict[str, object] = field(default_factory=dict)
    embedding: dict[str, object] = field(default_factory=dict)


def _timed(stages: list[dict[str, object]], name: str, fn, *args, **kwargs) -> object:
    """Run ``fn`` and record its wall time into ``stages``."""
    started = time.perf_counter()
    result = fn(*args, **kwargs)
    stages.append({"stage": name, "seconds": round(time.perf_counter() - started, 4)})
    return result


def scale_contracts(
    contracts_dir: str | Path, seed: int, tier_rows: int
) -> dict[str, SupplierContract]:
    """One contract per scale supplier, reusing the 3 canonical feed shapes (S04 non-goal:
    no per-supplier contract authoring)."""
    base = load_contracts(contracts_dir)
    by_shape = {
        "csv": base["acme_valves"],
        "json": base["northwind_supply"],
        "xml": base["pacific_pipe"],
    }
    return {spec.stem: by_shape[spec.shape] for spec in supplier_specs(seed, tier_rows)}


def _load_clusters(raw_dir: Path) -> list[ClusterTruth]:
    """Rebuild the ground-truth clusters from the written manifest."""
    payload = json.loads((raw_dir / "_manifest.json").read_text(encoding="utf-8"))
    clusters: list[ClusterTruth] = []
    for entry in payload["clusters"]:
        size, material, category = entry["template"].split("|")
        clusters.append(
            ClusterTruth(template=(float(size), material, category), skus=list(entry["skus"]))
        )
    return clusters


def _verify_clusters(
    conn: duckdb.DuckDBPyConnection, clusters: list[ClusterTruth]
) -> dict[str, object]:
    """Every ground-truth cluster's SKUs must have collapsed into exactly one deduped row."""
    group_of: dict[str, int] = {}
    for row_id, (sku, merged) in enumerate(
        conn.execute("SELECT sku, merged_skus FROM gold_deduped").fetchall()
    ):
        group_of[str(sku)] = row_id
        for loser in (str(merged) or "").split(","):
            if loser.strip():
                group_of[loser.strip()] = row_id

    verified = sum(
        1
        for cluster in clusters
        if len({group_of[sku] for sku in cluster.skus if sku in group_of}) == 1
    )
    return {
        "clusters": len(clusters),
        "verified": verified,
        "ok": verified == len(clusters),
    }


def run_scale(settings: Settings) -> ScaleReport:
    """Execute generate → ingest → quality → gold → dedupe and return the report."""
    if settings.scale_tier not in TIERS:
        raise ValueError(f"unknown SCALE_TIER={settings.scale_tier!r}; choose from {sorted(TIERS)}")

    raw_dir = settings.scale_dir / "raw"
    tier_rows = TIERS[settings.scale_tier]
    run_id = f"scale-s{settings.seed}-t{tier_rows}"
    report = ScaleReport(schema_version=1, seed=settings.seed, tier_rows=tier_rows)

    # 1. generate feeds + ground-truth manifest
    def _generate() -> None:
        write_scale_manifest(generate_scale_all(settings.seed, tier_rows, raw_dir), raw_dir)

    _timed(report.stages, "generate", _generate)

    # 2. bronze ingestion (idempotent: delete-then-insert per source file)
    conn = connect(settings.scale_dir / "catalog.duckdb")
    init_schema(conn)
    loaded = _timed(report.stages, "ingest", ingest_all, conn, raw_dir)
    bronze = sum(info.rows for info in loaded)

    # 3. quality gate (bronze = silver + quarantine, enforced inside run_quality)
    _timed(
        report.stages,
        "quality",
        run_quality,
        conn,
        scale_contracts(settings.contracts_dir, settings.seed, tier_rows),
        run_id,
    )

    # 4. gold catalog
    _timed(report.stages, "gold", materialize_gold, conn)

    # 5. dedupe + ground-truth cluster verification
    _timed(report.stages, "dedupe", materialize_deduped, conn)
    silver, quarantine = conn.execute(
        "SELECT (SELECT count(*) FROM silver_products), (SELECT count(*) FROM quarantine_records)"
    ).fetchone()
    report.reconciliation = {
        "bronze": bronze,
        "silver": int(silver),
        "quarantine": int(quarantine),
        "exact": bronze == int(silver) + int(quarantine),
    }
    report.clusters = _verify_clusters(conn, _load_clusters(raw_dir))

    # 6. local embeddings over gold_deduped.search_text + Vertex cost dry-run
    #    (chunked so both encode() and the insert stay memory-bounded at 100k)
    embedder, backend_fallback = get_embedder(settings)
    texts = conn.execute(
        "SELECT sku, search_text FROM gold_deduped WHERE search_text IS NOT NULL"
    ).fetchall()
    started = time.perf_counter()
    conn.execute("DROP TABLE IF EXISTS gold_embeddings")
    conn.execute("CREATE TABLE gold_embeddings (sku TEXT, embedding DOUBLE[])")
    for start in range(0, len(texts), _EMBED_CHUNK):
        chunk = texts[start : start + _EMBED_CHUNK]
        vectors = embedder.encode([text for _, text in chunk])
        conn.executemany(
            "INSERT INTO gold_embeddings VALUES (?, ?)",
            [(sku, vector) for (sku, _), vector in zip(chunk, vectors)],
        )
    embed_seconds = round(time.perf_counter() - started, 4)
    report.stages.append({"stage": "embed", "seconds": embed_seconds})
    report.embedding = {
        "backend": settings.embedding_backend,
        "backend_fallback": backend_fallback,
        "dim": settings.embedding_dim,
        "rows": len(texts),
        "embeddings_per_sec": round(len(texts) / embed_seconds, 1) if embed_seconds else 0.0,
        "estimated_vertex_usd": round(
            len(texts) / 1000 * settings.vertex_embedding_cost_usd_per_1k_rows, 4
        ),
    }
    conn.close()

    (settings.scale_dir / REPORT_NAME).write_text(
        json.dumps(
            {
                "schema_version": report.schema_version,
                "seed": report.seed,
                "tier": settings.scale_tier,
                "tier_rows": report.tier_rows,
                "stages": report.stages,
                "reconciliation": report.reconciliation,
                "clusters": report.clusters,
                "embedding": report.embedding,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return report


def main() -> None:
    """CLI entry point (wired to ``make scale``)."""
    settings = get_settings()
    report = run_scale(settings)
    print(f"scale rehearsal complete: tier={settings.scale_tier} seed={report.seed}")
    for stage in report.stages:
        print(f"  {stage['stage']:10s} {stage['seconds']:8.3f}s")
    print(f"  reconciliation: {report.reconciliation}")
    print(f"  clusters: {report.clusters}")
    print(f"  embedding: {report.embedding}")
    print(f"  report: {settings.scale_dir / REPORT_NAME}")


if __name__ == "__main__":
    main()

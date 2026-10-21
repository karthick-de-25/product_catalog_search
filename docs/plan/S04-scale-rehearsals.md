---
feature: S04
title: Scale rehearsals (make scale) — 100-supplier, 100k-tier, offline with local embeddings
status: done
approved: 2026-10-22
depends_on: [F01, F02, F03, F04, O03]
---

# S04 — Scale rehearsals

**Goal:** prove the local pipeline (generate → ingest → quality → gold → dedupe → embed) at
client-ish volume — 100 suppliers, default 100k rows, fully offline — with a machine-checkable
manifest of ground truth and per-stage telemetry so S01/S02/S05/S06 have before/after numbers.
**Non-goals:** no AlloyDB/Vertex in this feature (local embeddings only, `EMBEDDING_BACKEND=local`);
no per-supplier contract authoring (reuses the 3 canonical contract shapes); 1M is an optional
XL tier, not the default.

## Slices (≤3)

### Slice 1 — Scale feed generator (100 suppliers, Pareto, archetypes, ground truth)   `[x]`
- **In → out:** `(seed, tier_rows)` → `data/scale/raw/` (100 feeds across csv/json/xml shapes and
  anchor/mid/long-tail defect archetypes) + `data/scale/manifest.json` (per-file rows, sha256,
  defect counts, ground-truth cross-supplier dedupe clusters).
- **Files:** `src/generate/scale_feeds.py`, `tests/test_scale_feeds.py`
- **Test:** TIER=1k into a tmp dir → exactly 100 files, exactly 1000 rows total, manifest
  reconciles, rerun is byte-identical (determinism).
- **Critical actions:** `none`
- **Done when:** `python -m src.generate.scale_feeds` CLI writes 100 feeds + manifest; counts exact.

### Slice 2 — Offline pipeline run + telemetry (`make scale`)   `[x]`
- **In → out:** scale raw dir → `data/scale/catalog.duckdb` (bronze/silver/quarantine/gold/
  gold_deduped) + `data/scale/report.json` (per-stage seconds, `bronze = silver + quarantine`
  reconciliation, dedupe-cluster ground-truth verification).
- **Files:** `src/scale/run_scale.py`, `src/config.py` (`scale_dir`, `scale_tier`), `Makefile`
  (`scale` target), `tests/test_scale_run.py`
- **Test:** TIER=1k end-to-end → reconciliation exact, report contains all stages with timings,
  every ground-truth cluster collapsed to one deduped row.
- **Critical actions:** `none` (local only; the chosen DB is `data/scale/`, never the demo DB)
- **Done when:** `make scale` runs the full 1k path green; `make scale` defaults to 100k.

### Slice 3 — Local embeddings + Vertex cost telemetry   `[x]`
- **In → out:** `gold_deduped.search_text` → `gold_embeddings` table (768-d) in the scale DB;
  embeddings/sec and estimated Vertex AI $ in `report.json`.
- **Files:** `src/load/embed_local.py` (DeterministicEmbedder for offline CI + lazy
  SentenceTransformerEmbedder), `src/config.py` (backend/model/dim/cost-per-1k rows),
  `requirements.txt`, `.env.example`, `tests/test_embed_local.py`
- **Test:** deterministic 768-d embedder returns same vector for same text, distinct for
  different text; scale run records `embeddings_per_sec` and `estimated_vertex_usd` in the report.
- **Critical actions:** 🔴 new runtime dependency `sentence-transformers` (pulls torch, ~2 GB
  install) — **approved by human 2026-10-22** (S04 kickoff). Without it installed, `make scale`
  falls back to deterministic vectors **loudly** (WARNING + `backend_fallback: true` in report).
- **Done when:** report shows embedding speed + cost estimate; 1k CI path green with no network.

## Acceptance (feature-level)
- [x] `make scale` (100k default, offline) runs generate → ingest → quality → gold → dedupe → embed
- [x] report.json is machine-checkable (stages, reconciliation, cluster verification, embed telemetry)
- [x] `make check` green with 39 tests (3 new)

## Commands
```bash
make check
make scale                # 100k default
make scale TIER=1k        # fast CI-friendly rehearsal
make scale TIER=1M        # optional XL tier
```

## Log
- 2026-10-22 — plan created; human pre-approved S04 and the sentence-transformers dependency
  ("approve and imp S04"); 100k default tier + local embeddings locked in per discussion.
- 2026-10-22 — slice 1 done: 100 feeds / exact rows / archetypes / cluster ground truth;
  manifest named ``_manifest.json`` so the ingest layer ignores it. Tests: 37 green.
- 2026-10-22 — slice 2 done: ``make scale`` runs the offline pipeline (1k → 100k) into
  ``data/scale/`` with exact reconciliation + cluster verification + report.json. Tests: 38 green.
- 2026-10-22 — slice 3 done: local embeddings (deterministic fallback + lazy
  sentence-transformers), ``gold_embeddings`` table, embeddings/sec + Vertex cost dry-run in
  the report; ``requirements.txt`` +sentence-transformers (approved). Tests: 39 green.
- 2026-10-22 — feature done: ``make scale`` end-to-end verified at 100k; critical approval:
  sentence-transformers dependency.
- 2026-10-22 — **S04 findings (amendment, within plan acceptance):** the 100k rehearsal
  exposed two demo-scale performance defects that made the pipeline stall (~44 rows/s):
  (1) per-row ``conn.execute`` inserts in quality/gold/dedupe and loop-back ``executemany``
  in ingest — replaced with ``conn.append(pd.DataFrame)`` bulk writes (~1000x faster;
  identical tables/rows/invariants, no API change); (2) ground-truth cluster rows could carry
  defect mutations (injected SKU copies / ``'high'`` pressure) — cluster overlay now restores
  fully pristine rows so verification is exact at 100k. Result: 100k run 30.8s,
  100000 = 76201 silver + 23799 quarantine, 44/44 clusters verified.
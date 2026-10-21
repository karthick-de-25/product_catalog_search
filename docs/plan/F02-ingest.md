---
feature: F02
title: Bronze ingestion
status: done
approved: 2026-10-21
depends_on: [F01]
---

# F02 — Bronze ingestion

**Goal:** load every raw feed into one DuckDB `bronze_records` table, preserving the original row,
so the quality layer has a single immutable input.

**Non-goals:** cleaning, validation, quarantine (F03), normalization (F04). Bronze is untouched raw.

## Slices

### Slice 1 — Bronze schema + loaders   `[x]`
- **In → out:** `data/raw/**` → `data/catalog.duckdb` `bronze_records`
- **Files:** `src/ingest/{db.py,load_bronze.py}`, `tests/test_ingest.py`
- **Schema:** `run_id, supplier_id, source_file, source_format, row_index, raw_payload JSON`,
  plus permissive `raw_*` text columns (values exactly as delivered).
- **Test:** `test_ingest.py::test_bronze_counts_match_manifest` + `test_raw_payload_round_trips`
- **Critical actions:** none
- **Done when:** loading is idempotent (re-running does not duplicate rows) — verified by
  `test_ingest_is_idempotent`.

### Slice 2 — `make ingest`   `[x]`
- **In → out:** `make ingest` → prints per-file loaded counts
- **Files:** `Makefile`, `README.md`
- **Test:** covered by Slice 1's tests.
- **Critical actions:** none
- **Done when:** `make ingest` runs after `make data` and exits 0.

## Acceptance
- [x] `make data && make ingest` loads all feeds; counts reconcile with the manifest.
- [x] No parsing/typing of values in bronze (all text/JSON).

## Commands
```bash
make data && make ingest
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.
- 2026-10-21 — plan approved by human.
- 2026-10-21 — slice 1: `src/ingest/{db,load_bronze}.py` — idempotent `bronze_records` loader
  (CSV/JSON/XML flatteners, raw_payload preserved verbatim); fixed `.csv`-suffix filter bug.
- 2026-10-21 — slice 2: `make ingest` target; `make data && make ingest` loads 240 rows
  reconciling with the manifest; DuckDB returns JSON columns as text so the round-trip test
  parses with `json.loads`. F02 done.

---
feature: F02
title: Bronze ingestion
status: proposed
approved:
depends_on: [F01]
---

# F02 — Bronze ingestion

**Goal:** load every raw feed into one DuckDB `bronze_records` table, preserving the original row,
so the quality layer has a single immutable input.

**Non-goals:** cleaning, validation, quarantine (F03), normalization (F04). Bronze is untouched raw.

## Slices

### Slice 1 — Bronze schema + loaders   `[ ]`
- **In → out:** `data/raw/**` → `data/catalog.duckdb` `bronze_records`
- **Files:** `src/ingest/{db.py,load_bronze.py}`, `tests/test_ingest.py`
- **Schema:** `run_id, supplier_id, source_file, source_format, row_index, raw_payload JSON`,
  plus permissive `raw_*` text columns (values exactly as delivered).
- **Test:** `test_ingest.py::test_bronze_matches_manifest` — for each file, bronze row count
  equals the F01 manifest count; `raw_payload` round-trips one row per format.
- **Critical actions:** none
- **Done when:** loading is idempotent (re-running does not duplicate rows).

### Slice 2 — `make ingest`   `[ ]`
- **In → out:** `make ingest` → prints per-file loaded counts
- **Files:** `Makefile`, `README.md`
- **Test:** covered by Slice 1's test.
- **Critical actions:** none
- **Done when:** `make ingest` runs after `make data` and exits 0.

## Acceptance
- [ ] `make data && make ingest` loads all feeds; counts reconcile with the manifest.
- [ ] No parsing/typing of values in bronze (all text/JSON).

## Commands
```bash
make data && make ingest
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.

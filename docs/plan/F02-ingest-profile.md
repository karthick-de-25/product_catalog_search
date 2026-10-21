---
feature: F02
title: Bronze ingestion & profiling
status: proposed
owner: agent
approved:
created: 2026-10-21
updated: 2026-10-21
depends_on: [F01]
---

# F02 — Bronze ingestion & profiling

## Goal
Load every raw supplier feed into a single DuckDB **bronze** table without losing or altering a
single byte, then profile it so we know exactly how dirty it is before we try to clean it.

## Why now
Bronze is the immutable source of truth and the input to all quality work. Profiling turns
vague "the data is messy" into numbers we can track (and later prove the enrichment lift).

## Scope
- In scope: DuckDB connection/artifact, `bronze_records` schema preserving `raw_payload`,
  CSV/JSON/XML flatteners to a common envelope, profiling report, `make ingest`/`make profile`,
  reconciliation against `data/raw/_manifest.json`.
- Non-goals: validation, contracts, quarantine, normalization, dedupe (F03+). **Bronze is not
  cleaned here.**

## Assumptions
- [ ] `data/raw/_manifest.json` from F01 has stable `rows` counts per file — verify shape.
- [ ] `duckdb`, `pandas`, `pyarrow` installed — verify import.
- [ ] DuckDB file lives at `data/catalog.duckdb` (git-ignored) — verify `.gitignore`.

## Open questions (needs human)
- none

## Acceptance criteria (feature-level)
- [ ] AC1: `make ingest` loads all feeds into `bronze_records`, idempotently (re-running does
      not duplicate rows — truncate-and-reload by `source_file`, or a run-scoped table).
- [ ] AC2: `bronze_records` count per file equals `_manifest.json` `rows` exactly.
- [ ] AC3: `raw_payload` round-trips the original record (JSON/XML parse-back equals source).
- [ ] AC4: `make profile` writes `data/reports/profile_<run>.md` + `.csv` with null rate,
      distinct count, and top values per column, plus units/brand-variant samples.
- [ ] AC5: Profiling makes no cloud calls and needs no credentials.

---

## Slices

### Slice 1 — DuckDB connection & bronze schema
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** none
- **Outputs:** `src/ingest/db.py` (`connect()`, `init_schema()`), `bronze_records` table
- **Files:** `src/ingest/__init__.py`, `src/ingest/db.py`, `tests/ingest/test_db.py`
- **Acceptance criteria:**
  - [ ] `connect()` returns a DuckDB connection at `data/catalog.duckdb` (path from config).
  - [ ] `bronze_records` columns: `run_id`, `supplier_id`, `source_file`, `source_format`,
        `row_index`, `raw_payload JSON`, `ingested_at`, and a permissive set of `raw_*` text
        columns (values exactly as delivered, no parsing).
  - [ ] `init_schema()` is idempotent (`CREATE TABLE IF NOT EXISTS`).
  - [ ] Schema DDL is asserted in a test (column names/types).
- **Test:** `tests/ingest/test_db.py::test_schema_idempotent`
- **Tier C actions:** none
- **Notes:** Do not type-cast values here — everything is text/JSON in bronze.

### Slice 2 — Feed loaders (CSV / JSON / XML)
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** `data/raw/**`
- **Outputs:** `src/ingest/load_bronze.py` with per-format loaders
- **Files:** `src/ingest/load_bronze.py`, `tests/ingest/test_load_bronze.py`
- **Acceptance criteria:**
  - [ ] CSV: header row → `raw_*` columns verbatim.
  - [ ] JSON: nested records kept whole in `raw_payload`; known keys also flattened to `raw_*`.
  - [ ] XML: elements and attributes both captured; the supplier's `partNo` is preserved
        verbatim (no renaming to `sku`).
  - [ ] `row_index` is stable and zero-based within each file.
  - [ ] A `run_id` (uuid or timestamp from injected clock) tags every row of one ingest run.
- **Test:** `tests/ingest/test_load_bronze.py::test_roundtrip_raw_payload` — parse `raw_payload`
  back and compare to the source record for one row per format.
- **Tier C actions:** none
- **Notes:** Loader must tolerate a file with zero rows without crashing.

### Slice 3 — Profiling report
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** `bronze_records`
- **Outputs:** `src/quality/profile.py`, `data/reports/profile_<run>.{md,csv}`
- **Files:** `src/quality/__init__.py`, `src/quality/profile.py`, `tests/quality/test_profile.py`
- **Acceptance criteria:**
  - [ ] Per column: null rate, distinct count, min/max, top-10 values with counts.
  - [ ] Detects and reports unit-format variety (e.g. how many `"`, `in`, `mm` forms).
  - [ ] Detects brand-variant clusters (case/spacing/`Inc.` variants) without "fixing" them.
  - [ ] Report is deterministic for a fixed input (sorted output).
- **Test:** `tests/quality/test_profile.py::test_report_columns_and_determinism`
- **Tier C actions:** none
- **Notes:** `ydata-profiling` is optional sugar; the core report must work from plain DuckDB SQL
  so it stays fast and deterministic.

### Slice 4 — `make ingest` / `make profile` + reconciliation
- **Status:** `[ ]`
- **Tier:** 🟡
- **Inputs:** Slices 1–3
- **Outputs:** Makefile targets; reconciliation test; docs
- **Files:** `Makefile`, `tests/ingest/test_reconciliation.py`, `docs/plan/ROADMAP.md`
- **Acceptance criteria:**
  - [ ] `make ingest` runs load for all feeds and prints per-file loaded counts.
  - [ ] `make profile` depends on `make ingest` and prints the report path.
  - [ ] Reconciliation test: for each file, `bronze_records` count == `_manifest.json` rows.
  - [ ] Re-running `make ingest` is idempotent (AC1) — asserted.
- **Test:** `tests/ingest/test_reconciliation.py::test_bronze_matches_manifest`
- **Tier C actions:** none
- **Notes:** Idempotency policy: delete rows for the `source_file` being loaded, or use a fresh
  `run_id` and query the latest. Pick one and document it in the plan log.

---

## Commands
```bash
make data        # ensure inputs exist
make ingest
make profile
pytest -q tests/ingest tests/quality
make check
```

## Risks
- JSON/XML shape surprises → flatteners stay permissive; unknown keys go to `raw_payload` only.
- DuckDB file bloat/locking → single connection context manager; close on exit.
- Idempotency ambiguity → decide and document in Slice 4 notes.

## Rollback
Delete `data/catalog.duckdb`, `data/reports/`, `src/ingest/`, `src/quality/`, `tests/ingest/`,
`tests/quality/`, and the two Makefile targets. No cloud.

---

## Log
- 2026-10-21 — plan created (proposed).

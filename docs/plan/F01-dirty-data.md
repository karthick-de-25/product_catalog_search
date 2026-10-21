---
feature: F01
title: Synthetic dirty supplier feeds
status: done
approved: 2026-10-21
depends_on: [F00]
---

# F01 — Synthetic dirty supplier feeds

**Goal:** a seeded generator that writes realistic dirty supplier feeds (3 suppliers, 3 formats)
to `data/raw/` so the quality layer has something to fight.

**Non-goals:** real data, PDFs/LLM extraction, loading into DuckDB (F02), cleaning.

## Slices

### Slice 1 — Generator core (`make data`)   `[x]`
- **In → out:** `SEED` → `data/raw/{acme_valves.csv, northwind_supply.json, pacific_pipe.xml}`
- **Files:** `src/generate/{catalog_seed.py,make_dirty_data.py,defects.py}`, `tests/test_generate.py`,
  `Makefile`
- **Test:** `test_generate.py::test_same_seed_is_byte_identical` + `test_every_defect_kind_is_injected`
- **Defects to inject (keep it small):** mixed units (`3/4"`, `0.75 in`, `19 mm`), missing
  required fields, brand variants (`Watts`/`WATTS Inc.`), duplicate SKUs, a few bad numbers.
- **Critical actions:** none
- **Done when:** `make data` regenerates files; the tests pass.

### Slice 2 — Defect manifest   `[x]`
- **In → out:** generated files → `data/raw/_manifest.json` with per-file row counts + defect counts
- **Files:** `src/generate/manifest.py`, `tests/test_generate.py` (extend)
- **Test:** `test_generate.py::test_manifest_matches_actual_files` — manifest row counts and
  hashes equal the actual files.
- **Critical actions:** none
- **Done when:** `make data` writes the manifest; F02 can read it.

## Acceptance
- [x] `make data` produces 3 files + `_manifest.json`, reproducibly for a fixed seed.
- [x] All listed defect kinds appear at a configured rate.

## Commands
```bash
make data
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.
- 2026-10-21 — plan approved by human.
- 2026-10-21 — slice 1: `src/generate/{catalog_seed,defects,make_dirty_data}.py` + `make data`;
  deterministic across runs; all five defect kinds injected (units/missing/brand/dupe/bad)
  at configured rates; 9 tests green.
- 2026-10-21 — slice 2: `src/generate/manifest.py` wired into `make data`; `_manifest.json`
  records seed, per-file rows, sha256, and defect counts; manifest test verifies counts/hashes.
  Fixed XML writer bug (pressure key) found during sample inspection. F01 done.

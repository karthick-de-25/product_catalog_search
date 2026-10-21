---
feature: F01
title: Synthetic dirty supplier feeds
status: proposed
approved:
depends_on: [F00]
---

# F01 — Synthetic dirty supplier feeds

**Goal:** a seeded generator that writes realistic dirty supplier feeds (3 suppliers, 3 formats)
to `data/raw/` so the quality layer has something to fight.

**Non-goals:** real data, PDFs/LLM extraction, loading into DuckDB (F02), cleaning.

## Slices

### Slice 1 — Generator core (`make data`)   `[ ]`
- **In → out:** `SEED` → `data/raw/{acme_valves.csv, northwind_supply.json, pacific_pipe.xml}`
- **Files:** `src/generate/{catalog_seed.py,make_dirty_data.py,defects.py}`, `tests/test_generate.py`
- **Test:** `test_generate.py::test_deterministic_and_dirty` — same seed twice gives identical
  files; the expected defect kinds are present.
- **Defects to inject (keep it small):** mixed units (`3/4"`, `0.75 in`, `19 mm`), missing
  required fields, brand variants (`Watts`/`WATTS Inc.`), duplicate SKUs, a few bad numbers.
- **Critical actions:** none
- **Done when:** `make data` regenerates files; the test passes.

### Slice 2 — Defect manifest   `[ ]`
- **In → out:** generated files → `data/raw/_manifest.json` with per-file row counts + defect counts
- **Files:** `src/generate/manifest.py`, `tests/test_generate.py` (extend)
- **Test:** manifest row counts equal the actual file row counts.
- **Critical actions:** none
- **Done when:** `make data` writes the manifest; F02 can read it.

## Acceptance
- [ ] `make data` produces 3 files + `_manifest.json`, reproducibly for a fixed seed.
- [ ] All listed defect kinds appear at a configured rate.

## Commands
```bash
make data
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.

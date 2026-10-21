---
feature: F01
title: Synthetic dirty supplier feeds
status: proposed
owner: agent
approved:
created: 2026-10-21
updated: 2026-10-21
depends_on: [F00]
---

# F01 — Synthetic dirty supplier feeds

## Goal
A seeded generator that writes realistic, deliberately dirty supplier feeds in CSV, JSON, and
XML to `data/raw/`, plus a manifest of every injected defect — so the quality layer has
something honest to fight against.

## Why now
Nothing downstream is testable without realistic dirty input. The manifest turns "we made
messy data" into measurable assertions for F03/F04.

## Scope
- In scope: a small but representative PVF/HVAC/plumbing catalog (~5–10k rows), 3 suppliers with
  different formats and defect profiles, deterministic seeding, a defect manifest, `make data`.
- Non-goals: real supplier data, PDF/text spec sheets (F06/F13), loading into DuckDB (F02),
  any cleaning.

## Assumptions
- [ ] `faker` and `pyarrow`/`pandas` are in `requirements.txt` — verify install.
- [ ] ~10k rows is fast (<10s) and small (<5 MB) enough to regenerate per test — verify timing.

## Open questions (needs human)
- none

## Acceptance criteria (feature-level)
- [ ] AC1: `make data` regenerates byte-identical files for a fixed `SEED`.
- [ ] AC2: Three suppliers, three formats: CSV (`acme_valves`), JSON (`northwind_supply`),
      XML (`pacific_pipe`), each with its own column names/schema quirks.
- [ ] AC3: Every defect category appears at a known, configured rate: inconsistent units,
      missing required fields, brand variants, near-duplicate SKUs/products, wrong/missing
      category, malformed numerics.
- [ ] AC4: `data/raw/_manifest.json` records per-file row counts and per-defect counts.
- [ ] AC5: Re-running with a different seed produces different data (proves the seed matters).

---

## Slices

### Slice 1 — Generator core & catalog seed
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** `SEED` from config
- **Outputs:** taxonomy + a clean canonical product generator
- **Files:** `src/generate/__init__.py`, `src/generate/catalog_seed.py`
- **Acceptance criteria:**
  - [ ] `catalog_seed.py` defines controlled vocabularies: categories, brands (+aliases),
        materials, connection types, certifications, size/psi ranges.
  - [ ] `generate_clean_products(seed, n) -> pd.DataFrame` is deterministic for a fixed seed.
  - [ ] SKUs are unique and regex-valid in the clean base.
- **Test:** `tests/generate/test_catalog_seed.py::test_determinism` — two calls, equal frames.
- **Tier C actions:** none
- **Notes:** Keep vocabularies realistic; they become the ground truth for F05 normalizers.

### Slice 2 — CSV feed (`acme_valves`)
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** clean base from Slice 1
- **Outputs:** `data/raw/acme_valves/acme_valves.csv` with injected defects
- **Files:** `src/generate/make_dirty_data.py`, `src/generate/defects.py`
- **Acceptance criteria:**
  - [ ] Defect functions are pure and configurable by rate: `units`, `missing_required`,
        `brand_variant`, `bad_numeric`, `missing_category`.
  - [ ] Units appear as mixtures: `3/4"`, `0.75 in`, `19 mm`, `3/4 inch`.
  - [ ] Brand variants appear: `Watts`, `WATTS Inc.`, `watts`.
  - [ ] Output CSV uses the supplier's own (non-canonical) column names.
- **Test:** `tests/generate/test_make_dirty_data.py::test_csv_defects_present` — asserts each
  configured defect appears with count within tolerance.
- **Tier C actions:** none
- **Notes:** Rates live in config, not hard-coded.

### Slice 3 — JSON + XML feeds
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** clean base
- **Outputs:** `data/raw/northwind_supply/northwind_supply.json` (nested, semi-structured);
  `data/raw/pacific_pipe/pacific_pipe.xml` (attribute-heavy)
- **Files:** `src/generate/make_dirty_data.py` (extend)
- **Acceptance criteria:**
  - [ ] JSON nests attributes under an `attributes` object and varies key casing.
  - [ ] XML encodes fields as elements *and* attributes, with a non-`sku` id field
        (e.g. `partNo`) to force mapping work in F02.
  - [ ] Each format carries its own defect profile.
- **Test:** `tests/generate/test_make_dirty_data.py::test_json_and_xml_shapes` — parse back
  and assert the quirks exist.
- **Tier C actions:** none
- **Notes:** These quirks are the reason F02 flattening exists — don't normalize them here.

### Slice 4 — Defect manifest & determinism
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** outputs of Slices 2–3
- **Outputs:** `data/raw/_manifest.json`
- **Files:** `src/generate/manifest.py`, `tests/generate/test_manifest.py`
- **Acceptance criteria:**
  - [ ] Manifest records `seed`, generated-at (from an injected clock, not `now()` in tests),
        per-file `rows`, file `sha256`, and per-defect counts.
  - [ ] Manifest row counts equal the actual file row counts.
  - [ ] Same seed → identical file hashes; different seed → different hashes.
- **Test:** `tests/generate/test_manifest.py::test_reproducible_and_seed_sensitive`
- **Tier C actions:** none
- **Notes:** F02's reconciliation test reads this manifest — keep the schema stable.

### Slice 5 — `make data` target & docs
- **Status:** `[ ]`
- **Tier:** 🟡
- **Inputs:** Slices 1–4
- **Outputs:** `make data`; docs updated
- **Files:** `Makefile`, `README.md`, `docs/plan/F01-dirty-data.md`, `docs/plan/ROADMAP.md`
- **Acceptance criteria:**
  - [ ] `make data` cleans `data/raw/` then regenerates everything and prints a summary table.
  - [ ] README documents the three feeds and how to change the seed.
  - [ ] Plan slices ticked; ROADMAP F01 → `done` after `/skill:verify F01`.
- **Test:** `make data && pytest -q tests/generate` green.
- **Tier C actions:** none
- **Notes:** `make data` must be safe to run repeatedly.

---

## Commands
```bash
make data
pytest -q tests/generate
make check
```

## Risks
- Defect rates too low → quality layer looks trivial. Mitigation: assert counts within tolerance.
- "Realistic" data bloats → cap at ~10k rows and keep files <5 MB.
- Manifest schema churn breaks F02. Mitigation: treat `_manifest.json` schema as a contract.

## Rollback
Delete `src/generate/`, `tests/generate/`, `data/raw/`, and the `data` Makefile target. No cloud.

---

## Log
- 2026-10-21 — plan created (proposed).

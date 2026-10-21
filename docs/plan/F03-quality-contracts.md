---
feature: F03
title: Data contracts, validation & quarantine
status: proposed
owner: agent
approved:
created: 2026-10-21
updated: 2026-10-21
depends_on: [F02]
---

# F03 — Data contracts, validation & quarantine

## Goal
Declare each supplier feed's expectations in a YAML **data contract**, validate every bronze
row against it, materialize the survivors into **silver**, and quarantine the rest with a
`reason_code` — never silently dropping a row.

## Why now
This is the project's quality backbone: it enforces `CONTEXT.md` invariants 1, 2, and the
closed `ReasonCode` set, and produces the clean input that enrichment needs.

## Scope
- In scope: contract schema + loaders, rule engine, quarantine table, silver materialization,
  reconciliation, `make quality`.
- Non-goals: scorecards/trends (F04), normalization/unit conversion (F05 — a row with an
  unparseable unit is quarantined here, not repaired), dedupe (F07).

## Assumptions
- [ ] Bronze row counts reconcile with `_manifest.json` (F02 AC2) — verify.
- [ ] `pandera` and `pydantic`/`pyyaml` installed — verify import.
- [ ] `ReasonCode` in `src/errors.py` already matches `CONTEXT.md` (F00 AC3).

## Open questions (needs human)
- none

## Acceptance criteria (feature-level)
- [ ] AC1: `contracts/supplier_contract.yaml` declares required fields, types, ranges, allowed
      values, unit expectations, and thresholds for each supplier.
- [ ] AC2: Every bronze row is either in silver or in quarantine — asserted by reconciliation
      `bronze = silver + quarantine` (exact, per run).
- [ ] AC3: Each quarantined row records exactly one primary `ReasonCode` from the closed set,
      the field at fault, and the original `raw_payload`.
- [ ] AC4: The rule engine emits only codes defined in `CONTEXT.md`; a test guards drift.
- [ ] AC5: `make quality` is idempotent and needs no credentials/network.

---

## Slices

### Slice 1 — Contract model & loader
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** `contracts/supplier_contract.yaml`
- **Outputs:** `src/quality/contracts.py` (pydantic `DataContract`, `load_contract()`,
  `load_all_contracts()`), the YAML itself
- **Files:** `contracts/supplier_contract.yaml`, `src/quality/contracts.py`,
  `tests/quality/test_contracts.py`
- **Acceptance criteria:**
  - [ ] One contract entry per supplier, keyed by `supplier_id`, matching F01's three feeds.
  - [ ] Declares: `required`, per-field `type`/`min`/`max`/`allowed`/`unit`,
        and `thresholds: {completeness_min, duplicate_rate_max}`.
  - [ ] Invalid contract (unknown field type, missing `required`) raises `ContractError`
        with the offending path.
  - [ ] Contracts are loaded from the repo root regardless of cwd (path from `src/config.py`).
- **Test:** `tests/quality/test_contracts.py::test_load_and_reject_invalid`
- **Tier C actions:** none
- **Notes:** The contract is the single place thresholds live — do not duplicate numbers in code.

### Slice 2 — Rule engine emitting reason codes
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** a bronze row + its contract
- **Outputs:** `src/quality/rules.py` — pure functions `check_required`, `check_type`,
  `check_range`, `check_enum`, `check_unit_parseable`, `check_duplicate_sku`
- **Files:** `src/quality/rules.py`, `src/quality/reason_codes.py`, `tests/quality/test_rules.py`
- **Acceptance criteria:**
  - [ ] Each rule returns pass or a `Finding(reason_code, field, detail)`.
  - [ ] Rules are pure and independently unit-tested against tiny in-memory rows.
  - [ ] `MISSING_REQUIRED`, `TYPE_MISMATCH`, `OUT_OF_RANGE`, `INVALID_ENUM`,
        `UNIT_UNPARSEABLE`, `DUPLICATE_SKU` are all exercised.
  - [ ] Primary-code policy is deterministic (documented priority order, e.g. missing > type >
        range > enum > unit > duplicate).
- **Test:** `tests/quality/test_rules.py` — one test per reason code.
- **Tier C actions:** none
- **Notes:** Unit *parsing* beyond detectability belongs to F05; here `"3/4\"` is valid, `"banana"`
  is `UNIT_UNPARSEABLE`.

### Slice 3 — Validation + quarantine materialization
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** `bronze_records` + contracts
- **Outputs:** `src/quality/validate.py`, `quarantine_records` table
- **Files:** `src/quality/validate.py`, `tests/quality/test_validate.py`
- **Acceptance criteria:**
  - [ ] `quarantine_records`: `run_id`, `supplier_id`, `sku`, `field`, `reason_code`,
        `detail`, `raw_payload JSON`, `quarantined_at`.
  - [ ] Validation is idempotent for a `run_id` (delete-then-insert by run).
  - [ ] Reconciliation holds exactly: `bronze_count = silver_count + quarantine_count`.
  - [ ] A row with multiple failures keeps the primary code and logs the others in `detail`.
- **Test:** `tests/quality/test_validate.py::test_reconciliation_exact`
- **Tier C actions:** none
- **Notes:** `BROKEN_REFERENCE` (category/brand not in taxonomy) is emitted here using the
  vocabulary from `src/generate/catalog_seed.py`. `LOW_CONFIDENCE` belongs to F06.

### Slice 4 — Silver materialization
- **Status:** `[ ]`
- **Tier:** 🟢
- **Inputs:** rows that passed validation
- **Outputs:** `src/quality/silver.py`, `silver_products` table
- **Files:** `src/quality/silver.py`, `tests/quality/test_silver.py`
- **Acceptance criteria:**
  - [ ] Silver carries a canonical-but-unenriched shape: `sku`, `supplier_id`, `name`,
        `brand_raw`, `category_raw`, `size_raw`, `pressure_raw`, `material_raw`,
        `lead_free_raw`, `certifications_raw`, plus `run_id` and `source_file`.
  - [ ] Values are trimmed/typed but **not** canonicalized (that is F05).
  - [ ] No silver row exists for a quarantined source row and vice-versa.
- **Test:** `tests/quality/test_silver.py::test_no_overlap_and_typed`
- **Tier C actions:** none
- **Notes:** `raw_*` naming convention from `CONTEXT.md` invariant 4.

### Slice 5 — `make quality` + broken-fixture suite
- **Status:** `[ ]`
- **Tier:** 🟡
- **Inputs:** Slices 1–4
- **Outputs:** Makefile target, docs, broken fixtures
- **Files:** `Makefile`, `tests/fixtures/broken/` , `tests/quality/test_end_to_end.py`,
  `docs/plan/ROADMAP.md`
- **Acceptance criteria:**
  - [ ] `make quality` runs profile → validate → silver → quarantine and prints counts.
  - [ ] `tests/fixtures/broken/` contains one hand-written row per reason code.
  - [ ] End-to-end test runs against real F01 output and asserts AC2 reconciliation.
  - [ ] Running `make quality` twice yields identical counts (idempotent).
- **Test:** `tests/quality/test_end_to_end.py::test_quality_codes_and_reconciliation`
- **Tier C actions:** none
- **Notes:** Update ROADMAP F03 → `done` only after `/skill:verify F03` passes.

---

## Commands
```bash
make data && make ingest
make quality
pytest -q tests/quality
make check
```

## Risks
- Ambiguous primary reason code → define and test the priority order in Slice 2.
- Contracts drift from F01's schema → a test loads F01 output and validates every column is
  covered by the contract (unknown columns warn, not fail).
- Over-strict contracts quarantine everything → tune rates to the manifest's known defect counts.

## Rollback
Drop `quarantine_records` and `silver_products`; delete `src/quality/{contracts,rules,validate,silver}.py`,
`contracts/`, and the `quality` Makefile target. No cloud.

---

## Log
- 2026-10-21 — plan created (proposed).

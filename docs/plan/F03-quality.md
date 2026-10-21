---
feature: F03
title: Data quality — contract, validate, quarantine
status: proposed
approved:
depends_on: [F02]
---

# F03 — Data quality: contract, validate, quarantine

**Goal:** declare each feed's expectations in a YAML contract, validate every bronze row, and split
the result into **silver** (passed) and **quarantine** (failed, with a `reason_code`) — the core of
the data-quality story.

**Non-goals:** scorecards/trends (optional), normalization/unit conversion (F04), dedupe (optional).

## Slices

### Slice 1 — Contract + loader   `[ ]`
- **In → out:** `contracts/supplier_contract.yaml` → a typed `DataContract` per supplier
- **Files:** `contracts/supplier_contract.yaml`, `src/quality/contracts.py`, `tests/test_quality.py`
- **Contract declares:** `required` fields, per-field `type`/`min`/`max`/`allowed`.
- **Test:** `test_quality.py::test_load_contracts` — all 3 suppliers load.
- **Critical actions:** none
- **Done when:** contracts load from the repo root.

### Slice 2 — Rules + quarantine   `[ ]`
- **In → out:** bronze rows + contract → findings with a `reason_code`
- **Files:** `src/quality/rules.py`, `src/quality/validate.py`, `tests/test_quality.py` (extend)
- **Reason codes (closed set):** `MISSING_REQUIRED`, `TYPE_MISMATCH`, `OUT_OF_RANGE`, `DUPLICATE_SKU`.
- **Test:** `test_quality.py::test_each_reason_code` — a broken fixture triggers each code.
- **Critical actions:** none
- **Done when:** bad rows are written to `quarantine_records` with code + field + raw payload.

### Slice 3 — `make quality`   `[ ]`
- **In → out:** `make quality` → `silver_products` + `quarantine_records`
- **Files:** `src/quality/validate.py` (silver write), `Makefile`
- **Test:** `test_quality.py::test_reconciliation` — `bronze = silver + quarantine`, exactly.
- **Critical actions:** none
- **Done when:** `make quality` is idempotent and reconciles.

## Acceptance
- [ ] `make quality` splits every bronze row into silver or quarantine; counts reconcile exactly.
- [ ] Every quarantined row has one `reason_code` from the closed set and its `raw_payload`.

## Commands
```bash
make data && make ingest && make quality
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.

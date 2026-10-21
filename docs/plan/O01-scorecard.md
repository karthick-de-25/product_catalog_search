---
feature: O01
title: Per-supplier quality scorecard + trend
status: done
approved: 2026-10-21
depends_on: [F03]
---

# O01 — Quality scorecard (optional, prioritized P1)

**Goal:** give the data-quality pillar numbers — per supplier: bronze/silver/quarantine counts,
reason-code breakdown, attribute completeness, validity, and a 0–100 score — appended to a
history table so the demo can show a trend.

**Non-goals:** dashboards/UI (scorecards feed F14's app later), alerts, aggregation beyond supplier.

## Slices

### Slice 1 — Compute + history table   `[x]`
- **In → out:** `bronze_records` + `silver_products` + `quarantine_records` → `supplier_scorecards`
- **Files:** `src/quality/scorecard.py`, `tests/test_scorecard.py`
- **Metrics per supplier:** bronze, silver, quarantine, `missing_required`, `type_mismatch`,
  `out_of_range`, `duplicate_sku`, `completeness` (non-empty attribute cells / total cells on
  silver), `validity` (silver/bronze), `score = 100 * (0.5·completeness + 0.5·validity)`.
- **Test:** reconciliation against quality tables; completeness < 1; scores in 0–100; calling
  twice with different run ids appends history (trend).
- **Critical actions:** none (all local DuckDB).
- **Done when:** the table exists and the offline tests pass.

### Slice 2 — `make scorecard`   `[x]`
- **In → out:** `make scorecard` → prints the per-supplier table
- **Files:** `Makefile`, `docs/plan/O01-scorecard.md`, `docs/plan/OPTIONAL.md`
- **Critical actions:** none
- **Done when:** the target runs after `make data && make ingest && make quality`.

## Acceptance
- [x] `make scorecard` prints one row per supplier with all metrics, and repeated runs append
      history so a trend is visible.

## Commands
```bash
make data && make ingest && make quality && make scorecard
make check
```

## Log
- 2026-10-21 — feature requested and approved by human (priority P1); plan created approved.
- 2026-10-21 — slice 1+2 implemented: `src/quality/scorecard.py` (supplier metrics,
  completeness/validity/score, history table) + `make scorecard`; 3 suppliers scored
  (acme 87.6, northwind 89.7, pacific 94.1); repeated runs append trend; 30 tests green.

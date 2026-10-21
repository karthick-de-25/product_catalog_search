---
feature: O03
title: Deduplication — merge near-duplicate products
status: done
approved: 2026-10-21
depends_on: [F04]
---

# O03 — Dedupe (optional, prioritized P2)

**Goal:** collapse near-duplicate products (same material+category+size, similar names —
often the same valve sold under multiple suppliers) into one canonical product, recording the
absorbed SKUs in `merged_skus` (CONTEXT invariant 3: losers recorded, never erased).

**Non-goals:** touching AlloyDB (a reload/re-embed of the deduped catalog would be a separate,
🔴 approved step), fuzzy matching beyond names, merging across different sizes.

## Slices

### Slice 1 — Candidate grouping + merge (pure)   `[x]`
- **In → out:** gold rows → grouped near-duplicates → canonical + absorbed SKUs
- **Files:** `src/enrichment/dedupe.py`, `tests/test_dedupe.py`
- **Blocking:** `(material, category, size_in)`; **similarity:** RapidFuzz `token_sort_ratio`
  on the name with its "for \<supplier\>" tail removed (threshold 88).
- **Canonical pick:** most complete row, tie-break by lowest SKU (deterministic).
- **Test:** normalization, threshold behavior, deterministic merge with a known group,
  losers recorded.
- **Critical actions:** none
- **Done when:** offline tests pass.

### Slice 2 — `gold_deduped` + `make dedupe`   `[x]`
- **In → out:** `gold_products` → `gold_deduped` + merge report
- **Files:** `src/enrichment/dedupe.py` (materialize), `Makefile`, `docs/plan/OPTIONAL.md`
- **Critical actions:** none (local DuckDB only)
- **Done when:** `make dedupe` prints gold → deduped counts and absorbed SKUs.

## Acceptance
- [x] `make dedupe` produces `gold_deduped` with merged rows; every absorbed SKU is recorded.
- [x] The merge is deterministic for a fixed catalog.

## Commands
```bash
make gold && make dedupe
make check
```

## Log
- 2026-10-21 — feature requested and approved by human (priority P2); plan created approved.
- 2026-10-21 — slices 1+2 implemented: `src/enrichment/dedupe.py` (blocking
  material+category+size; RapidFuzz token-sort on names minus "for <supplier>" tail; canonical
  = most complete, tie-break lowest sku) + `make dedupe`. Live: gold_products 197 →
  gold_deduped 107, 90 absorbed SKUs in 51 merged groups; losers recorded in `merged_skus`;
  rows with unknown size kept separate (conservative). 36 tests green.

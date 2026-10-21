---
feature: F04
title: Clean catalog (gold)
status: done
approved: 2026-10-21
depends_on: [F03]
---

# F04 — Clean catalog (gold)

**Goal:** normalize silver rows into the canonical model and materialize `gold_products` with a
`search_text` field ready for indexing.

**Non-goals:** LLM extraction, dedupe (both optional), taxonomy beyond a small controlled list.

## Slices

### Slice 1 — Normalize   `[x]`
- **In → out:** `silver_products` → normalized values (inches, PSI, clean brand/category)
- **Files:** `src/enrichment/normalize.py`, `tests/test_normalize.py`
- **Test:** `test_normalize.py::test_parse_size` — `3/4"`, `0.75 in`, `19 mm` all → `0.75`
  inches (19 mm → `0.748`); unparseable → `None`.
- **Critical actions:** none
- **Done when:** unit/brand/category normalization is a pure, tested function.

### Slice 2 — Materialize gold   `[x]`
- **In → out:** normalized rows → `gold_products` + `search_text`; `make gold` prints completeness lift
- **Files:** `src/enrichment/gold.py`, `Makefile`, `tests/test_gold.py`
- **Test:** `test_gold.py::test_gold_search_text` — every gold row has non-empty `search_text` and
  canonical `size_in`/`pressure_psi`.
- **Critical actions:** none
- **Done when:** `make gold` runs after `make quality` and exits 0.

## Acceptance
- [x] `make gold` produces `gold_products` with canonical units and a populated `search_text`.
- [x] Original raw values remain available for reference (in `silver_products`).

## Commands
```bash
make quality && make gold
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.
- 2026-10-21 — plan approved by human.
- 2026-10-21 — slice 1: `src/enrichment/normalize.py` — `parse_size` (`3/4"`, `0.75 in`,
  `19 mm` → 0.748; unparseable → None), `parse_pressure_psi`, brand alias table,
  `normalize_row`.
- 2026-10-21 — slice 2: `src/enrichment/gold.py` — `build_search_text` + `materialize_gold`
  + `make gold`; live run: gold 197 rows, size completeness silver 100% -> gold 96.4%.
  F04 done.
- 2026-10-21 — [P0 fix] `build_search_text` now replaces `_` with spaces so the full-text
  tokenizer sees real words (`ball_valves` -> `ball valves`). Regenerated gold locally, then
  (🔴 approved) cleared AlloyDB embeddings + `make load` (197 re-embedded, 0 nulls). Keyword
  search verified live: "brass ball valve lead free" and "pvc pipe" now return hits.

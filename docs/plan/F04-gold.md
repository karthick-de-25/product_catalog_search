---
feature: F04
title: Clean catalog (gold)
status: proposed
approved:
depends_on: [F03]
---

# F04 — Clean catalog (gold)

**Goal:** normalize silver rows into the canonical model and materialize `gold_products` with a
`search_text` field ready for indexing.

**Non-goals:** LLM extraction, dedupe (both optional), taxonomy beyond a small controlled list.

## Slices

### Slice 1 — Normalize   `[ ]`
- **In → out:** `silver_products` → normalized values (inches, PSI, clean brand/category)
- **Files:** `src/enrichment/normalize.py`, `tests/test_normalize.py`
- **Test:** `test_normalize.py::test_parse_size` — `3/4"`, `0.75 in`, `19 mm` all → `0.75`
  inches (19 mm → `0.748`); unparseable → `None`.
- **Critical actions:** none
- **Done when:** unit/brand/category normalization is a pure, tested function.

### Slice 2 — Materialize gold   `[ ]`
- **In → out:** normalized rows → `gold_products` + `search_text`; `make gold` prints completeness lift
- **Files:** `src/enrichment/gold.py`, `Makefile`, `tests/test_gold.py`
- **Test:** `test_gold.py::test_gold_search_text` — every gold row has non-empty `search_text` and
  canonical `size_in`/`pressure_psi`.
- **Critical actions:** none
- **Done when:** `make gold` runs after `make quality` and exits 0.

## Acceptance
- [ ] `make gold` produces `gold_products` with canonical units and a populated `search_text`.
- [ ] Original raw values remain available for reference.

## Commands
```bash
make quality && make gold
make check
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.

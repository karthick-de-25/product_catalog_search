---
feature: F06
title: Hybrid search (vector + keyword RRF)
status: proposed
approved:
depends_on: [F05]
---

# F06 — Hybrid search (vector + keyword RRF)

**Goal:** serve a single search entry point that routes a query — part-number style vs natural
language — and fuses vector and keyword results with Reciprocal Rank Fusion.

**Non-goals:** reranking, evaluation harness, RAG (all optional).

## Slices

### Slice 1 — Router + SQL   `[ ]`
- **In → out:** a query string → `("sku" | "text", params)`
- **Files:** `sql/04_hybrid_search.sql`, `src/search/hybrid_search.py`, `tests/test_search.py`
- **Test:** `test_search.py::test_route_query` — `"A-1234"` routes to SKU lookup; `"brass ball
  valve lead free"` routes to hybrid text.
- **Critical actions:** none
- **Done when:** the RRF SQL is written and the router is tested.

### Slice 2 — Search API + `make search`   `[ ]`
- **In → out:** query → ranked rows (`vector + keyword FULL OUTER JOIN`, `k = 60`)
- **Files:** `src/search/hybrid_search.py` (query executor), `Makefile`
- **Test:** `test_search.py::test_rrf_merge` — merging two canned ranked lists produces the
  expected RRF order (no database needed).
- **Critical actions:** none (the live query needs AlloyDB, but is exercised by the demo).
- **Done when:** `make search QUERY="..."` prints ranked results against AlloyDB.

## Acceptance
- [ ] Keyword-only, vector-only, and hybrid RRF paths all work; the router picks SKU vs text.
- [ ] `test_search.py` covers routing and RRF merge offline.

## Commands
```bash
make check
make search QUERY="3/4 brass ball valve lead free"   # needs AlloyDB
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.

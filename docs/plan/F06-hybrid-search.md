---
feature: F06
title: Hybrid search (vector + keyword RRF)
status: done
approved: 2026-10-21
depends_on: [F05]
---

# F06 — Hybrid search (vector + keyword RRF)

**Goal:** serve a single search entry point that routes a query — part-number style vs natural
language — and fuses vector and keyword results with Reciprocal Rank Fusion.

**Non-goals:** reranking, evaluation harness, RAG (all optional).

## Slices

### Slice 1 — Router + SQL   `[x]`
- **In → out:** a query string → `("sku" | "text", params)`
- **Files:** `sql/04_hybrid_search.sql`, `src/search/hybrid_search.py`, `tests/test_search.py`
- **Test:** `test_search.py::test_route_query` — `"A-1234"` routes to SKU lookup; `"brass ball
  valve lead free"` routes to hybrid text.
- **Critical actions:** none
- **Done when:** the RRF SQL is written and the router is tested.

### Slice 2 — Search API + `make search`   `[x]`
- **In → out:** query → ranked rows (`vector + keyword FULL OUTER JOIN`, `k = 60`)
- **Files:** `src/search/hybrid_search.py` (query executor), `Makefile`
- **Test:** `test_search.py::test_rrf_merge` — merging two canned ranked lists produces the
  expected RRF order (no database needed).
- **Critical actions:** none (the live query needs AlloyDB, but is exercised by the demo).
- **Done when:** `make search QUERY="..."` prints ranked results against AlloyDB.

## Acceptance
- [x] Keyword-only, vector-only, and hybrid RRF paths all work; the router picks SKU vs text.
- [x] `test_search.py` covers routing and RRF merge offline.

## Commands
```bash
make check
make search QUERY="3/4 brass ball valve lead free"   # needs AlloyDB
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.
- 2026-10-21 — plan approved by human.
- 2026-10-21 — slice 1: `sql/04_hybrid_search.sql` (named-param RRF, k=60) +
  `src/search/hybrid_search.py` (SKU-pattern router + pure `rrf_merge`); offline tests.
- 2026-10-21 — slice 2: keyword/vector/hybrid executors + `make search`. Live demo vs
  AlloyDB: keyword-only 0 hits (tokenizer), vector + hybrid rank brass ball valves
  (ACME-0069/0042, NORT-0075 …). Fixed `round(real/double,int)` -> `::numeric` and
  `%(cat)s::text` type inference in all three paths. F06 done.

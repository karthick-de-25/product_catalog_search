---
feature: O04
title: Evaluation harness — keyword vs vector vs hybrid
status: done
approved: 2026-10-21
depends_on: [F06]
---

# O04 — Evaluation harness (optional, prioritized P1)

**Goal:** quantify the demo's core claim — *hybrid > vector > keyword* — with Recall@10,
MRR, and NDCG@10 over a deterministic golden query set built from the real catalog.

**Non-goals:** Ragas, human-labeled golden sets, production CI gating.

## Slices

### Slice 1 — Golden set + metrics   `[x]`
- **In → out:** `gold_products`/`products` → golden queries (material+category, size-scoped,
  exact SKU) + pure metric functions
- **Files:** `src/eval/golden.py`, `tests/test_eval.py`
- **Golden set:** seeded sampling of `(material, category)` combos → query = "brass ball
  valves"; relevant = all gold SKUs with that material+category. Plus a few size-scoped and
  exact-SKU queries. Deterministic for a fixed seed + catalog.
- **Metrics:** `recall_at_k`, `mrr`, `ndcg_at_k` (binary relevance) — pure, unit-tested on
  hand-computed values.
- **Critical actions:** none
- **Done when:** offline tests pass (metrics math + golden builder against DuckDB gold).

### Slice 2 — `make eval`   `[x]`
- **In → out:** live AlloyDB → per-method Recall@10 / MRR / NDCG@10 table
- **Files:** `src/eval/golden.py` (evaluate_live + main), `Makefile`
- **Runs** keyword / vector / hybrid over the golden set (read-only; each vector/hybrid query
  makes one small query-embedding call).
- **Critical actions:** none (read-only; live run needs the proxy + `ENABLE_CLOUD=true`)
- **Done when:** `make eval` prints the comparison table.

## Acceptance
- [x] `make eval` reports Recall@10 / MRR / NDCG@10 for keyword-only, vector-only, hybrid (RRF).
- [x] Metrics are unit-tested offline; the golden set is deterministic per seed.

## Commands
```bash
make eval            # needs AlloyDB + proxy
make check           # offline tests
```

## Log
- 2026-10-21 — feature requested and approved by human (priority P1); plan created approved.
- 2026-10-21 — slices 1+2 implemented: `src/eval/golden.py` (deterministic golden set from
  the catalog, pure recall/mrr/ndcg), `make eval`. Live run (33 queries): keyword recall
  0.9704 MRR 1.0 NDCG 1.0; vector 0.9704/0.9606/0.9652; hybrid 0.9704/1.0/1.0 — the P0
  tokenizer fix made keyword exact on literal queries, so hybrid matches it; vector trails
  slightly. Paraphrase-style queries (to show vector's edge) noted as future polish.

# ROADMAP — Product Catalog Intelligence Platform

**Core = data quality + hybrid search.** Optional extras are in [`OPTIONAL.md`](./OPTIONAL.md).

Workflow: `/skill:plan FNN` → human approves → `/skill:implement FNN`.
Statuses: `todo` · `planned` · `approved` · `in-progress` · `done` · `blocked`.
Keep features to **≤3 slices**, one happy-path test each. 🔴 = needs critical approval (cloud/cost).

---

## Core (first round)

The story: dirty feeds → ingest → quality gate → clean catalog → AlloyDB → hybrid search → demo.

| ID | Feature | Depends on | Status | Slices |
|---|---|---|---|---|
| F00 | Foundation & dev env | — | done | 5/5 |
| F01 | Synthetic dirty supplier feeds | F00 | done | 2/2 |
| F02 | Bronze ingestion | F01 | done | 2/2 |
| F03 | Data quality: contract, validate, quarantine | F02 | done | 3/3 |
| F04 | Clean catalog (gold) | F03 | done | 2/2 |
| F05 | AlloyDB + load + embeddings 🔴 | F04 | done | 2/2 |
| F06 | Hybrid search (vector + keyword RRF) | F05 | done | 2/2 |
| F07 | Streamlit search demo | F06 | done | 1/1 |

**All core features (F00–F07) are done.** Optional ideas: `docs/plan/OPTIONAL.md`.

---

## Slice outline (core)

### F01 · Synthetic dirty supplier feeds — *`F01-dirty-data.md`*
1. Seeded generator: 3 suppliers, 3 formats (CSV/JSON/XML), small catalog, injected defects
2. `make data` + deterministic output + a manifest of defect counts

### F02 · Bronze ingestion — *`F02-ingest.md`*
1. DuckDB connection + `bronze_records` (raw payload preserved) + CSV/JSON/XML flattening
2. `make ingest` + row counts reconcile with the F01 manifest

### F03 · Data quality: contract, validate, quarantine — *`F03-quality.md`*
1. Contract model + `contracts/supplier_contract.yaml`
2. Validation rules emitting the 4 `reason_code`s
3. `make quality` → `silver_products` + `quarantine_records` with `bronze = silver + quarantine`

### F04 · Clean catalog (gold) — *`F04-gold.md`*
1. Minimal normalization (units → inches/PSI, brand/category cleanup) → `gold_products`
2. `make gold` + build `search_text`; completeness lift printed

### F05 · AlloyDB + load + embeddings 🔴 — *`F05-alloydb.md`*
1. `sql/01..03`: extensions, `products` schema, ScaNN + GIN + pg_trgm indexes
2. `make db` + `make load`: upsert gold → AlloyDB, embeddings via Vertex AI

### F06 · Hybrid search — *`F06-hybrid-search.md`*
1. `sql/04_hybrid_search.sql` (vector + keyword, RRF `k=60`) + query routing (SKU vs text)
2. `src/search/hybrid_search.py` + `make search` smoke

### F07 · Streamlit search demo — *`F07-streamlit-demo.md`*
1. One-page app: search box, metadata filters, results table, keyword-vs-hybrid toggle

---

## Optional (not required for round 1)

See [`OPTIONAL.md`](./OPTIONAL.md): scorecard, Gemini extraction, dedupe, evaluation harness,
RAG assistant, feedback loop. Build only if the core demo is solid and the human asks.

---

## Conventions

- Feature ids are stable. Amend a plan in place; never create `FNN-v2.md`.
- Adding a feature or changing scope/acceptance criteria requires approval (`AGENTS.md` §4).
- Keep this file and the plan files in sync — the implement skill reads both.

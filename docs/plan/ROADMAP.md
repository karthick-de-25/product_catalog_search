# ROADMAP — Product Catalog Intelligence Platform

Single source of truth for delivery order. A **feature** is a vertical capability with its own
plan file `docs/plan/FNN-slug.md`. A **slice** is the smallest end-to-end increment of a feature.

**Statuses:** `todo` · `planned` · `approved` · `in-progress` · `done` · `blocked`

Workflow: `/skill:plan FNN` → human approves → `/skill:implement FNN` → `/skill:verify FNN`.
Never start a feature whose dependencies are not `done`. Never implement without an approved plan.

Legend: 🔴 = feature will need Tier C (cloud/cost) approval during build.

---

## Progress

| ID | Feature | Depends on | Status | Slices |
|---|---|---|---|---|
| F00 | Foundation & dev environment | — | in-progress | 3/5 |
| F01 | Synthetic dirty supplier feeds | F00 | planned | 5 |
| F02 | Bronze ingestion & profiling | F01 | todo | 4 |
| F03 | Data contracts, validation & quarantine | F02 | todo | 5 |
| F04 | Quality scorecard & monitoring | F03 | todo | 4 |
| F05 | Normalization & standardization | F03 | todo | 5 |
| F06 | LLM attribute extraction (Gemini) | F05 | todo | 5 |
| F07 | Deduplication | F05 | todo | 4 |
| F08 | Gold canonical catalog | F06, F07 | todo | 4 |
| F09 | AlloyDB foundation 🔴 | F08 | todo | 5 |
| F10 | Load gold + embeddings 🔴 | F09 | todo | 5 |
| F11 | Hybrid search & query routing | F10 | todo | 5 |
| F12 | Evaluation harness | F11 | todo | 5 |
| F13 | RAG assistant | F11 | todo | 6 |
| F14 | Streamlit app | F12, F13 | todo | 4 |
| F15 | Feedback & observability | F13, F14 | todo | 3 |

**Next up:** F00 — approved. Run `/skill:implement F00`.

---

## Backlog outline (slice titles)

> Detailed, executable plan files are authored just-in-time by the `plan` skill. Full plans
> exist today for F00–F03. The list below is the agreed scope — do not silently expand it.

### F00 · Foundation & dev environment — *draft plan: `F00-foundation.md`*
1. `pyproject.toml` tool config (ruff, mypy, pytest) + `src/` package skeleton
2. Typed config loader (`src/config.py`) from env with safe defaults + `src/logging_utils.py`
3. Shared errors + closed `reason_code` enum (`src/errors.py`)
4. `Makefile` (`setup`, `check`, `test`, `fmt`, `clean`) wired to the tools
5. Test harness (`tests/conftest.py`, `tests/fixtures/`) + smoke test; `make check` green

### F01 · Synthetic dirty supplier feeds — *draft plan: `F01-dirty-data.md`*
1. Seeded generator core + product taxonomy sample
2. CSV feed (`acme_valves`) with injected defects
3. JSON feed (`northwind_supply`) + XML feed (`pacific_pipe`)
4. Defect manifest + determinism/reproducibility test
5. `make data` target + docs

### F02 · Bronze ingestion & profiling — *draft plan: `F02-ingest-profile.md`*
1. DuckDB connection helper + bronze schema (raw payload preserved)
2. CSV/JSON/XML flattening to a common bronze record (semi-structured aware)
3. Profiling: null rate, cardinality, distributions → report artifact
4. `make ingest` / `make profile` + reconciliation test

### F03 · Data contracts, validation & quarantine — *draft plan: `F03-quality-contracts.md`*
1. Contract model + loader (`contracts/supplier_contract.yaml`)
2. Rule engine (required/type/range/enum/unit) emitting `reason_code`s
3. Quarantine table + `bronze = silver + quarantine` reconciliation
4. Silver materialization
5. `make quality` + tests against deliberately broken fixtures

### F04 · Quality scorecard & monitoring
1. Per-supplier completeness/duplicate/validity scoring
2. Run-history table + trend across runs
3. Scorecard report artifact (markdown + CSV)
4. Threshold alerting + tests

### F05 · Normalization & standardization
1. Unit parser (fractions, `"`, `in`, `mm`) → canonical inches/PSI
2. Brand normalization (alias table + RapidFuzz)
3. Taxonomy/category mapping to the controlled vocabulary
4. Material / certification normalization
5. `make enrich` (structured part) + tests

### F06 · LLM attribute extraction (Gemini)
1. JSON-schema output contract + mockable Gemini adapter
2. Extraction prompt + schema validation + per-attribute confidence
3. `review_queue` for low-confidence attributes
4. Precision/recall on a small labeled sample
5. Offline mock tests (no network in CI)

### F07 · Deduplication
1. Blocking keys (brand + category)
2. Similarity scoring (RapidFuzz token/ratio)
3. Deterministic merge policy + golden-record selection
4. Near-duplicate fixture tests

### F08 · Gold canonical catalog
1. Gold schema (canonical model from `CONTEXT.md`) + materialization
2. `search_text` construction
3. Gold reconciliation + completeness-lift report
4. `make gold` + tests

### F09 · AlloyDB foundation 🔴
1. `sql/01_extensions.sql` (`vector`, `alloydb_scann`, `google_ml_integration`, `pg_trgm`)
2. `sql/02_schema.sql` (`products`, `doc_chunks`, `feedback`, `review_queue`, column comments)
3. `sql/03_indexes.sql` (ScaNN, GIN `tsv`, `pg_trgm`, category)
4. `sql/05_row_level_security.sql`
5. Idempotent apply script; **apply to cloud is Tier C**

### F10 · Load gold + embeddings 🔴
1. Auth-Proxy connection adapter, config-guarded
2. Idempotent upsert loader
3. Embedding generation in SQL (batched, cost-capped, only where null/changed)
4. Load verification (counts, null embeddings, RLS sanity)
5. `make load` / `make embed`

### F11 · Hybrid search & query routing
1. `sql/04_hybrid_search.sql` (RRF, `k = 60`)
2. Query classifier (SKU/part number vs natural language)
3. `pg_trgm` fuzzy fallback for typos
4. Metadata filters (brand, category, `lead_free`, material)
5. Python search API + tests against a fake/recorded DB

### F12 · Evaluation harness
1. Golden query set (~50 labeled queries: exact SKU, typos, synonyms, NL)
2. Metrics: Recall@k, MRR, NDCG@10
3. Keyword vs vector vs hybrid runner
4. Results table + report artifact (before/after enrichment)
5. `make eval`

### F13 · RAG assistant
1. Doc ingestion + structure-aware chunking with metadata (sku, doc type, page)
2. `doc_chunks` embeddings
3. Hybrid retrieval for documents
4. Grounded answer with citations + refusal on weak evidence
5. Feedback + latency/token logging
6. Mockable tests, including a refusal test

### F14 · Streamlit app
1. Search page (keyword vs vector vs hybrid side by side)
2. RAG page with citations and refusal states
3. Quality dashboard (scorecard, quarantine reasons, enrichment lift)
4. `make app` + smoke test

### F15 · Feedback & observability
1. Feedback capture (thumbs up/down) into `feedback`
2. Zero-result and latency monitoring
3. Per-run metrics summary artifact

---

## Conventions

- Feature ids are stable. Never renumber.
- Amend a plan in place; never create `FNN-v2.md`.
- Adding a feature, changing scope, or changing acceptance criteria is **Tier C** (needs the human).
- Keep this file and the plan files in sync — the `implement`/`verify` skills read both.

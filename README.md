# Product Catalog Intelligence Platform

An end-to-end **demo**: turn messy multi-supplier product feeds (CSV/JSON/XML) into a clean,
enriched catalog, then serve **hybrid search** (semantic vector + keyword) from AlloyDB for
PostgreSQL — with a Streamlit UI on top.

> **Scenario:** a PVF/HVAC/plumbing distributor gets data from thousands of suppliers in every
> possible shape. Contractors search with vague phrases (*"3/4 inch brass ball valve lead free"*)
> or paste part numbers. Bad data means bad search and lost sales.

**Round 1 focuses on two things: data quality + hybrid search.** Everything else is pending/optional
([`docs/plan/OPTIONAL.md`](./docs/plan/OPTIONAL.md)).

---

## Status — implemented vs pending

### ✅ Implemented

| Feature | What it does | Make |
|---|---|---|
| **F01** Dirty supplier feeds | Seeded generator: 3 suppliers, 3 formats (CSV/JSON/XML), 240 rows with injected defects + manifest | `make data` |
| **F02** Bronze ingestion | Raw rows loaded verbatim into DuckDB `bronze_records` (idempotent) | `make ingest` |
| **F03** Data quality gate | YAML contracts → validate → **197 silver + 43 quarantined** (exact reconciliation `bronze = silver + quarantine`) | `make quality` |
| **F04** Clean catalog (gold) | Canonical units (inches/PSI), clean brands, `search_text`; unparseable sizes → `NULL`, never guessed | `make gold` |
| **F05** AlloyDB 🔴 | `products` table + extensions + indexes (vector, ScaNN, GIN, trgm), upsert + in-DB embeddings (capped) | `make db` / `make load` |
| **F06** Hybrid search | Query router (SKU vs text) + vector & keyword fused with **RRF (k=60)** | `make search` |
| **F07** Streamlit demo | One-page search UI: keyword vs hybrid side by side, filters | `make app` |
| **O01** Quality scorecard | Per-supplier completeness/validity/score + **trend history** | `make scorecard` |
| **O03** Dedupe | Near-duplicate merge: gold **197 → 107**, 90 absorbed SKUs recorded | `make dedupe` |
| **O04** Evaluation | Recall@10 / MRR / NDCG over 33 golden queries, keyword vs vector vs hybrid | `make eval` |

### ⏳ Pending / optional (needs your approval to build)

| Item | Idea | Effort |
|---|---|---|
| **O2** Gemini attribute extraction | Pull size/material/certs from free text with confidence + review queue | medium, LLM cost |
| **O5** RAG assistant | "Ask your catalog" with citations and a grounding/refusal rule | high |
| **O6** Feedback & monitoring | Thumbs up/down, zero-result and latency tracking | low |
| Eval polish | Paraphrase-style golden queries to show vector search's edge | low |

---

## Pipeline

```
 supplier feeds (CSV/JSON/XML)
   → bronze_records (raw, immutable)         make data → make ingest
      → contract + validation rules
         → silver_products                   make quality  (bronze = silver + quarantine)
         → quarantine_records (reason codes)
      → normalize + search_text → gold      make gold
      → (dedupe) → gold_deduped             make dedupe
   → AlloyDB products + embeddings          make db · make load   (🔴 cloud)
   → hybrid search (RRF)                     make search / make app
   → scorecard, eval                        make scorecard · make eval
```

**Reason codes (closed set):** `MISSING_REQUIRED` · `TYPE_MISMATCH` · `OUT_OF_RANGE` · `DUPLICATE_SKU`.

---

## Quick start

```bash
# one-time
make setup            # create .venv + install deps

# the demo, end to end (all local except the last two)
make data             # dirty feeds
make ingest           # → bronze (240)
make quality          # → silver (197) + quarantine (43)
make gold             # → gold catalog
make scorecard        # per-supplier quality scores
make dedupe           # optional: merge near-duplicates (197 → 107)

# cloud (🔴 needs AlloyDB cluster + Auth Proxy; see docs/gcp-setup.md)
make db
make load

# search + UI
make search QUERY="brass ball valve lead free"
make eval             # keyword vs vector vs hybrid numbers (needs AlloyDB)
make app              # Streamlit
```

**Live eval numbers (33 golden queries):** keyword `0.97 / 1.00 / 1.00`, vector `0.97 / 0.96 / 0.97`,
hybrid `0.97 / 1.00 / 1.00` (Recall@10 / MRR / NDCG@10) — literal queries are exact after the
tokenizer fix; paraphrase queries are future polish.

---

## The two core stories

**1. Data quality — fail loudly, never silently.** Every feed is declared in a YAML contract
(`contracts/supplier_contract.yaml`). Rows that fail validation land in `quarantine_records`
with one primary reason code + the original payload; `bronze = silver + quarantine` is enforced
exactly. The scorecard turns that into per-supplier numbers with history.

**2. Hybrid search — keyword alone isn't enough.** "brass ball valves" can defeat the English
tokenizer (`ball_valves` is one word); vector search understands meaning. Hybrid fuses both
rankings with Reciprocal Rank Fusion (`sql/04_hybrid_search.sql`, k=60), so a product found by
*both* methods wins.

---

## GCP / AlloyDB

AlloyDB is the only cloud component (vectors, full-text, ScaNN, trgm, `embedding()` from SQL).
Step-by-step setup: [`docs/gcp-setup.md`](./docs/gcp-setup.md).

> **Cost:** the cluster bills per hour and cannot be paused — delete it when not demoing:
> `gcloud alloydb clusters delete catalog-cluster --region=<your-region> --force`, then re-create
> + `make db && make load` next time. Embedding/query costs are cents at demo scale.

---

## Development (local, no cloud)

```bash
make check      # ruff + pytest  (the gate — no GCP needed)
make fmt        # ruff format + fix
make typecheck  # mypy (optional, not part of `check`)
make clean      # caches only, never data/
```

Tests: **36 tests**, one happy-path test per slice, fully offline. `data/catalog.duckdb` holds
all local tables (`bronze_records`, `silver_products`, `quarantine_records`, `gold_products`,
`gold_deduped`, `supplier_scorecards`).

---

## Agents workflow

The repo is built feature-by-feature in vertical slices by an AI agent. Binding contract:
[`AGENTS.md`](./AGENTS.md) · domain model: [`CONTEXT.md`](./CONTEXT.md) · delivery order:
[`docs/plan/ROADMAP.md`](./docs/plan/ROADMAP.md).

```
/skill:plan FNN → human: "approve FNN" → /skill:implement FNN
```

Cloud/cost/destructive/scope changes require human approval (`AGENTS.md` §4); everything else is
autonomous. `make check` stays green after every slice. There is no separate verification step.

---

## Design decisions (short)

- **Local-first, AlloyDB-in-cloud only** — DuckDB/Parquet stand in for BigQuery/GCS/Dataflow.
- **Contracts + quarantine over silent coercion** — failures are visible, countable, recoverable.
- **RRF over score tuning** — combines vector + keyword ranks without calibration.
- **Determinism first** — seeds, sorted iteration, and tie-breaks make every step reproducible.

## License

MIT

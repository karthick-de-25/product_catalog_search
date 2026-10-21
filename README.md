# Product Catalog Intelligence Platform (GCP + AlloyDB)

An end-to-end data engineering project that turns messy multi-supplier product feeds into a clean, enriched, **searchable** catalog using **hybrid AI search** (semantic vector + keyword) on **AlloyDB for PostgreSQL**, with a simple **RAG** assistant on top.

> **Scenario:** A large PVF/HVAC/plumbing distributor works with ~37,000 suppliers. Every supplier sends data differently (units, names, missing attributes, duplicates). Contractors search with vague phrases like *"3/4 inch brass ball valve lead free"* or paste part numbers. Bad data means bad search and lost sales.

---

## What this project demonstrates

| Requirement | Where it is covered |
|---|---|
| Data quality, validation, profiling, monitoring, governance | `src/quality/`, `contracts/`, quality scorecard dashboard |
| Data enrichment (structured, semi-structured, unstructured) | `src/enrichment/` (CSV/JSON/XML normalization, PDF/text extraction with Gemini) |
| Hybrid AI search (vector + keyword) | `sql/` + `src/search/` on AlloyDB (ScaNN, tsvector, pg_trgm, RRF) |
| RAG and enterprise search | `src/rag/` (hybrid retrieval, citations, grounding checks) |
| AlloyDB | The only cloud-hosted component, with embeddings generated from SQL via Vertex AI |

---

## Development workflow (humans + AI agents)

This repo is set up to be built **feature by feature, in vertical slices**, mostly by an AI
agent, with human approval only at gates that matter.

- **[`AGENTS.md`](./AGENTS.md)** — the binding contract: golden rules, approval policy
  (🟢 autonomous / 🟡 announce / 🔴 stop-and-ask), conventions, definition of done.
- **[`CONTEXT.md`](./CONTEXT.md)** — domain glossary, canonical product model, invariants,
  and the closed set of quarantine reason codes.
- **[`docs/plan/ROADMAP.md`](./docs/plan/ROADMAP.md)** — every feature (F00–F15), dependencies,
  and status. **This is the source of truth for delivery order.**
- **[`docs/plan/`](./docs/plan)** — one plan file per feature, sliced end-to-end, each with
  acceptance criteria and a test. [`TEMPLATE.md`](./docs/plan/TEMPLATE.md) shows the shape.
- **[`docs/adr/`](./docs/adr)** — architecture decision records.
- **[`docs/agents/README.md`](./docs/agents/README.md)** — how the agent skills/subagents are wired.

The loop:

```
/skill:plan FNN  →  human: "approve FNN"  →  /skill:implement FNN  →  /skill:verify FNN
```

1. **Plan** — the agent scopes the feature into vertical slices and writes
   `docs/plan/FNN-*.md`, then **stops for your approval**.
2. **Approve** — you review scope, slices, and any 🔴 critical items. One approval, not per-slice.
3. **Implement** — the agent builds slice by slice, tests each one, and keeps `make check`
   green. It only stops mid-flight for critical changes (cloud/GCP, cost, destructive ops,
   secrets, breaking contracts/interfaces, new dependencies, scope changes).
4. **Verify** — the agent reproduces evidence against the acceptance criteria and marks the
   feature done.

Current state: **F00 (Foundation) is planned and awaiting approval.** Run `/skill:plan F00` to
review it, or `/skill:status` for a progress snapshot.

---

## Design principle: local first, AlloyDB in the cloud

To keep it simple (no Docker, no orchestration platform), everything runs on your laptop except the pieces that **must** be on GCP:

| Concern | Production-scale choice | What this project uses |
|---|---|---|
| Raw/bronze/silver/gold storage | GCS + BigQuery + Dataflow | **Local Parquet files + DuckDB** |
| Data quality rules | Dataplex / Great Expectations | **Python rules + Pandera**, YAML data contracts |
| Orchestration | Cloud Composer / Airflow | **Simple Python scripts + Makefile** |
| LLM enrichment | Vertex AI | **Gemini via Vertex AI** (free trial credits) |
| Vector + keyword search | AlloyDB | **AlloyDB on GCP** (the star of the project) |
| API / UI | Cloud Run | **Streamlit locally** |
| Connectivity to AlloyDB | VPC / private IP | **AlloyDB Auth Proxy** (a single binary, no Docker) |

---

## Architecture

```
 Supplier feeds (CSV / JSON / XML) + PDF spec sheets
                    │
                    ▼
   Local data lake (Parquet)  ──►  DuckDB (bronze → silver → gold)
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
 Data Quality layer        Enrichment layer
 (contracts, rules,        (unit normalization, brand matching,
  profiling, quarantine,    Gemini attribute extraction from
  supplier scorecard)       text/PDF, taxonomy mapping)
        └───────────┬────────────┘
                    ▼
        Clean, enriched products (gold)
                    │   load via Auth Proxy
                    ▼
   ┌──────────────────────────────────────────┐
   │ AlloyDB (GCP)                            │
   │  • pgvector + ScaNN index                │
   │  • embedding() from SQL → Vertex AI      │
   │  • tsvector + GIN (keyword)              │
   │  • pg_trgm (typos / part numbers)        │
   │  • Hybrid ranking with RRF in SQL        │
   │  • Row-level security                    │
   └──────────────────────────────────────────┘
                    │
                    ▼
   Search + RAG layer (Python)  ──►  Streamlit app
                    │
                    ▼
   Evaluation (Recall@k, MRR, NDCG) + Quality dashboard
```

---

## Tech stack

- **Language:** Python 3.11+
- **Local data:** DuckDB, Pandas, Parquet
- **Quality:** Pandera, ydata-profiling, YAML data contracts
- **LLM / embeddings:** Gemini + `text-embedding-005` on Vertex AI
- **Database:** AlloyDB for PostgreSQL (`vector`, `alloydb_scann`, `google_ml_integration`, `pg_trgm`)
- **App:** Streamlit
- **Evaluation:** custom golden query set (Recall@k, MRR, NDCG), optional Ragas for RAG

---

## Repository structure

```
product-catalog-intelligence/
├── README.md
├── Makefile
├── requirements.txt
├── .env.example
├── contracts/
│   └── supplier_contract.yaml        # data contract per supplier feed
├── data/
│   ├── raw/                          # generated dirty supplier feeds
│   ├── silver/
│   ├── gold/
│   └── docs/                         # sample PDF spec sheets
├── sql/
│   ├── 01_extensions.sql
│   ├── 02_schema.sql
│   ├── 03_indexes.sql
│   ├── 04_hybrid_search.sql
│   └── 05_row_level_security.sql
├── src/
│   ├── generate/make_dirty_data.py   # synthetic supplier feeds with injected errors
│   ├── ingest/load_bronze.py
│   ├── quality/
│   │   ├── profile.py
│   │   ├── validate.py               # rules + quarantine + reason codes
│   │   └── scorecard.py              # per-supplier quality score
│   ├── enrichment/
│   │   ├── normalize.py              # units, brand matching, taxonomy
│   │   ├── extract_attributes.py     # Gemini → JSON schema output
│   │   └── dedupe.py                 # near-duplicate detection
│   ├── load/load_alloydb.py
│   ├── search/hybrid_search.py       # query routing + RRF
│   ├── rag/
│   │   ├── ingest_docs.py            # chunking + embeddings
│   │   └── answer.py                 # retrieval + Gemini with citations
│   ├── eval/
│   │   ├── golden_queries.csv
│   │   └── evaluate_search.py
│   └── app/streamlit_app.py
└── docs/
    └── architecture.png
```

---

## Prerequisites

- Python 3.11+
- A GCP account with the **free trial** enabled and a project created
- `gcloud` CLI installed and authenticated
- AlloyDB Auth Proxy binary ([download from Google docs](https://cloud.google.com/alloydb/docs/auth-proxy/connect))
- Billing **budget alert** configured on day one

---

## Setup

### 1. Local environment

```bash
git clone <your-repo-url> && cd product-catalog-intelligence
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Suggested `requirements.txt`:

```
duckdb
pandas
pyarrow
pandera
pyyaml
faker
ydata-profiling
psycopg[binary]
google-genai
google-cloud-aiplatform
rapidfuzz
streamlit
pypdf
python-dotenv
```

### 2. GCP and AlloyDB

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

gcloud services enable alloydb.googleapis.com aiplatform.googleapis.com \
  compute.googleapis.com servicenetworking.googleapis.com
```

Create the AlloyDB cluster and a **primary instance (smallest size, 2 vCPU)** from the console or CLI. Use a private services access range, then enable **public IP** on the instance for easy laptop access through the Auth Proxy (dev only).

Allow AlloyDB to call Vertex AI (required for `embedding()` in SQL):

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:service-PROJECT_NUMBER@gcp-sa-alloydb.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Run the Auth Proxy in a separate terminal:

```bash
./alloydb-auth-proxy \
  "projects/YOUR_PROJECT_ID/locations/REGION/clusters/CLUSTER/instances/INSTANCE" \
  --public-ip --port 5432
```

Fill `.env`:

```
GCP_PROJECT=your-project-id
GCP_REGION=us-central1
PGHOST=127.0.0.1
PGPORT=5432
PGUSER=postgres
PGPASSWORD=...
PGDATABASE=catalog
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-005
```

> **Cost tip:** AlloyDB is the main cost driver. **Stop or delete the cluster when not in use.** Keep the dataset to 20K–50K products.

---

## Development (local, no cloud)

The dev loop is a single Makefile entry point. `make setup` creates the virtualenv and
installs dependencies; `make check` is the gate and never needs GCP credentials.

```bash
make setup      # create .venv and install requirements*.txt (uv preferred, pip fallback)
make fmt        # ruff format + ruff check --fix
make lint       # ruff check
make typecheck  # mypy --strict on src/
make test       # pytest
make check      # lint + format check + types + tests   ← run before every commit
make clean      # remove caches only (never touches data/)
```

Pipeline targets (`data`, `ingest`, `quality`, `enrich`, `gold`, `db`, `load`, `embed`,
`eval`, `app`) are added by the feature that implements them — see
[`docs/plan/ROADMAP.md`](./docs/plan/ROADMAP.md). Nothing here calls GCP.

For the AI-agent build workflow, see [`AGENTS.md`](./AGENTS.md) and
[`docs/agents/README.md`](./docs/agents/README.md).

---

## How to run (step by step)

```bash
make data        # 1. generate dirty supplier feeds
make ingest      # 2. load raw feeds into DuckDB (bronze)
make quality     # 3. profile, validate, quarantine, scorecard
make enrich      # 4. normalize, Gemini extraction, dedupe
make db          # 5. create AlloyDB schema, extensions, indexes
make load        # 6. load gold products into AlloyDB
make embed       # 7. generate embeddings inside AlloyDB
make eval        # 8. compare keyword vs vector vs hybrid
make app         # 9. launch Streamlit (search + RAG + quality dashboard)
```

---

## Module details

### 1. Data quality, profiling, monitoring and governance

**Synthetic dirty data** (`make_dirty_data.py`): generated with Faker plus injected defects across 3 to 5 simulated suppliers, each with its own schema and format:

- Inconsistent units: `3/4"`, `0.75 in`, `19 mm`
- Missing attributes (material, pressure rating, certification)
- Duplicate SKUs and near-duplicate products
- Brand name variants (`Watts`, `WATTS Inc.`, `watts`)
- Wrong or missing categories

**Quality framework:**

| Capability | Implementation |
|---|---|
| Data contracts | `contracts/supplier_contract.yaml`: required fields, types, allowed values, units |
| Profiling | Null rates, cardinality, distributions via DuckDB SQL and `ydata-profiling` |
| Validation rules | Completeness, uniqueness, validity, consistency (Pandera + custom checks) |
| Quarantine | Bad rows go to `quarantine` with `reason_code`, never silently dropped |
| Scorecard | Per-supplier score, e.g. *"Supplier X: 62% attribute completeness"* |
| Monitoring | Row-count and freshness checks, score trends stored per run |
| Governance | Column descriptions and tags (`COMMENT ON`), PII/sensitive column flags, row-level security, lineage documented in `docs/` |

Example contract:

```yaml
supplier: acme_valves
required: [sku, name, brand, category]
fields:
  sku:        {type: string, unique: true}
  size_in:    {type: float, min: 0.125, max: 48}
  material:   {type: string, allowed: [brass, bronze, pvc, cpvc, copper, stainless]}
  lead_free:  {type: boolean}
thresholds:
  completeness_min: 0.90
  duplicate_rate_max: 0.02
```

### 2. Data enrichment

| Source type | Technique |
|---|---|
| **Structured** (CSV) | Unit standardization, brand normalization (RapidFuzz), taxonomy mapping |
| **Semi-structured** (JSON/XML) | Flatten and map varied supplier schemas to a canonical model |
| **Unstructured** (descriptions, PDF spec sheets) | Gemini extracts size, material, pressure rating, certifications (NSF/ANSI 61, lead-free), connection type |

Guardrails for LLM enrichment:

- Output constrained to a **JSON schema** and validated before use
- **Confidence score** per attribute; low confidence goes to a `review_queue` table (human-in-the-loop)
- Accuracy measured on a small labeled sample (precision/recall per attribute)
- Near-duplicate detection using blocking (brand + category) plus similarity threshold

### 3. AlloyDB hybrid search

**Extensions** (`sql/01_extensions.sql`):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS alloydb_scann;
CREATE EXTENSION IF NOT EXISTS google_ml_integration;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**Schema** (`sql/02_schema.sql`):

```sql
CREATE TABLE products (
  id            BIGSERIAL PRIMARY KEY,
  sku           TEXT UNIQUE NOT NULL,
  supplier_id   TEXT,
  name          TEXT,
  description   TEXT,
  brand         TEXT,
  category      TEXT,
  size_in       NUMERIC,
  material      TEXT,
  pressure_psi  INT,
  lead_free     BOOLEAN,
  certifications TEXT[],
  search_text   TEXT,
  tsv           TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(search_text,''))) STORED,
  embedding     VECTOR(768)
);
```

**Generate embeddings directly in SQL** (Vertex AI called from AlloyDB):

```sql
UPDATE products
SET embedding = embedding('text-embedding-005', search_text)::vector
WHERE embedding IS NULL;
```

**Indexes** (`sql/03_indexes.sql`):

```sql
CREATE INDEX idx_products_scann ON products USING scann (embedding cosine);
CREATE INDEX idx_products_tsv   ON products USING GIN (tsv);
CREATE INDEX idx_products_sku_trgm  ON products USING GIN (sku gin_trgm_ops);
CREATE INDEX idx_products_name_trgm ON products USING GIN (name gin_trgm_ops);
CREATE INDEX idx_products_category  ON products (category);
```

**Hybrid ranking with Reciprocal Rank Fusion** (`sql/04_hybrid_search.sql`):

```sql
WITH vec AS (
  SELECT id,
         ROW_NUMBER() OVER (ORDER BY embedding <=> embedding('text-embedding-005', :q)::vector) AS r
  FROM products
  WHERE (:cat IS NULL OR category = :cat)
  ORDER BY embedding <=> embedding('text-embedding-005', :q)::vector
  LIMIT 50
),
kw AS (
  SELECT id,
         ROW_NUMBER() OVER (ORDER BY ts_rank_cd(tsv, plainto_tsquery('english', :q)) DESC) AS r
  FROM products
  WHERE tsv @@ plainto_tsquery('english', :q)
    AND (:cat IS NULL OR category = :cat)
  LIMIT 50
)
SELECT p.id, p.sku, p.name, p.brand,
       COALESCE(1.0/(60 + vec.r), 0) + COALESCE(1.0/(60 + kw.r), 0) AS rrf_score
FROM vec FULL OUTER JOIN kw USING (id)
JOIN products p ON p.id = COALESCE(vec.id, kw.id)
ORDER BY rrf_score DESC
LIMIT 10;
```

**Query routing** (`hybrid_search.py`):

1. Looks like a part number or SKU → exact match, then `pg_trgm` fuzzy match
2. Natural language → hybrid RRF with optional metadata filters (brand, category, lead-free, material)
3. Optional rerank of the top results (Vertex AI Ranking API)

### 4. RAG and enterprise search

**Use case:** *"Which valve works for 150 psi potable water and is NSF 61 certified?"* answered from spec sheets and install guides.

Pipeline (`src/rag/`):

```
PDF / text docs → structure-aware chunking (+ metadata: sku, doc type, page)
   → embeddings (AlloyDB embedding()) → doc_chunks table
   → hybrid retrieval (vector + keyword, RRF) → optional rerank
   → Gemini answer with citations
```

Production touches included:

- **Citations** (document + page) in every answer
- **Grounding check:** refuse to answer when retrieved evidence is weak
- **Row-level security** in AlloyDB (`sql/05_row_level_security.sql`), e.g. restrict supplier-confidential or pricing data by role
- **Feedback loop:** thumbs up/down stored in a `feedback` table
- Latency and token usage logged per request

---

## Evaluation (the part that proves it works)

`src/eval/golden_queries.csv` contains around 50 queries with known relevant SKUs, covering exact part numbers, typos, synonyms (`PEX` ↔ `cross-linked polyethylene`) and natural language.

```bash
make eval
```

Results table template (fill with your real numbers):

| Method | Recall@10 | MRR | NDCG@10 |
|---|---|---|---|
| Keyword only (tsvector) | _ | _ | _ |
| Vector only (ScaNN) | _ | _ | _ |
| **Hybrid (RRF)** | _ | _ | _ |

Also track before/after enrichment:

| Metric | Before | After |
|---|---|---|
| Attribute completeness | _ % | _ % |
| Duplicate rate | _ % | _ % |
| Quarantined records | _ | _ |

---

## Demo flow (5 minutes)

1. Show a dirty supplier feed and its quality scorecard
2. Show quarantine reason codes and the enrichment lift (completeness before/after)
3. Search *"3/4 brass ball valve lead free"*: compare keyword vs vector vs hybrid side by side
4. Search a part number with a typo: show the `pg_trgm` fallback
5. Ask the RAG assistant a spec question: show citations and a refusal on an out-of-scope question
6. Show the evaluation table

---

## Design decisions to talk about

- **Why AlloyDB?** Transactional data, vectors, full-text and SQL in one engine; ScaNN performance; simple governance (IAM, row-level security) versus running a separate vector DB plus Elasticsearch.
- **Why RRF?** Combines rankings without having to calibrate scores from different systems.
- **Why contracts and quarantine?** Fail loudly at ingestion; bad data never reaches search.
- **Why confidence plus review queue?** LLM output is useful but must be measurable and auditable.
- **Local-first choice:** DuckDB and Parquet stand in for BigQuery and GCS; the same logic maps directly to Dataplex, BigQuery and Cloud Run at scale.

## Scaling to production (discussion points)

- Replace local DuckDB/Parquet with GCS + BigQuery (Dataflow for streaming feeds); Cloud Composer for orchestration
- Incremental embedding refresh (only changed rows), ScaNN index tuning (`num_leaves`), read pool instances for search traffic
- Handle inventory and pricing freshness separately from catalog attributes
- CMEK, VPC Service Controls, private IP, least-privilege IAM
- CI/CD with Terraform and Cloud Build; production search monitoring (zero-result queries, click-through)

---

## Cleanup

```bash
gcloud alloydb clusters delete CLUSTER --region=REGION --force
```

## License

MIT

# ADR-0001 — Local-first pipeline; AlloyDB is the only cloud component

- **Status:** accepted
- **Date:** 2026-10-21
- **Deciders:** human
- **Related:** `README.md`, `docs/plan/F09-alloydb-foundation.md`

## Context
The project must demonstrate production-grade data engineering (quality, enrichment, hybrid
search, RAG) while staying cheap and runnable by one person on a laptop. Managed GCP services
(GCS, BigQuery, Dataflow, Composer, Vertex AI pipelines) would be realistic but add setup cost,
credentials, and monthly spend before any value is visible. AlloyDB, however, is central: hybrid
search with pgvector/ScaNN + full-text + SQL is the point of the project and has no faithful
local substitute.

## Decision
Run everything locally with DuckDB + Parquet (standing in for GCS/BigQuery/Dataflow),
Python scripts + Makefile (standing in for Composer), and Gemini/Vertex AI for LLM work.
Use **AlloyDB for PostgreSQL on GCP** for the serving layer only: vectors, `tsvector`,
`pg_trgm`, RRF hybrid search, and row-level security.

## Consequences
- **Positive:** near-zero cost until the cloud step; fast iteration; no Docker/orchestration;
  the pipeline is reproducible offline and fully testable in CI.
- **Negative / trade-offs:** local layers are a stand-in, so scale characteristics differ;
  cloud behavior (auth, RLS, index tuning) is only exercised on GCP.
- **Follow-ups:** F09/F10 are Tier C (cost + credentials). Keep the AlloyDB cluster small and
  stop/delete it when idle. Document the production mapping (GCS/BigQuery/Dataflow/Dataplex).

## Alternatives considered
- **BigQuery + Vertex AI Vector Search** — less overlap with the SQL/hybrid-search goal, two
  systems to secure and pay for.
- **Postgres + pgvector in Docker locally only** — avoids GCP entirely but drops the AlloyDB
  features (`alloydb_scann`, `google_ml_integration` `embedding()`) the project is showcasing.
- **Managed vector DB (Pinecone/Weaviate) + Elasticsearch** — more moving parts and cost; no
  single-engine governance.

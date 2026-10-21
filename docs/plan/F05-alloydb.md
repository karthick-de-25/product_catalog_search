---
feature: F05
title: AlloyDB setup, load, and embeddings
status: proposed
approved:
depends_on: [F04]
---

# F05 — AlloyDB + load + embeddings  🔴

**Goal:** create the AlloyDB serving schema and load `gold_products` with embeddings — the only
cloud component.

> 🔴 **Every step here is a critical action.** Running `make db`/`make load` needs the human's
> explicit go-ahead and an existing AlloyDB cluster + Auth Proxy. Nothing in this feature runs in
> tests or in CI.

## Slices

### Slice 1 — SQL schema + indexes   `[ ]`
- **In → out:** `sql/*.sql` → an idempotent apply script
- **Files:** `sql/01_extensions.sql`, `sql/02_schema.sql`, `sql/03_indexes.sql`,
  `src/load/apply_sql.py`, `Makefile`
- **Content:** `vector`, `alloydb_scann`, `google_ml_integration`, `pg_trgm`; `products`
  (with `embedding vector(768)`, generated `tsv`); ScaNN + GIN + trigram indexes.
- **Test:** `test_load.py::test_sql_files_exist` — the SQL files contain the required statements
  (offline check only).
- **Critical actions:** 🔴 `make db` — creates extensions/tables/indexes in AlloyDB.
- **Done when:** SQL files are reviewed and the apply script is idempotent.

### Slice 2 — Load + embeddings   `[ ]`
- **In → out:** `gold_products` → AlloyDB `products` (upsert) → `embedding` populated
- **Files:** `src/load/load_alloydb.py`, `Makefile`
- **Approach:** connect via Auth Proxy (`ENABLE_CLOUD=true` required); batched upsert; then
  `UPDATE products SET embedding = embedding('text-embedding-005', search_text)::vector
  WHERE embedding IS NULL`.
- **Test:** `test_load.py::test_build_upsert_sql` — the generated UPSERT lists the expected columns
  (no live connection).
- **Critical actions:** 🔴 `make load` — writes to AlloyDB and calls Vertex AI for embeddings
  (cost). Cap the batch.
- **Done when:** `SELECT count(*) FROM products` matches gold; no null embeddings.

## Acceptance
- [ ] `sql/` creates the schema and indexes idempotently (verified on AlloyDB, 🔴 approved).
- [ ] Gold rows load with embeddings; counts match.

## Commands
```bash
make check          # offline: SQL string checks only
make db             # 🔴 critical — AlloyDB
make load           # 🔴 critical — AlloyDB + Vertex AI
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.

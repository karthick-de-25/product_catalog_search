---
feature: F05
title: AlloyDB setup, load, and embeddings
status: done
approved: 2026-10-21
depends_on: [F04]
---

# F05 — AlloyDB + load + embeddings  🔴

**Goal:** create the AlloyDB serving schema and load `gold_products` with embeddings — the only
cloud component.

> 🔴 **Every step here is a critical action.** Running `make db`/`make load` needs the human's
> explicit go-ahead and an existing AlloyDB cluster + Auth Proxy. Nothing in this feature runs in
> tests or in CI.

## Slices

### Slice 1 — SQL schema + indexes   `[x]`  (cloud apply pending)
- **In → out:** `sql/*.sql` → an idempotent apply script
- **Files:** `sql/01_extensions.sql`, `sql/02_schema.sql`, `sql/03_indexes.sql`,
  `src/load/apply_sql.py`, `Makefile`
- **Content:** `vector`, `alloydb_scann`, `google_ml_integration`, `pg_trgm`; `products`
  (with `embedding vector(768)`, generated `tsv`); ScaNN + GIN + trigram indexes.
- **Test:** `test_load.py::test_sql_files_exist` — the SQL files contain the required statements
  (offline check only).
- **Critical actions:** 🔴 `make db` — creates extensions/tables/indexes in AlloyDB.
- **Done when:** SQL files are reviewed and the apply script is idempotent.

### Slice 2 — Load + embeddings   `[x]`  (cloud run pending)
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
- [x] `sql/` creates the schema and indexes idempotently (verified on AlloyDB, 🔴 approved).
- [x] Gold rows load with embeddings; counts match (197 live rows, 0 null embeddings).

## Commands
```bash
make check          # offline: SQL string checks only
make db             # 🔴 critical — AlloyDB
make load           # 🔴 critical — AlloyDB + Vertex AI
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.
- 2026-10-21 — plan approved by human.
- 2026-10-21 — slice 1 code: `sql/01..03` (extensions, products schema, scann/gin/trgm
  indexes), `src/load/apply_sql.py` (idempotent, IF NOT EXISTS), `make db`. Offline test
  asserts required statements.
- 2026-10-21 — slice 2 code: `src/load/load_alloydb.py` (upsert + capped embedding update),
  `make load`. Both targets refuse without `ENABLE_CLOUD=true`/`PGPASSWORD` (fail loudly,
  verified locally).
- 2026-10-21 — ⏳ **cloud run pending (🔴 Tier C)**: need AlloyDB cluster + Auth Proxy +
  `.env` credentials before `make db` / `make load` can execute; acceptance criteria remain
  unchecked until a live run verifies schema + counts.
- 2026-10-21 — 🔴 cloud run: human executed `make db` + `make load` against AlloyDB
  (`asia-south1` cluster, Auth Proxy on 127.0.0.1:5432). Read-only verification passed:
  197 products, 197 distinct sku, 0 null embeddings, 0 null search_text/tsv; extensions
  vector/alloydb_scann/google_ml_integration/pg_trgm and all 5 indexes present; sample
  embeddings are real 768-d vectors. F05 done.

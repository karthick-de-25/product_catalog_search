-- AlloyDB extensions required for hybrid search (F05).
-- Applied by `make db` — a critical (Tier: 🔴) action.
create extension if not exists vector;
create extension if not exists alloydb_scann;
create extension if not exists google_ml_integration;
create extension if not exists pg_trgm;

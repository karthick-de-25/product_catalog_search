-- Indexes for hybrid search (F05). Applied by `make db` — a critical (Tier: 🔴) action.
create index if not exists idx_products_scann     on products using scann (embedding cosine);
create index if not exists idx_products_tsv       on products using gin (tsv);
create index if not exists idx_products_sku_trgm  on products using gin (sku gin_trgm_ops);
create index if not exists idx_products_name_trgm on products using gin (name gin_trgm_ops);
create index if not exists idx_products_category  on products (category);

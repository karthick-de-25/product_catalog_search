-- Canonical serving schema (F05). Mirrors the gold model in CONTEXT.md.
-- Applied by `make db` — a critical (Tier: 🔴) action.
create table if not exists products (
    id           bigserial primary key,
    sku          text unique not null,               -- canonical identifier
    supplier_id  text,                               -- governance: which feed supplied the row
    name         text,
    description  text,
    brand        text,
    category     text,
    size_in      numeric,                            -- canonical length unit: inches
    material     text,
    pressure_psi integer,                            -- canonical pressure unit: psi
    lead_free    boolean,                            -- null = unknown, never false by default
    search_text  text,                               -- embedding + full-text source
    tsv          tsvector generated always as (to_tsvector('english', coalesce(search_text, ''))) stored,
    embedding    vector(768)                         -- text-embedding-005
);

comment on column products.supplier_id is 'supplier feed that provided this product';
comment on column products.lead_free is 'null means unknown; only positive evidence sets true';

"""Load ``gold_products`` into AlloyDB and generate embeddings (F05, slice 2).

Entry point: ``python -m src.load.load_alloydb`` (wired to ``make load``).

🔴 **Critical**: writes to AlloyDB and calls Vertex AI embeddings (cost). Refuses to run
unless ``ENABLE_CLOUD=true``. Embedding generation is capped per run by
``LLM_MAX_ROWS_PER_RUN`` and only touches rows that have no embedding yet.
"""

from __future__ import annotations

from src.config import get_settings
from src.errors import ConfigError
from src.ingest.db import connect as connect_duckdb
from src.load.apply_sql import connect_alloydb

PRODUCT_COLUMNS = (
    "sku",
    "supplier_id",
    "name",
    "description",
    "brand",
    "category",
    "size_in",
    "material",
    "pressure_psi",
    "lead_free",
    "search_text",
)


def build_upsert_sql() -> str:
    """UPSERT with a deterministic refresh of the search-relevant columns."""
    columns = ", ".join(PRODUCT_COLUMNS)
    placeholders = ", ".join("%s" for _ in PRODUCT_COLUMNS)
    return (
        f"insert into products ({columns}) values ({placeholders}) "
        "on conflict (sku) do update set "
        "search_text = excluded.search_text, "
        "brand = excluded.brand, category = excluded.category, "
        "size_in = excluded.size_in, material = excluded.material, "
        "pressure_psi = excluded.pressure_psi, lead_free = excluded.lead_free"
    )


def build_embed_sql(limit: int) -> str:
    """Embed only rows that still need it, capped at ``limit`` per run (cost guard)."""
    return (
        "with pending as ("
        "  select sku from products"
        "   where embedding is null and search_text is not null"
        f"   limit {limit}"
        ") "
        "update products set embedding = embedding('text-embedding-005', search_text)::vector "
        "where sku in (select sku from pending)"
    )


def main() -> None:
    settings = get_settings()
    if not settings.enable_cloud:
        raise ConfigError("ENABLE_CLOUD is false — refusing to write to AlloyDB")

    # Read gold from the local DuckDB catalog.
    duck = connect_duckdb(settings.duckdb_path)
    rows = duck.execute(
        "select sku, supplier_id, name, null, brand, category, size_in, material, "
        "pressure_psi, lead_free, search_text from gold_products order by sku"
    ).fetchall()
    duck.close()

    conn = connect_alloydb(settings)
    with conn.cursor() as cursor:
        cursor.executemany(build_upsert_sql(), rows)
    print(f"upserted {len(rows)} products")

    with conn.cursor() as cursor:
        cursor.execute(build_embed_sql(settings.llm_max_rows_per_run))
    print(f"embeddings generated (batch capped at {settings.llm_max_rows_per_run})")
    conn.close()


if __name__ == "__main__":
    main()

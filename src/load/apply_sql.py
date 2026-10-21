"""Apply the AlloyDB DDL in ``sql/01..03`` in order (F05, slice 1).

Entry point: ``python -m src.load.apply_sql`` (wired to ``make db``).

🔴 **Critical**: talks to a real AlloyDB cluster. Refuses to run unless ``ENABLE_CLOUD=true``
and ``PGPASSWORD`` are set. Everything uses ``IF NOT EXISTS``, so re-applying is safe.
"""

from __future__ import annotations

from pathlib import Path

import psycopg

from src.config import Settings, get_settings
from src.errors import ConfigError

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def connect_alloydb(settings: Settings) -> psycopg.Connection:
    """Open an autocommit connection to AlloyDB through the Auth Proxy."""
    if not settings.enable_cloud:
        raise ConfigError("ENABLE_CLOUD is false — refusing to touch AlloyDB")
    if settings.pgpassword is None:
        raise ConfigError("PGPASSWORD is not set")
    return psycopg.connect(
        host=settings.pghost,
        port=settings.pgport,
        user=settings.pguser,
        password=settings.pgpassword.get_secret_value(),
        dbname=settings.pgdatabase,
        autocommit=True,
    )


def main() -> None:
    settings = get_settings()
    conn = connect_alloydb(settings)
    for path in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))
        print(f"applied {path.name}")
    conn.close()
    print("AlloyDB schema ready")


if __name__ == "__main__":
    main()

"""Typed, environment-backed configuration for the pipeline.

Every tunable comes from the environment (documented in ``.env.example``). Importing this
module performs no I/O beyond optionally reading a local ``.env`` file, and never makes a
network or cloud call. Cloud behaviour is opt-in via ``ENABLE_CLOUD``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_REDACTED = "***"


class Settings(BaseSettings):
    """Resolved pipeline settings.

    Defaults are safe for offline, local-only work: cloud is disabled, database
    credentials are unset, and all paths are relative to the repository root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- local pipeline ---
    seed: int = 42
    data_dir: Path = Path("data")
    raw_dir: Path = Path("data/raw")
    reports_dir: Path = Path("data/reports")
    duckdb_path: Path = Path("data/catalog.duckdb")
    contracts_dir: Path = Path("contracts")
    log_level: str = "INFO"

    # --- cloud opt-in (off by default, per CONTEXT.md) ---
    enable_cloud: bool = False
    gcp_project: str | None = None
    gcp_region: str = "us-central1"

    # --- AlloyDB (only used when enable_cloud is true) ---
    pghost: str = "127.0.0.1"
    pgport: int = 5432
    pguser: str = "postgres"
    pgpassword: SecretStr | None = None
    pgdatabase: str = "catalog"

    # --- Vertex AI / Gemini ---
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-005"

    # --- LLM guardrails ---
    llm_max_rows_per_run: int = 500
    extraction_confidence_min: float = 0.75

    def redacted(self) -> dict[str, Any]:
        """Return a JSON-serializable view of the settings with secrets masked."""
        data: dict[str, Any] = self.model_dump(mode="json")
        if self.pgpassword is not None:
            data["pgpassword"] = _REDACTED
        return data


def get_settings() -> Settings:
    """Load settings from the environment (and a local ``.env`` when present)."""
    return Settings()


def main() -> None:
    """CLI entry point: print the resolved, redacted settings as JSON."""
    settings = get_settings()
    # This is a CLI boundary; structured `print` here is intentional (see AGENTS.md §9).
    print(json.dumps(settings.redacted(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

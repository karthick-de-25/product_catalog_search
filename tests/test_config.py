"""Slice 2: typed settings load from the environment with safe defaults."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from src.config import Settings, get_settings

_ENV_KEYS = (
    "SEED",
    "DATA_DIR",
    "DUCKDB_PATH",
    "RAW_DIR",
    "REPORTS_DIR",
    "CONTRACTS_DIR",
    "LOG_LEVEL",
    "ENABLE_CLOUD",
    "GCP_PROJECT",
    "GCP_REGION",
    "PGHOST",
    "PGPORT",
    "PGUSER",
    "PGPASSWORD",
    "PGDATABASE",
    "GEMINI_MODEL",
    "EMBEDDING_MODEL",
    "LLM_MAX_ROWS_PER_RUN",
    "EXTRACTION_CONFIDENCE_MIN",
)


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Remove every pipeline env var so defaults and overrides are deterministic."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield


def test_defaults_and_redaction(clean_env: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.seed == 42
    assert settings.enable_cloud is False
    assert settings.gcp_project is None
    assert settings.pgpassword is None
    assert settings.duckdb_path.name == "catalog.duckdb"

    redacted = settings.redacted()
    assert redacted["enable_cloud"] is False
    assert redacted["pgpassword"] is None
    # Paths serialize to strings for JSON.
    assert redacted["duckdb_path"].endswith("catalog.duckdb")


def test_env_override_and_password_redaction(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SEED", "7")
    monkeypatch.setenv("ENABLE_CLOUD", "true")
    monkeypatch.setenv("PGPASSWORD", "s3cret-value")

    settings = Settings(_env_file=None)

    assert settings.seed == 7
    assert settings.enable_cloud is True

    redacted = settings.redacted()
    assert redacted["pgpassword"] == "***"
    assert "s3cret-value" not in json.dumps(redacted)


def test_get_settings_returns_settings() -> None:
    assert isinstance(get_settings(), Settings)

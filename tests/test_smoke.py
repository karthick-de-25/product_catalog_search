"""Slice 5: end-to-end smoke checks for the foundation layer."""

from __future__ import annotations

import json

import pytest

from src.config import Settings, get_settings
from src.errors import ReasonCode

_ENV_KEYS = (
    "SEED",
    "DATA_DIR",
    "DUCKDB_PATH",
    "ENABLE_CLOUD",
    "GCP_PROJECT",
    "PGPASSWORD",
)


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_settings_defaults_with_empty_environment(clean_env: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.seed == 42
    assert settings.enable_cloud is False
    assert settings.gcp_project is None
    assert settings.pgpassword is None
    assert settings.data_dir.name == "data"


def test_redacted_settings_are_json_serializable(clean_env: None) -> None:
    payload = json.dumps(Settings(_env_file=None).redacted())
    assert "catalog.duckdb" in payload


def test_get_settings_returns_settings() -> None:
    assert isinstance(get_settings(), Settings)


def test_reason_code_set_is_closed() -> None:
    assert len(list(ReasonCode)) == 8
    assert {code.value for code in ReasonCode} >= {"MISSING_REQUIRED", "LOW_CONFIDENCE"}

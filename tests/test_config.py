"""Typed settings: safe defaults and secret redaction."""

from __future__ import annotations

import json

import pytest

from src.config import Settings

_ENV_KEYS = ("SEED", "ENABLE_CLOUD", "GCP_PROJECT", "PGPASSWORD", "DUCKDB_PATH")


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_are_local_and_offline(clean_env: None) -> None:
    settings = Settings(_env_file=None)

    assert settings.seed == 42
    assert settings.enable_cloud is False
    assert settings.gcp_project is None
    assert settings.duckdb_path.name == "catalog.duckdb"


def test_env_override_and_password_redaction(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SEED", "7")
    monkeypatch.setenv("PGPASSWORD", "topsecret")

    settings = Settings(_env_file=None)
    redacted = settings.redacted()

    assert settings.seed == 7
    assert redacted["pgpassword"] == "***"
    assert "topsecret" not in json.dumps(redacted)

"""Slice 2: logging setup is idempotent and yields named loggers."""

from __future__ import annotations

import logging

import pytest

import src.logging_utils as logging_utils
from src.logging_utils import configure_logging, get_logger


def test_configure_logging_sets_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging_utils, "_configured", False)
    configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging_utils, "_configured", False)
    configure_logging("WARNING")

    root = logging.getLogger()
    handlers_before = list(root.handlers)

    configure_logging("DEBUG")  # must be a no-op

    assert root.level == logging.WARNING
    assert list(root.handlers) == handlers_before


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("src.demo")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "src.demo"

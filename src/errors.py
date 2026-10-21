"""Shared exceptions and the closed set of data-quality reason codes.

The :class:`ReasonCode` values are defined in ``CONTEXT.md`` ("Reason codes"). A test in
``tests/test_errors.py`` parses that document and fails if this enum drifts, keeping the two
in sync. Adding or removing a code is a Tier C decision.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ReasonCode(StrEnum):
    """Closed set of quarantine/flag reason codes (see ``CONTEXT.md``)."""

    MISSING_REQUIRED = "MISSING_REQUIRED"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    INVALID_ENUM = "INVALID_ENUM"
    DUPLICATE_SKU = "DUPLICATE_SKU"
    UNIT_UNPARSEABLE = "UNIT_UNPARSEABLE"
    BROKEN_REFERENCE = "BROKEN_REFERENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class PipelineError(Exception):
    """Base class for every pipeline error, carrying structured context."""

    def __init__(self, message: str, /, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context)

    def __str__(self) -> str:
        if not self.context:
            return self.message
        details = ", ".join(f"{key}={value!r}" for key, value in sorted(self.context.items()))
        return f"{self.message} ({details})"


class ConfigError(PipelineError):
    """Invalid or missing configuration."""


class ContractError(PipelineError):
    """A data contract is missing, malformed, or violated."""


class DataQualityError(PipelineError):
    """A data-quality rule failed for a single record.

    ``reason_code`` is stored both as an attribute and in :attr:`context` so quarantine
    writers can persist it without re-deriving it.
    """

    def __init__(self, message: str, /, *, reason_code: ReasonCode, **context: Any) -> None:
        super().__init__(message, reason_code=reason_code.value, **context)
        self.reason_code = reason_code

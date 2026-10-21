"""Shared exceptions and the small, closed set of data-quality reason codes.

Reason codes are listed in ``CONTEXT.md`` and used by the quarantine table. Keep them few and
stable; changing the set is a critical change (see ``AGENTS.md`` §4).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ReasonCode(StrEnum):
    """Why a row was quarantined (see ``CONTEXT.md``)."""

    MISSING_REQUIRED = "MISSING_REQUIRED"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    DUPLICATE_SKU = "DUPLICATE_SKU"


class PipelineError(Exception):
    """Base class for pipeline errors, carrying structured context."""

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
    """A data-quality rule failed for a single record."""

    def __init__(self, message: str, /, *, reason_code: ReasonCode, **context: Any) -> None:
        super().__init__(message, reason_code=reason_code.value, **context)
        self.reason_code = reason_code

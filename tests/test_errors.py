"""Slice 3: shared errors and the closed reason-code set."""

from __future__ import annotations

import re
from pathlib import Path

from src.errors import (
    ConfigError,
    ContractError,
    DataQualityError,
    PipelineError,
    ReasonCode,
)

_CONTEXT_MD = Path(__file__).resolve().parents[1] / "CONTEXT.md"


def _reason_codes_in_context() -> set[str]:
    """Extract the closed reason-code set from the CONTEXT.md table."""
    text = _CONTEXT_MD.read_text(encoding="utf-8")
    section = text.split("## Reason codes", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\|\s*`([A-Z_]+)`", section, re.MULTILINE))


def test_reason_codes_match_context() -> None:
    """The enum is exactly the closed set documented in CONTEXT.md."""
    assert {code.value for code in ReasonCode} == _reason_codes_in_context()


def test_reason_code_count() -> None:
    assert len(list(ReasonCode)) == 8


def test_data_quality_error_carries_structured_context() -> None:
    error = DataQualityError("row rejected", reason_code=ReasonCode.MISSING_REQUIRED, sku="A-1")

    assert error.reason_code is ReasonCode.MISSING_REQUIRED
    assert error.context["sku"] == "A-1"
    assert error.context["reason_code"] == "MISSING_REQUIRED"
    assert "sku='A-1'" in str(error)


def test_error_hierarchy() -> None:
    assert issubclass(ConfigError, PipelineError)
    assert issubclass(ContractError, PipelineError)
    assert issubclass(DataQualityError, PipelineError)


def test_error_without_context_renders_plain_message() -> None:
    assert str(ConfigError("missing GCP_PROJECT")) == "missing GCP_PROJECT"

"""Reason codes and structured error context."""

from __future__ import annotations

from src.errors import DataQualityError, PipelineError, ReasonCode


def test_reason_codes_are_the_closed_set() -> None:
    assert {code.value for code in ReasonCode} == {
        "MISSING_REQUIRED",
        "TYPE_MISMATCH",
        "OUT_OF_RANGE",
        "DUPLICATE_SKU",
    }


def test_data_quality_error_carries_context() -> None:
    error = DataQualityError("row rejected", reason_code=ReasonCode.MISSING_REQUIRED, sku="A-1")

    assert error.reason_code is ReasonCode.MISSING_REQUIRED
    assert error.context["sku"] == "A-1"
    assert isinstance(error, PipelineError)
    assert "sku='A-1'" in str(error)

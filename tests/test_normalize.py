"""F04: canonical unit parsing and brand cleanup."""

from __future__ import annotations

from src.enrichment.normalize import (
    normalize_brand,
    normalize_lead_free,
    parse_pressure_psi,
    parse_size,
)


def test_parse_size_common_variants() -> None:
    assert parse_size('3/4"') == 0.75
    assert parse_size("0.75 in") == 0.75
    assert parse_size("3/4 inch") == 0.75
    assert parse_size("1 in") == 1.0
    assert parse_size("0,75 in") == 0.75
    assert parse_size("19 mm") == round(19 / 25.4, 3)


def test_parse_size_unparseable_is_none() -> None:
    assert parse_size("banana") is None
    assert parse_size("") is None
    assert parse_size(None) is None


def test_pressure_and_brand_and_lead_free() -> None:
    assert parse_pressure_psi("381") == 381
    assert parse_pressure_psi("high") is None

    assert normalize_brand("WATTS Inc.") == "Watts"
    assert normalize_brand(" watts ") == "Watts"
    assert normalize_brand("acme_valves") == "acme_valves"

    assert normalize_lead_free("True") is True
    assert normalize_lead_free("false") is False
    assert normalize_lead_free("") is None

"""Minimal enrichment: canonical units and clean brand/category values (F04).

Canonical units (CONTEXT.md): length in inches, pressure in PSI. Values that cannot be
parsed become ``None`` — the row stays in gold with unknown units (unknown ≠ false, and we
never silently invent a value).
"""

from __future__ import annotations

import re

BRAND_ALIASES = {
    "watts": "Watts",
    "watts inc.": "Watts",
    "watts inc": "Watts",
    "apollo": "Apollo",
    "apollo valves": "Apollo",
    "nibco": "NIBCO",
    "nibco inc.": "NIBCO",
    "nibco inc": "NIBCO",
    "mueller": "Mueller",
    "mueller co.": "Mueller",
    "mueller co": "Mueller",
}

_IRRELEVANT = re.compile(r"[^\d.,+-]")
_FRACTION = re.compile(r"(\d+)\s*/\s*(\d+)")


def _to_float(text: str) -> float | None:
    cleaned = _IRRELEVANT.sub("", text)
    if not cleaned:
        return None
    try:
        return float(cleaned.replace(",", "."))
    except ValueError:
        return None


def parse_size(text: str | None) -> float | None:
    """Parse a size string into **inches**. ``None`` when unparseable.

    Handles the formats our suppliers ship: ``'3/4\"'``, ``'0.75 in'``, ``'3/4 inch'``,
    ``'19 mm'``, ``'0,75 in'``.
    """
    if text is None or not text.strip():
        return None
    value = text.strip().lower()

    if "mm" in value:
        millimetres = _to_float(value)
        return round(millimetres / 25.4, 3) if millimetres is not None else None

    value = value.replace("inch", "").replace("in", "").replace('"', "").strip()
    fraction = _FRACTION.fullmatch(value)
    if fraction:
        numerator, denominator = int(fraction.group(1)), int(fraction.group(2))
        return numerator / denominator if denominator else None
    return _to_float(value)


def parse_pressure_psi(text: str | None) -> int | None:
    """Parse a pressure string into whole **PSI**. ``None`` when unparseable."""
    if text is None or not text.strip():
        return None
    number = _to_float(text)
    return int(number) if number is not None else None


def normalize_brand(raw: str | None) -> str:
    """Map known display variants (``WATTS Inc.``, ``watts``) to a canonical brand."""
    if raw is None:
        return ""
    stripped = raw.strip()
    return BRAND_ALIASES.get(stripped.lower(), stripped)


def normalize_lead_free(raw: str | None) -> bool | None:
    """Map delivery booleans to real booleans; unknown stays ``None``."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in ("true", "1"):
        return True
    if value in ("false", "0"):
        return False
    return None


def normalize_row(row: dict[str, object]) -> dict[str, object]:
    """Normalize one ``silver_products`` row into the canonical gold shape."""
    return {
        "sku": str(row["sku"]).strip(),
        "supplier_id": str(row["supplier_id"]),
        "name": str(row["name"]).strip(),
        "brand": normalize_brand(str(row["brand_raw"] or "")),
        "category": str(row["category_raw"] or "").strip(),
        "size_in": parse_size(str(row["size_raw"] or "")),
        "material": str(row["material_raw"] or "").strip().lower(),
        "pressure_psi": parse_pressure_psi(str(row["pressure_raw"] or "")),
        "lead_free": normalize_lead_free(str(row["lead_free_raw"] or "")),
    }

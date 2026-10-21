"""Pure defect injectors for the synthetic supplier feeds (F01).

Each function takes the same list of rows and a seeded RNG, mutates some rows, and returns
how many rows it changed. Rates are parameters with sensible defaults so tests can control
them. Defects are the *reason* the quality layer (F03) exists.
"""

from __future__ import annotations

import random

Row = dict[str, object]

UNIT_VARIANTS = ('3/4"', "0.75 in", "19 mm", "3/4 inch")
BRAND_VARIANTS = ("Watts", "WATTS Inc.", "watts")
REQUIRED_FIELDS = ("name", "material", "category")


def inject_units(rows: list[Row], rng: random.Random, rate: float = 0.3) -> int:
    """Rewrite ``size_raw`` in a supplier's own, non-canonical unit format."""
    changed = 0
    for row in rows:
        if rng.random() < rate:
            row["size_raw"] = rng.choice(UNIT_VARIANTS)
            changed += 1
    return changed


def inject_missing_required(rows: list[Row], rng: random.Random, rate: float = 0.1) -> int:
    """Blank out a contract-required field (-> MISSING_REQUIRED)."""
    changed = 0
    for row in rows:
        if rng.random() < rate:
            row[rng.choice(REQUIRED_FIELDS)] = ""
            changed += 1
    return changed


def inject_brand_variants(rows: list[Row], rng: random.Random, rate: float = 0.15) -> int:
    """Replace the canonical brand with one of its display variants."""
    changed = 0
    for row in rows:
        if rng.random() < rate:
            row["brand"] = rng.choice(BRAND_VARIANTS)
            changed += 1
    return changed


def inject_duplicate_skus(rows: list[Row], rng: random.Random, rate: float = 0.05) -> int:
    """Overwrite some rows' SKUs with another row's SKU (-> DUPLICATE_SKU)."""
    changed = 0
    if not rows:
        return changed
    for row in rows:
        if rng.random() < rate:
            row["sku"] = rows[rng.randrange(len(rows))]["sku"]
            changed += 1
    return changed


def inject_bad_numbers(rows: list[Row], rng: random.Random, rate: float = 0.05) -> int:
    """Put unparseable/out-of-range values into numeric fields (-> TYPE/OUT_OF_RANGE)."""
    changed = 0
    for row in rows:
        if rng.random() < rate:
            if rng.random() < 0.5:
                row["pressure_psi"] = "high"
            else:
                row["size_raw"] = "banana"
            changed += 1
    return changed

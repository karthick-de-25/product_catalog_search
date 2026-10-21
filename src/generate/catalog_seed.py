"""Controlled vocabularies and seeded, deterministic clean-product generation.

Everything here is pure: same ``seed`` in, same list of products out. The vocabularies are
also the ground truth used later by the quality layer (categories, brands, materials).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Catalog:
    """Small, realistic plumbing/PVF vocabulary."""

    categories: tuple[str, ...]
    brands: dict[str, tuple[str, ...]]  # canonical brand -> known display variants
    materials: tuple[str, ...]
    sizes_in: tuple[float, ...]
    max_pressure_psi: int


DEFAULT_CATALOG = Catalog(
    categories=("ball_valves", "gate_valves", "check_valves", "pipe", "fittings"),
    brands={
        "watts": ("Watts", "WATTS Inc.", "watts"),
        "apollo": ("Apollo", "APOLLO VALVES", "apollo valves"),
        "nibco": ("NIBCO", "Nibco Inc.", "nibco"),
        "mueller": ("Mueller", "MUELLER CO.", "mueller"),
    },
    materials=("brass", "bronze", "pvc", "copper", "stainless"),
    sizes_in=(0.5, 0.75, 1.0, 1.5, 2.0),
    max_pressure_psi=600,
)


def format_size(size_in: float) -> str:
    """Render a size as canonical-ish text, e.g. ``0.75 -> '0.75 in'``."""
    return f"{size_in:g} in"


def clean_products(seed: int, count: int, brand: str) -> list[dict[str, object]]:
    """Deterministic list of *clean* product rows for one supplier feed.

    ``brand`` is the canonical name; each row carries ``size_raw`` (readable text) plus typed
    values, so defect injectors have something realistic to corrupt.
    """
    rng = random.Random(seed)
    products: list[dict[str, object]] = []
    for i in range(count):
        size = rng.choice(DEFAULT_CATALOG.sizes_in)
        category = rng.choice(DEFAULT_CATALOG.categories)
        material = rng.choice(DEFAULT_CATALOG.materials)
        roll = rng.random()
        products.append(
            {
                "sku": f"{brand.upper()[:4]}-{i + 1:04d}",
                "name": f"{format_size(size)} {material} {category.replace('_', ' ')} for {brand}",
                "brand": brand,
                "category": category,
                "size_raw": format_size(size),
                "size_in": size,
                "material": material,
                "pressure_psi": int(rng.randint(100, DEFAULT_CATALOG.max_pressure_psi)),
                "lead_free": None if roll < 0.2 else (roll < 0.7),
                "description": "Commercial plumbing valve for potable-water applications.",
            }
        )
    return products

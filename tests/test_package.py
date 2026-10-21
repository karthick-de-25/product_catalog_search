"""Slice 1: the package skeleton imports cleanly."""

from __future__ import annotations

import src


def test_import_src() -> None:
    """`import src` works and exposes a version string."""
    assert src.__version__ == "0.1.0"

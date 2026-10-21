"""Logging helpers shared across the pipeline.

Use :func:`get_logger` at module level in every module and :func:`configure_logging`
once at process start. No ``print`` statements outside CLI entry points.
"""

from __future__ import annotations

import logging
import sys

_DEFAULT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"
_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging for the process.

    Idempotent: repeated calls after the first are no-ops, so scripts and tests can
    call this freely without duplicating handlers.
    """
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=level.upper(),
        format=_DEFAULT_FORMAT,
        stream=sys.stderr,
        force=True,
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return the module-level logger registered under ``name``."""
    return logging.getLogger(name)

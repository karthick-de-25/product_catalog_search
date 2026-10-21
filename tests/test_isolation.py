"""Slice 5: the foundation layer stays offline and cloud-free when imported.

Satisfies F00 AC4 (no cloud/app dependency imported at load time) and AC5 (importing any
``src`` module makes no network call).
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_PREFIXES = ("google.cloud", "google.genai", "vertexai", "psycopg", "streamlit")
_FOUNDATION_MODULES = ("src", "src.config", "src.errors", "src.logging_utils")


def _forbidden_loaded(modules: set[str]) -> list[str]:
    return sorted(
        name
        for name in modules
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in _FORBIDDEN_PREFIXES)
    )


def test_importing_foundation_adds_no_cloud_or_app_dependency() -> None:
    """Importing ``src`` must not newly import a cloud/app dependency.

    ``google``/``google.cloud`` namespace packages are registered at interpreter startup by a
    ``.pth`` file shipped with ``google-cloud-aiplatform``, so we compare before/after rather
    than checking the whole module table.
    """
    before = set(sys.modules)
    for name in _FOUNDATION_MODULES:
        importlib.import_module(name)

    newly_loaded = _forbidden_loaded(set(sys.modules) - before)
    assert newly_loaded == [], f"foundation import pulled in: {newly_loaded}"


def test_importing_foundation_opens_no_socket() -> None:
    """Import the foundation modules in a subprocess with outbound network calls blocked.

    An audit hook is used instead of replacing ``socket.socket`` because the latter breaks
    the standard library (``ssl`` subclasses ``socket.socket`` at import time).
    """
    script = textwrap.dedent(
        """
        import sys

        _BLOCKED = {"socket.connect", "socket.getaddrinfo", "socket.bind", "socket.sendto"}


        def _audit(event, args):
            if event in _BLOCKED:
                raise AssertionError(f"network access during import: {event}")


        sys.addaudithook(_audit)

        import src
        import src.config
        import src.errors
        import src.logging_utils
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

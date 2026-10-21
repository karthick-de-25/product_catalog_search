"""Local embedding backends for the S04 scale rehearsal (slice 3).

Offline-first: the **deterministic backend** (hash-based, fixed-dim unit vectors) needs no
model weights and no network, so CI and laptops exercise the full embed + telemetry path.
When ``sentence-transformers`` is installed, ``EMBEDDING_BACKEND=local`` uses
``all-mpnet-base-v2`` (768-d) for real semantic vectors — the model loads lazily on first
use, so importing this module is network-free.

If the dependency is missing, ``get_embedder`` returns the deterministic backend and flags
``backend_fallback=True`` **loudly** (warnings.warn + report flag) — never a silent swap.
"""

from __future__ import annotations

import hashlib
import warnings
from importlib.util import find_spec
from typing import Protocol

import numpy as np

from src.config import Settings

_DETERMINISTIC_SALT = "s04-deterministic"


class Embedder(Protocol):
    """Anything that maps texts to fixed-dimension unit vectors."""

    def encode(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicEmbedder:
    """Seeded 768-d unit vectors: deterministic and offline, but NOT semantic.

    Used as the CI/fallback backend so embedding telemetry is testable with zero weights.
    """

    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        indices = np.arange(self.dim, dtype=np.int64)
        vectors: list[list[float]] = []
        for text in texts:
            digest = np.frombuffer(
                hashlib.sha256(f"{_DETERMINISTIC_SALT}:{text}".encode("utf-8")).digest(),
                dtype=np.uint8,
            )
            seed = digest[(indices // 32) % 32].astype(np.int64)
            raw = ((seed + indices) % 256).astype(np.float64)
            norm = float(np.sqrt((raw * raw).sum())) or 1.0
            vectors.append((raw / norm).tolist())
        return vectors


class SentenceTransformerEmbedder:
    """Real semantic embeddings via sentence-transformers (lazy model load, 768-d)."""

    def __init__(self, model_name: str, dim: int) -> None:
        self.model_name = model_name
        self.dim = dim
        self._model = None

    def _load(self):  # lazy so importing this module is network-free
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # heavy import, on demand

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        rows = model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        vectors = [row.tolist() for row in rows]
        if any(len(vector) != self.dim for vector in vectors):
            raise ValueError(
                f"local model {self.model_name!r} produced dim {len(vectors[0])}, "
                f"expected {self.dim}"
            )
        return vectors


def get_embedder(settings: Settings) -> tuple[Embedder, bool]:
    """Return ``(embedder, backend_fallback)`` for ``EMBEDDING_BACKEND`` (see module doc)."""
    backend = settings.embedding_backend
    if backend == "vertex":
        raise ValueError(
            "EMBEDDING_BACKEND=vertex is the AlloyDB in-DB embedding() path — it is not "
            "available offline; S04 uses local embedding only"
        )
    if backend == "local":
        if find_spec("sentence_transformers") is not None:
            embedder = SentenceTransformerEmbedder(
                settings.local_embedding_model, settings.embedding_dim
            )
            return embedder, False
        warnings.warn(
            "sentence-transformers is not installed (run 'make setup' for semantic vectors); "
            "using deterministic fallback vectors — NOT semantic",
            stacklevel=2,
        )
        return DeterministicEmbedder(settings.embedding_dim), True
    raise ValueError(f"unknown EMBEDDING_BACKEND={backend!r}; choose local (offline) or vertex")

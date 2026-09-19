"""Embedding protocol with deterministic fake and dimension validation."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class EmbeddingError(ValueError):
    pass


class EmbeddingProvider(Protocol):
    dimension: int
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class FakeEmbedding:
    model_name = "fake-384"

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            values: list[float] = []
            seed = text.encode("utf-8")
            for index in range(self.dimension):
                digest = hashlib.sha256(seed + index.to_bytes(4, "big")).digest()
                values.append((int.from_bytes(digest[:4], "big") / 2**32) * 2 - 1)
            norm = math.sqrt(sum(value * value for value in values)) or 1
            vectors.append([value / norm for value in values])
        return vectors


def validate_embeddings(vectors: list[list[float]], dimension: int) -> None:
    if any(len(vector) != dimension for vector in vectors):
        raise EmbeddingError(f"Embedding dimension mismatch; expected {dimension}")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise EmbeddingError("Embedding contains a non-finite value")

"""Embedding protocol with deterministic fake and dimension validation."""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol

import httpx


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


class OpenAIEmbedding:
    """OpenAI-compatible embedding adapter with one fixed output dimension."""

    def __init__(self, base_url: str, api_key: str, model_name: str, dimension: int = 384) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingError("Embedding provider is not configured")
        try:
            response = httpx.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model_name, "input": texts, "dimensions": self.dimension},
                timeout=float(os.getenv("AI_EMBEDDING_TIMEOUT_SECONDS", "30")),
            )
            response.raise_for_status()
            body = response.json()
            vectors = [item["embedding"] for item in sorted(body["data"], key=lambda item: item["index"])]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError("Embedding provider request failed") from exc
        validate_embeddings(vectors, self.dimension)
        return vectors


def get_embedding_provider() -> EmbeddingProvider:
    """Use the configured provider, otherwise stay offline and deterministic."""

    api_key = os.getenv("AI_API_KEY", "").strip()
    model_name = os.getenv("AI_EMBEDDING_MODEL", "fake-384")
    dimension = int(os.getenv("AI_EMBEDDING_DIMENSION", "384"))
    if not api_key or model_name == "fake-384":
        return FakeEmbedding(dimension=dimension)
    return OpenAIEmbedding(
        base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key,
        model_name=model_name,
        dimension=dimension,
    )


def validate_embeddings(vectors: list[list[float]], dimension: int) -> None:
    if any(len(vector) != dimension for vector in vectors):
        raise EmbeddingError(f"Embedding dimension mismatch; expected {dimension}")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise EmbeddingError("Embedding contains a non-finite value")

"""Ready/current document retriever with deterministic cosine ranking."""

from __future__ import annotations

import math
from typing import Callable

from sqlalchemy import select

from db.models.rag import Document, DocumentChunk, DocumentVersion

from .embeddings import EmbeddingProvider, validate_embeddings


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


class Retriever:
    def __init__(self, session_factory: Callable, embedder: EmbeddingProvider) -> None:
        self.session_factory = session_factory
        self.embedder = embedder

    def search(self, query: str, top_k: int = 5, document_id: str | None = None) -> list[dict]:
        vector = self.embedder.embed([query])[0]
        validate_embeddings([vector], self.embedder.dimension)
        with self.session_factory() as session:
            rows = session.execute(
                select(DocumentChunk, Document)
                .join(DocumentVersion, DocumentVersion.id == DocumentChunk.document_version_id)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.status == "ready", DocumentVersion.is_current.is_(True))
            ).all()
            if document_id:
                rows = [row for row in rows if row[1].id == document_id]
            ranked = sorted(
                ((cosine(vector, list(chunk.embedding)), chunk, document) for chunk, document in rows),
                key=lambda row: (-row[0], row[1].chunk_index),
            )
            return [
                {
                    "chunk_id": chunk.id,
                    "document_id": document.id,
                    "title": document.title,
                    "score": round(score, 6),
                    "text": chunk.text,
                    "page": chunk.page,
                    "section": chunk.section,
                }
                for score, chunk, document in ranked[:top_k]
            ]

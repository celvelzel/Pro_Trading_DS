"""Citation construction and source consistency checks."""

from __future__ import annotations

import hashlib

from .schemas import DocumentChunkData


def document_citation(
    *, document_id: str, version: int, chunk_id: str, title: str, chunk: DocumentChunkData
) -> dict:
    excerpt_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
    if excerpt_hash != chunk.content_hash:
        raise ValueError("Citation excerpt hash does not match source chunk")
    return {
        "type": "document",
        "document_id": document_id,
        "version": version,
        "chunk_id": chunk_id,
        "title": title,
        "page": chunk.page,
        "section": chunk.section,
        "excerpt": chunk.text[:500],
        "content_hash": chunk.content_hash,
    }

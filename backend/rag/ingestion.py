"""Document ingestion pipeline with staged failures and atomic ready switch."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable

from sqlalchemy import select

from db.models.rag import Document, DocumentChunk, DocumentVersion, IngestionJob

from .chunking import chunk_sections
from .embeddings import EmbeddingProvider, FakeEmbedding, validate_embeddings
from .parsers.markdown import parse_markdown
from .parsers.pdf import parse_pdf
from .schemas import DocumentValidationError


def storage_path(storage_key: str) -> Path:
    root = Path(os.getenv("DOCUMENT_STORAGE_DIR", "data/documents"))
    root.mkdir(parents=True, exist_ok=True)
    return root / storage_key


def ingest_document(
    document_id: str,
    session_factory: Callable,
    embedder: EmbeddingProvider | None = None,
) -> dict[str, str]:
    embedder = embedder or FakeEmbedding()
    with session_factory() as session:
        document = session.get(Document, document_id)
        if document is None:
            return {"status": "missing", "document_id": document_id}
        version = session.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version.desc())
        )
        job = session.scalar(select(IngestionJob).where(IngestionJob.document_id == document.id).order_by(IngestionJob.created_at.desc()))
        if version is None or job is None:
            document.status = "failed"
            document.failure_reason = "INTERNAL_ERROR"
            session.commit()
            return {"status": "failed", "document_id": document_id}
        path = storage_path(document.storage_key)
        document.status = "parsing"
        job.status = "running"
        job.stage = "parsing"
        session.commit()

    try:
        content = path.read_bytes()
        sections = parse_pdf(content) if document.document_type == "pdf" else parse_markdown(content)
        with session_factory() as session:
            document = session.get(Document, document_id)
            job = session.get(IngestionJob, job.id)
            document.status = "chunking"
            job.stage = "chunking"
            session.commit()
        chunks = chunk_sections(sections)
        with session_factory() as session:
            document = session.get(Document, document_id)
            job = session.get(IngestionJob, job.id)
            document.status = "embedding"
            job.stage = "embedding"
            session.commit()
        vectors = embedder.embed([chunk.text for chunk in chunks])
        validate_embeddings(vectors, embedder.dimension)
        with session_factory() as session:
            document = session.get(Document, document_id)
            version = session.get(DocumentVersion, version.id)
            job = session.get(IngestionJob, job.id)
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                session.add(
                    DocumentChunk(
                        document_id=document.id,
                        document_version_id=version.id,
                        chunk_index=index,
                        text=chunk.text,
                        token_count=chunk.token_count,
                        page=chunk.page,
                        section=chunk.section,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        content_hash=chunk.content_hash,
                        embedding=vector,
                    )
                )
            version.status = "ready"
            version.is_current = True
            document.current_version = version.version
            document.status = "ready"
            document.embedding_model = embedder.model_name
            document.embedding_dimension = embedder.dimension
            job.status = "ready"
            job.stage = "ready"
            session.commit()
        return {"status": "ready", "document_id": document_id}
    except DocumentValidationError as exc:
        code = exc.code
    except Exception:
        code = "INTERNAL_ERROR"
    with session_factory() as session:
        document = session.get(Document, document_id)
        job = session.get(IngestionJob, job.id)
        document.status = "failed"
        document.failure_reason = code
        job.status = "failed"
        job.error_code = code
        job.stage = "failed"
        session.commit()
    return {"status": "failed", "document_id": document_id, "error_code": code}

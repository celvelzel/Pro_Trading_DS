"""Document upload, status and retrieval API."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from agent.tools.knowledge import KnowledgeSearchInput, search_knowledge_base
from api.models.documents import DocumentResponse
from db.models.rag import Document, DocumentVersion, IngestionJob
from db.session import sync_session_factory
from rag.ingestion import ingest_document, storage_path
from rag.schemas import DocumentValidationError, validate_upload

router = APIRouter()


def _dump(document: Document) -> dict[str, Any]:
    return {
        "id": document.id,
        "title": document.title,
        "document_type": document.document_type,
        "status": document.status,
        "current_version": document.current_version,
        "failure_reason": document.failure_reason,
        "content_hash": document.content_hash,
        "embedding_model": document.embedding_model,
        "embedding_dimension": document.embedding_dimension,
    }


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    try:
        document_type, content_hash = validate_upload(file.filename or "document", content, file.content_type)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc
    with sync_session_factory() as session:
        duplicate = session.scalar(select(Document).where(Document.content_hash == content_hash, Document.status != "deleted"))
        if duplicate:
            return {"document": _dump(duplicate), "duplicate": True}
        document = Document(
            title=Path(file.filename or "document").name,
            document_type=document_type,
            storage_key=f"{uuid.uuid4()}{Path(file.filename or '').suffix.lower()}",
            content_hash=content_hash,
            status="uploaded",
        )
        session.add(document)
        session.flush()
        version = DocumentVersion(document_id=document.id, version=1, content_hash=content_hash, status="uploaded")
        session.add(version)
        session.flush()
        job = IngestionJob(document_id=document.id, status="pending", idempotency_key=content_hash)
        session.add(job)
        session.commit()
        document_id = document.id
        storage_key = document.storage_key
    storage_path(storage_key).write_bytes(content)
    if os.getenv("REDIS_URL"):
        from workers.rag_tasks import ingest_document_task

        ingest_document_task.delay(document_id)
    else:
        await asyncio.to_thread(ingest_document, document_id, sync_session_factory)
    return {"document": _dump(_get(document_id)), "duplicate": False}


@router.get("")
async def list_documents():
    with sync_session_factory() as session:
        return [_dump(document) for document in session.scalars(select(Document).order_by(Document.created_at.desc()))]


@router.get("/{document_id}")
async def get_document(document_id: str):
    document = _get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _dump(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str):
    with sync_session_factory() as session:
        document = session.get(Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        document.status = "deleted"
        document.current_version = None
        session.commit()


@router.post("/search")
async def search_documents(payload: KnowledgeSearchInput):
    return search_knowledge_base(payload).model_dump(mode="json")


def _get(document_id: str) -> Document | None:
    with sync_session_factory() as session:
        document = session.get(Document, document_id)
        if document:
            session.expunge(document)
        return document

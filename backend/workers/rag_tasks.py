"""Compute queue task for document ingestion."""

from workers.celery_app import celery_app
from db.session import sync_session_factory


@celery_app.task(name="backend.workers.rag_tasks.ingest_document", queue="compute")
def ingest_document_task(document_id: str) -> dict[str, str]:
    from rag.ingestion import ingest_document

    return ingest_document(document_id, sync_session_factory)

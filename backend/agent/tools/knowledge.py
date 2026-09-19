"""Read-only knowledge search tool with document citations."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from ..schemas import Citation
from .registry import ToolSpec, default_registry


class KnowledgeSearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    document_id: str | None = None


class KnowledgeSearchOutput(BaseModel):
    results: list[dict[str, Any]]
    citations: list[Citation] = Field(default_factory=list)


def search_knowledge_base(payload: KnowledgeSearchInput, session_factory: Callable | None = None) -> KnowledgeSearchOutput:
    if session_factory is None:
        from db.session import sync_session_factory

        session_factory = sync_session_factory
    from rag.embeddings import get_embedding_provider
    from rag.retriever import Retriever

    results = Retriever(session_factory, get_embedding_provider()).search(payload.query, payload.top_k, payload.document_id)
    citations = [
        Citation(
            type="document",
            ref_id=result["chunk_id"],
            label=result["title"],
            excerpt=result["text"][:500],
            metadata={"document_id": result["document_id"], "page": result["page"], "section": result["section"]},
        )
        for result in results
    ]
    return KnowledgeSearchOutput(results=results, citations=citations)


default_registry.register(
    ToolSpec(
        name="search_knowledge_base",
        version="1",
        description="Search only ready/current trusted document chunks and return source citations.",
        input_model=KnowledgeSearchInput,
        output_model=KnowledgeSearchOutput,
        handler=search_knowledge_base,
        timeout_seconds=20,
    )
)

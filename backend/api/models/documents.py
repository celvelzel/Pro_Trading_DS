"""Document API response DTOs."""

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    document_type: str
    status: str
    current_version: int | None = None
    failure_reason: str | None = None
    content_hash: str
    embedding_model: str
    embedding_dimension: int

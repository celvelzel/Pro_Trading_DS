"""create RAG document and citation tables

Revision ID: 0002_rag
Revises: 0001_agent_platform
"""

from __future__ import annotations

from alembic import op

from backend.db.models.rag import CitationSnapshot, Document, DocumentChunk, DocumentVersion, IngestionJob

revision = "0002_rag"
down_revision = "0001_agent_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector") if bind.dialect.name == "postgresql" else None
    for table in (Document.__table__, DocumentVersion.__table__, DocumentChunk.__table__, IngestionJob.__table__, CitationSnapshot.__table__):
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (CitationSnapshot.__table__, IngestionJob.__table__, DocumentChunk.__table__, DocumentVersion.__table__, Document.__table__):
        table.drop(bind=bind, checkfirst=True)

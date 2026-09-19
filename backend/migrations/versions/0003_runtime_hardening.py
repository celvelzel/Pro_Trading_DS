"""Add optimistic versioning for explicit memories."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_runtime_hardening"
down_revision = "0002_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("memory_items")}
    if "version" not in columns:
        op.add_column("memory_items", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("memory_items")}
    if "version" in columns:
        op.drop_column("memory_items", "version")

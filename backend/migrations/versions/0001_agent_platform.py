"""create Agent conversations, runs, events and compute jobs

Revision ID: 0001_agent_platform
Revises:
"""

from __future__ import annotations

from alembic import op

from backend.db.base import Base
from backend.db.models import agent, jobs  # noqa: F401 - register all tables

revision = "0001_agent_platform"
down_revision = None
branch_labels = None
depends_on = None

# Historical ownership is fixed; future live ORM imports must not move tables here.
OWNED_TABLES = (
    'conversations', 'messages', 'conversation_summaries', 'memory_items',
    'agent_runs', 'agent_plans', 'agent_steps', 'agent_events', 'tool_calls',
    'tool_results', 'message_citations', 'jobs', 'backtest_runs',
)


def upgrade() -> None:
    """Create the W1 schema from the ORM metadata."""

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[name] for name in OWNED_TABLES])


def downgrade() -> None:
    """Drop only tables owned by this migration head."""

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=[Base.metadata.tables[name] for name in OWNED_TABLES])

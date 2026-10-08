"""Add isolated financial run, invocation, artifact and relationship tables."""
from alembic import op
from backend.db.base import Base
from backend.db.models import financial_mas  # noqa: F401

revision = '0004_financial_mas'
down_revision = '0003_runtime_hardening'
branch_labels = None
depends_on = None
OWNED_TABLES = ('financial_runs', 'financial_invocations', 'financial_artifacts', 'financial_relations')


def upgrade():
    Base.metadata.create_all(op.get_bind(), tables=[Base.metadata.tables[n] for n in OWNED_TABLES])


def downgrade():
    Base.metadata.drop_all(op.get_bind(), tables=[Base.metadata.tables[n] for n in OWNED_TABLES])

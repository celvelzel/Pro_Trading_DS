"""Persist captured live financial inputs without modifying portfolio storage."""
from alembic import op
from backend.db.base import Base
from backend.db.models import financial_mas  # noqa: F401

revision = '0005_financial_datasets'
down_revision = '0004_financial_mas'
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(op.get_bind(), tables=[Base.metadata.tables['financial_datasets']])


def downgrade():
    Base.metadata.drop_all(op.get_bind(), tables=[Base.metadata.tables['financial_datasets']])

"""Make strategy_version_id nullable in pre_execution_reviews

Revision ID: 013
Revises: 012
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'pre_execution_reviews',
        'strategy_version_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'pre_execution_reviews',
        'strategy_version_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

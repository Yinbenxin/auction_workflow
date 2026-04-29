"""Create task_configs table

Revision ID: 005
Revises: 004
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'task_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tasks', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column('attachments', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('configured_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['strategy_version_id'], ['strategy_versions.id']),
        sa.ForeignKeyConstraint(['configured_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('task_configs')

"""Create pre_execution_reviews table

Revision ID: 006
Revises: 005
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pre_execution_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('checklist', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('configurer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['strategy_version_id'], ['strategy_versions.id']),
        sa.ForeignKeyConstraint(['configurer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('pre_execution_reviews')

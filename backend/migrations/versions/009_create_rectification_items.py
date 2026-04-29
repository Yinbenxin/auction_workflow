"""Create rectification_items table

Revision ID: 009
Revises: 008
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rectification_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('retrospective_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.VARCHAR(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('measures', sa.Text(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column('evidence', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column('delay_reason', sa.Text(), nullable=True),
        sa.Column('close_reason', sa.Text(), nullable=True),
        sa.Column('confirmed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('confirmed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['retrospective_id'], ['retrospectives.id']),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id']),
        sa.ForeignKeyConstraint(['confirmed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('rectification_items')

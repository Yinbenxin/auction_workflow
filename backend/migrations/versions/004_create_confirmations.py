"""Create confirmations table

Revision ID: 004
Revises: 003
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'confirmations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('target_type', sa.VARCHAR(50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.VARCHAR(20), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('confirmed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('confirmed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['confirmed_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('confirmations')

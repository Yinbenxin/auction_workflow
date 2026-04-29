"""Create auctions table

Revision ID: 002
Revises: 001
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'auctions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.VARCHAR(200), nullable=False),
        sa.Column('auction_date', sa.Date(), nullable=False),
        sa.Column('current_phase', sa.SmallInteger(), server_default=sa.text('1'), nullable=False),
        sa.Column('phase_statuses', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('basic_info', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('history_analysis', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('version', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('auctions')

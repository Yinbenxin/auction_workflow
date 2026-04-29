"""Create strategy_versions table

Revision ID: 003
Revises: 002
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'strategy_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_code', sa.VARCHAR(50), nullable=False),
        sa.Column('version_name', sa.VARCHAR(200), nullable=False),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column('bid_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('bid_quantity', sa.Numeric(18, 2), nullable=True),
        sa.Column('bid_time_points', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column('trigger_conditions', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('fallback_plan', sa.Text(), nullable=True),
        sa.Column('applicable_scenarios', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column('scenario_strategies', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('risk_level', sa.VARCHAR(20), server_default=sa.text("'NORMAL'"), nullable=False),
        sa.Column('pre_authorized_actions', postgresql.JSONB(), nullable=True),
        sa.Column('risk_notes', sa.Text(), nullable=True),
        sa.Column('previous_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('auction_id', 'version_code', name='uq_strategy_versions_auction_version_code'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['previous_version_id'], ['strategy_versions.id']),
    )


def downgrade() -> None:
    op.drop_table('strategy_versions')

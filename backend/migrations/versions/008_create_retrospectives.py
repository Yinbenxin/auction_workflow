"""Create retrospectives table

Revision ID: 008
Revises: 007
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'retrospectives',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('basic_info', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('strategy_summary', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('execution_summary', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('transaction_result', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('deviation_analysis', sa.Text(), nullable=True),
        sa.Column('anomaly_records', sa.Text(), nullable=True),
        sa.Column('confirmation_records', sa.Text(), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('improvement_actions', sa.Text(), nullable=True),
        sa.Column('strategy_learnings', sa.Text(), nullable=True),
        sa.Column('emergency_explanation', sa.Text(), nullable=True),
        sa.Column('status', sa.VARCHAR(20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['strategy_version_id'], ['strategy_versions.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('retrospectives')

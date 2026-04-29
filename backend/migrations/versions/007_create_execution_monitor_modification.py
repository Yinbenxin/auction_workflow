"""Create execution_logs, monitor_records, modifications tables

Revision ID: 007
Revises: 006
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_number', sa.VARCHAR(50), nullable=False),
        sa.Column('triggered_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('bid_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('bid_quantity', sa.Numeric(18, 2), nullable=True),
        sa.Column('system_status', sa.VARCHAR(50), nullable=True),
        sa.Column('data_feed_status', sa.VARCHAR(50), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('logged_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['logged_by'], ['users.id']),
    )

    op.create_table(
        'monitor_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('record_type', sa.VARCHAR(20), server_default=sa.text("'normal'"), nullable=False),
        sa.Column('price_change', sa.Numeric(18, 4), nullable=True),
        sa.Column('remaining_quantity', sa.Numeric(18, 2), nullable=True),
        sa.Column('transaction_speed', sa.VARCHAR(50), nullable=True),
        sa.Column('data_feed_normal', sa.Boolean(), server_default=sa.text('TRUE'), nullable=True),
        sa.Column('system_normal', sa.Boolean(), server_default=sa.text('TRUE'), nullable=True),
        sa.Column('anomaly_type', sa.VARCHAR(100), nullable=True),
        sa.Column('anomaly_action', sa.Text(), nullable=True),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recorded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
    )

    op.create_table(
        'modifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('auction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.VARCHAR(30), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column('affected_fields', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column('before_value', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('after_value', postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('impact_scope', sa.Text(), nullable=False),
        sa.Column('risk_notes', sa.Text(), nullable=True),
        sa.Column('is_emergency', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.Column('is_pre_authorized', sa.Boolean(), nullable=True),
        sa.Column('matched_emergency_rule_id', sa.VARCHAR(100), nullable=True),
        sa.Column('deviation_reason', sa.Text(), nullable=True),
        sa.Column('post_explanation', sa.Text(), nullable=True),
        sa.Column('attachments', postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('approval_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('executed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('executed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('execution_result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id']),
        sa.ForeignKeyConstraint(['strategy_version_id'], ['strategy_versions.id']),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['executed_by'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('modifications')
    op.drop_table('monitor_records')
    op.drop_table('execution_logs')

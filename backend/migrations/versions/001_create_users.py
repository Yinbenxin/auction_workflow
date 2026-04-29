"""Create users table

Revision ID: 001
Revises:
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('username', sa.VARCHAR(50), nullable=False),
        sa.Column('hashed_password', sa.VARCHAR(255), nullable=False),
        sa.Column('full_name', sa.VARCHAR(100), nullable=False),
        sa.Column('role', sa.VARCHAR(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
    )


def downgrade() -> None:
    op.drop_table('users')

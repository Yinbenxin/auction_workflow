"""Add roles to auctions, remove role from users

Revision ID: 010
Revises: 009
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add roles JSONB column to auctions
    op.add_column(
        'auctions',
        sa.Column(
            'roles',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    # Remove role column from users (roles are now per-auction)
    op.drop_column('users', 'role')


def downgrade() -> None:
    op.add_column(
        'users',
        sa.Column('role', sa.VARCHAR(50), nullable=False, server_default='trader'),
    )
    op.drop_column('auctions', 'roles')

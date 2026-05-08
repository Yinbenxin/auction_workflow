"""Add user_roles array to users

Revision ID: 015
Revises: 014
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'user_roles',
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default='{}',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'user_roles')

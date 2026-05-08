"""Add system_role to users

Revision ID: 014
Revises: 013
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE system_role_enum AS ENUM ('root', 'user')")
    op.add_column(
        'users',
        sa.Column(
            'system_role',
            sa.Enum('root', 'user', name='system_role_enum'),
            nullable=False,
            server_default='user',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'system_role')
    op.execute("DROP TYPE system_role_enum")

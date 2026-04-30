"""Add description to auctions

Revision ID: 011
Revises: 010
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('auctions', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('auctions', 'description')

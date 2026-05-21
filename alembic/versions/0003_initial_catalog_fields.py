"""Add initial_data JSON field to seller_applications

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-21
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS so this is safe to run even if 0004 already added the column
    op.execute(
        "ALTER TABLE seller_applications ADD COLUMN IF NOT EXISTS initial_data JSONB"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE seller_applications DROP COLUMN IF EXISTS initial_data"
    )

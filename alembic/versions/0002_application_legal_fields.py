"""Add legal and auth fields to seller_applications

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seller_applications", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column("seller_applications", sa.Column("legal_name", sa.Text(), nullable=True))
    op.add_column("seller_applications", sa.Column("mfo", sa.String(10), nullable=True))
    op.add_column("seller_applications", sa.Column("account_number", sa.String(30), nullable=True))
    op.add_column("seller_applications", sa.Column("oked", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("seller_applications", "oked")
    op.drop_column("seller_applications", "account_number")
    op.drop_column("seller_applications", "mfo")
    op.drop_column("seller_applications", "legal_name")
    op.drop_column("seller_applications", "password_hash")

"""Add initial catalog and product fields to seller_applications

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seller_applications", sa.Column("initial_catalog_name", sa.Text(), nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_name", sa.Text(), nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_description", sa.Text(), nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_price", sa.BigInteger(), nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_image", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("seller_applications", "initial_product_image")
    op.drop_column("seller_applications", "initial_product_price")
    op.drop_column("seller_applications", "initial_product_description")
    op.drop_column("seller_applications", "initial_product_name")
    op.drop_column("seller_applications", "initial_catalog_name")

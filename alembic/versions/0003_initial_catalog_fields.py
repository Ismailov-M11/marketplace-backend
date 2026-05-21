"""Add initial catalog and product fields to seller_applications

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seller_applications", sa.Column("initial_catalog_name_uz",       sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_catalog_name_ru",       sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_name_uz",       sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_name_ru",       sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_description_uz",sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_description_ru",sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_sku",           sa.String(100),     nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_is_featured",   sa.Boolean(),       nullable=True, server_default="false"))
    op.add_column("seller_applications", sa.Column("initial_product_image",         sa.Text(),          nullable=True))
    op.add_column("seller_applications", sa.Column("initial_product_variants",      postgresql.JSON(),  nullable=True))


def downgrade() -> None:
    op.drop_column("seller_applications", "initial_product_variants")
    op.drop_column("seller_applications", "initial_product_image")
    op.drop_column("seller_applications", "initial_product_is_featured")
    op.drop_column("seller_applications", "initial_product_sku")
    op.drop_column("seller_applications", "initial_product_description_ru")
    op.drop_column("seller_applications", "initial_product_description_uz")
    op.drop_column("seller_applications", "initial_product_name_ru")
    op.drop_column("seller_applications", "initial_product_name_uz")
    op.drop_column("seller_applications", "initial_catalog_name_ru")
    op.drop_column("seller_applications", "initial_catalog_name_uz")

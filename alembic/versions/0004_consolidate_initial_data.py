"""Consolidate initial catalog/product columns into single initial_data JSONB

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-21
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new column — IF NOT EXISTS is safe whether 0003 added it or not
    op.execute(
        "ALTER TABLE seller_applications ADD COLUMN IF NOT EXISTS initial_data JSONB"
    )
    # Drop old individual columns if they exist (from the old version of migration 0003)
    for col in [
        "initial_catalog_name_uz",
        "initial_catalog_name_ru",
        "initial_product_name_uz",
        "initial_product_name_ru",
        "initial_product_description_uz",
        "initial_product_description_ru",
        "initial_product_sku",
        "initial_product_is_featured",
        "initial_product_image",
        "initial_product_variants",
    ]:
        op.execute(f"ALTER TABLE seller_applications DROP COLUMN IF EXISTS {col}")


def downgrade() -> None:
    op.drop_column("seller_applications", "initial_data")

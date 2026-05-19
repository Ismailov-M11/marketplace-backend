from fastapi import APIRouter, Query, UploadFile, File, status
from sqlalchemy import func, select
from python_slugify import slugify

from app.api.deps import DB, CurrentSeller, CurrentSellerUser, Paginate
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.product import Category, Product, ProductImage, ProductVariant
from app.schemas.common import PaginatedResponse
from app.schemas.product import (
    CategoryCreate, CategoryOut, CategoryUpdate,
    ProductCreate, ProductListOut, ProductOut, ProductUpdate,
    VariantCreate, VariantOut, VariantUpdate,
)

router = APIRouter()

# ── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Category).where(Category.seller_id == seller.id, Category.deleted_at.is_(None))
        .order_by(Category.sort_order)
    )
    return result.scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryCreate, db: DB, seller: CurrentSeller):
    slug = slugify(body.name_ru or body.name_uz, allow_unicode=False, separator="-")
    cat = Category(
        seller_id=seller.id,
        parent_id=body.parent_id,
        name_uz=body.name_uz,
        name_ru=body.name_ru,
        slug=slug,
        image_url=body.image_url,
        sort_order=body.sort_order,
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


@router.patch("/categories/{cat_id}", response_model=CategoryOut)
async def update_category(cat_id: int, body: CategoryUpdate, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Category).where(Category.id == cat_id, Category.seller_id == seller.id, Category.deleted_at.is_(None))
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise NotFoundError("Category not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cat, field, value)
    return cat


@router.delete("/categories/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(cat_id: int, db: DB, seller: CurrentSeller):
    from datetime import datetime, timezone
    result = await db.execute(
        select(Category).where(Category.id == cat_id, Category.seller_id == seller.id, Category.deleted_at.is_(None))
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise NotFoundError("Category not found")
    cat.deleted_at = datetime.now(timezone.utc)


# ── Products ─────────────────────────────────────────────────────────────────

@router.get("/products", response_model=PaginatedResponse[ProductListOut])
async def list_products(
    db: DB, seller: CurrentSeller, pagination: Paginate,
    q: str | None = None, category_id: int | None = None,
    is_active: bool | None = None,
):
    stmt = select(Product).where(Product.seller_id == seller.id, Product.deleted_at.is_(None))
    if q:
        stmt = stmt.where(Product.name_ru.ilike(f"%{q}%") | Product.name_uz.ilike(f"%{q}%"))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(Product.sort_order, Product.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, db: DB, seller: CurrentSeller):
    product = Product(
        seller_id=seller.id,
        category_id=body.category_id,
        name_uz=body.name_uz,
        name_ru=body.name_ru,
        description_uz=body.description_uz,
        description_ru=body.description_ru,
        sku=body.sku,
        is_featured=body.is_featured,
        sort_order=body.sort_order,
        attributes=body.attributes,
    )
    db.add(product)
    await db.flush()

    for i, v in enumerate(body.variants):
        db.add(ProductVariant(
            product_id=product.id,
            seller_id=seller.id,
            name_uz=v.name_uz,
            name_ru=v.name_ru,
            sku=v.sku,
            price=v.price,
            old_price=v.old_price,
            stock_quantity=v.stock_quantity,
            track_stock=v.track_stock,
            attributes=v.attributes,
            is_default=v.is_default or i == 0,
        ))

    await db.flush()
    await db.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.seller_id == seller.id, Product.deleted_at.is_(None))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found")
    return product


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(product_id: int, body: ProductUpdate, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.seller_id == seller.id, Product.deleted_at.is_(None))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(product, field, value)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, db: DB, seller: CurrentSeller):
    from datetime import datetime, timezone
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.seller_id == seller.id, Product.deleted_at.is_(None))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found")
    product.deleted_at = datetime.now(timezone.utc)


@router.post("/products/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
async def add_variant(product_id: int, body: VariantCreate, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.seller_id == seller.id, Product.deleted_at.is_(None))
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Product not found")

    variant = ProductVariant(
        product_id=product_id,
        seller_id=seller.id,
        name_uz=body.name_uz,
        name_ru=body.name_ru,
        sku=body.sku,
        price=body.price,
        old_price=body.old_price,
        stock_quantity=body.stock_quantity,
        track_stock=body.track_stock,
        attributes=body.attributes,
        is_default=body.is_default,
    )
    db.add(variant)
    await db.flush()
    await db.refresh(variant)
    return variant


@router.patch("/products/{product_id}/variants/{variant_id}", response_model=VariantOut)
async def update_variant(product_id: int, variant_id: int, body: VariantUpdate, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
            ProductVariant.seller_id == seller.id,
            ProductVariant.deleted_at.is_(None),
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise NotFoundError("Variant not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(variant, field, value)
    return variant

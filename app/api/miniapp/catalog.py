from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentCustomer, Paginate
from app.core.exceptions import NotFoundError
from app.models.product import Category, Product, ProductVariant
from app.schemas.common import PaginatedResponse
from app.schemas.product import CategoryOut, ProductListOut, ProductOut

router = APIRouter()


@router.get("/catalog/categories", response_model=list[CategoryOut])
async def get_categories(customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Category).where(
            Category.seller_id == customer.seller_id,
            Category.is_active == True,
            Category.deleted_at.is_(None),
        ).order_by(Category.sort_order)
    )
    return result.scalars().all()


@router.get("/catalog/products", response_model=PaginatedResponse[ProductListOut])
async def get_products(
    customer: CurrentCustomer,
    db: DB,
    pagination: Paginate,
    category_id: int | None = None,
    q: str | None = None,
):
    stmt = (
        select(Product)
        .options(selectinload(Product.variants), selectinload(Product.images))
        .where(
            Product.seller_id == customer.seller_id,
            Product.is_active == True,
            Product.deleted_at.is_(None),
        )
    )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if q:
        stmt = stmt.where(Product.name_ru.ilike(f"%{q}%") | Product.name_uz.ilike(f"%{q}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(Product.is_featured.desc(), Product.sort_order).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)

    return PaginatedResponse(items=result.scalars().all(), total=total, page=pagination.page, limit=pagination.limit)


@router.get("/catalog/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.variants), selectinload(Product.images))
        .where(
            Product.id == product_id,
            Product.seller_id == customer.seller_id,
            Product.is_active == True,
            Product.deleted_at.is_(None),
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product not found")
    return product


@router.get("/catalog/featured", response_model=list[ProductListOut])
async def get_featured(customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.variants), selectinload(Product.images))
        .where(
            Product.seller_id == customer.seller_id,
            Product.is_active == True,
            Product.is_featured == True,
            Product.deleted_at.is_(None),
        )
        .limit(20)
    )
    return result.scalars().all()

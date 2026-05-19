from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DB, CurrentAdmin, Paginate
from app.core.exceptions import NotFoundError
from app.core.security import create_access_token
from app.models.seller import Seller, SellerUser
from app.schemas.common import PaginatedResponse
from app.schemas.seller import SellerOut, SellerUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SellerOut])
async def list_sellers(
    db: DB,
    admin: CurrentAdmin,
    pagination: Paginate,
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
):
    stmt = select(Seller).where(Seller.deleted_at.is_(None))
    if q:
        stmt = stmt.where(
            Seller.company_name.ilike(f"%{q}%") | Seller.slug.ilike(f"%{q}%")
        )
    if status_filter:
        stmt = stmt.where(Seller.status == status_filter)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    stmt = stmt.order_by(Seller.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{seller_id}", response_model=SellerOut)
async def get_seller(seller_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None)))
    seller = result.scalar_one_or_none()
    if not seller:
        raise NotFoundError("Seller not found")
    return seller


@router.patch("/{seller_id}", response_model=SellerOut)
async def update_seller(seller_id: int, body: SellerUpdate, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Seller).where(Seller.id == seller_id, Seller.deleted_at.is_(None)))
    seller = result.scalar_one_or_none()
    if not seller:
        raise NotFoundError("Seller not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(seller, field, value)

    return seller


@router.post("/{seller_id}/suspend")
async def suspend_seller(seller_id: int, db: DB, admin: CurrentAdmin, reason: str = ""):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise NotFoundError("Seller not found")
    seller.status = "suspended"
    seller.suspended_reason = reason
    return {"message": "Seller suspended"}


@router.post("/{seller_id}/activate")
async def activate_seller(seller_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise NotFoundError("Seller not found")
    seller.status = "active"
    seller.suspended_reason = None
    return {"message": "Seller activated"}


@router.post("/{seller_id}/impersonate")
async def impersonate_seller(seller_id: int, db: DB, admin: CurrentAdmin):
    """Returns a temporary seller JWT for the owner of the given seller."""
    result = await db.execute(
        select(SellerUser).where(
            SellerUser.seller_id == seller_id,
            SellerUser.role == "owner",
            SellerUser.is_active == True,
        )
    )
    owner = result.scalar_one_or_none()
    if not owner:
        raise NotFoundError("Seller owner not found")

    token = create_access_token({
        "sub": owner.id, "type": "seller", "role": owner.role, "seller_id": seller_id,
        "impersonated_by": admin.id,
    })
    return {"access_token": token, "token_type": "bearer"}

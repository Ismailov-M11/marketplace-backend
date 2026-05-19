from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentSeller, Paginate
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.order import Order, OrderStatusHistory
from app.schemas.common import PaginatedResponse
from app.schemas.order import OrderListOut, OrderOut, UpdateOrderStatus

router = APIRouter()

VALID_TRANSITIONS: dict[str, list[str]] = {
    "new": ["confirmed", "cancelled"],
    "confirmed": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["shipped", "cancelled"],
    "shipped": ["delivered", "cancelled"],
    "delivered": ["refunded"],
    "cancelled": [],
    "refunded": [],
}


@router.get("", response_model=PaginatedResponse[OrderListOut])
async def list_orders(
    db: DB,
    seller: CurrentSeller,
    pagination: Paginate,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = None,
):
    stmt = select(Order).where(Order.seller_id == seller.id)
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    if q:
        stmt = stmt.where(
            Order.order_number.ilike(f"%{q}%") |
            Order.customer_name.ilike(f"%{q}%") |
            Order.customer_phone.ilike(f"%{q}%")
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(Order.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)

    return PaginatedResponse(items=result.scalars().all(), total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.status_history))
        .where(Order.id == order_id, Order.seller_id == seller.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Order not found")
    return order


@router.patch("/{order_id}/status")
async def update_order_status(order_id: int, body: UpdateOrderStatus, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.seller_id == seller.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Order not found")

    if body.status not in VALID_TRANSITIONS.get(order.status, []):
        raise BadRequestError(f"Cannot transition from '{order.status}' to '{body.status}'")

    now = datetime.now(timezone.utc)
    db.add(OrderStatusHistory(
        order_id=order.id,
        seller_id=seller.id,
        from_status=order.status,
        to_status=body.status,
        changed_by=f"seller:{seller.id}",
        note=body.note,
    ))

    order.status = body.status
    # Set timestamp fields
    if body.status == "confirmed":
        order.confirmed_at = now
    elif body.status == "shipped":
        order.shipped_at = now
    elif body.status == "delivered":
        order.delivered_at = now
    elif body.status == "cancelled":
        order.cancelled_at = now

    return {"message": f"Order status updated to {body.status}"}


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, db: DB, seller: CurrentSeller, reason: str = ""):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.seller_id == seller.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Order not found")
    if order.status in ("delivered", "cancelled", "refunded"):
        raise BadRequestError("Cannot cancel this order")

    db.add(OrderStatusHistory(
        order_id=order.id, seller_id=seller.id,
        from_status=order.status, to_status="cancelled",
        changed_by=f"seller:{seller.id}", note=reason,
    ))
    order.status = "cancelled"
    order.cancel_reason = reason
    order.cancelled_at = datetime.now(timezone.utc)
    return {"message": "Order cancelled"}

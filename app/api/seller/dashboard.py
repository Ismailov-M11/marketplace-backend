from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DB, CurrentSeller
from app.models.order import Order
from app.models.product import Product
from app.models.customer import Customer

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(db: DB, seller: CurrentSeller):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    async def order_stats(since):
        result = await db.execute(
            select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
            .where(Order.seller_id == seller.id, Order.created_at >= since, Order.status != "cancelled")
        )
        return result.one()

    today_count, today_revenue = await order_stats(today_start)
    week_count, week_revenue = await order_stats(week_start)
    month_count, month_revenue = await order_stats(month_start)

    new_orders = (await db.execute(
        select(func.count(Order.id)).where(Order.seller_id == seller.id, Order.status == "new")
    )).scalar() or 0

    total_products = (await db.execute(
        select(func.count(Product.id)).where(Product.seller_id == seller.id, Product.deleted_at.is_(None))
    )).scalar() or 0

    total_customers = (await db.execute(
        select(func.count(Customer.id)).where(Customer.seller_id == seller.id)
    )).scalar() or 0

    return {
        "today": {"orders": today_count, "revenue": today_revenue},
        "week": {"orders": week_count, "revenue": week_revenue},
        "month": {"orders": month_count, "revenue": month_revenue},
        "new_orders": new_orders,
        "total_products": total_products,
        "total_customers": total_customers,
    }

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DB, CurrentAdmin
from app.models.bot import Bot
from app.models.order import Order
from app.models.seller import Seller

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: DB, admin: CurrentAdmin):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    active_sellers = (await db.execute(
        select(func.count()).where(Seller.is_active == True)
    )).scalar() or 0

    active_bots = (await db.execute(
        select(func.count()).where(Bot.is_active == True)
    )).scalar() or 0

    today_orders = (await db.execute(
        select(func.count()).where(Order.created_at >= today_start)
    )).scalar() or 0

    return {
        "active_sellers": active_sellers,
        "active_bots": active_bots,
        "today_orders": today_orders,
    }

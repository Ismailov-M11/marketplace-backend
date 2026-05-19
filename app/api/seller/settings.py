from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentSeller
from app.core.exceptions import NotFoundError
from app.models.bot import Bot, BotSettings
from app.schemas.bot import BotSettingsOut, BotSettingsUpdate

router = APIRouter()


@router.get("/settings")
async def get_settings(db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Bot).options(selectinload(Bot.settings)).where(Bot.seller_id == seller.id, Bot.is_active == True)
    )
    bot = result.scalar_one_or_none()
    if not bot:
        return {"bot": None}
    return {"bot": bot.settings}


@router.patch("/settings/bot", response_model=BotSettingsOut)
async def update_bot_settings(body: BotSettingsUpdate, db: DB, seller: CurrentSeller):
    result = await db.execute(
        select(Bot).options(selectinload(Bot.settings)).where(Bot.seller_id == seller.id, Bot.is_active == True)
    )
    bot = result.scalar_one_or_none()
    if not bot or not bot.settings:
        raise NotFoundError("Bot settings not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(bot.settings, field, value)

    return bot.settings

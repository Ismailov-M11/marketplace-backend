from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DB, CurrentAdmin, Paginate
from app.core.exceptions import NotFoundError
from app.core.security import decrypt_token, generate_webhook_secret
from app.models.bot import Bot
from app.schemas.bot import BotOut
from app.schemas.common import PaginatedResponse
import httpx

router = APIRouter()


@router.get("", response_model=PaginatedResponse[BotOut])
async def list_bots(db: DB, admin: CurrentAdmin, pagination: Paginate):
    stmt = select(Bot)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    result = await db.execute(stmt.order_by(Bot.created_at.desc()).offset(pagination.offset).limit(pagination.limit))
    return PaginatedResponse(items=result.scalars().all(), total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{bot_id}", response_model=BotOut)
async def get_bot(bot_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise NotFoundError("Bot not found")
    return bot


@router.post("/{bot_id}/check-health")
async def check_bot_health(bot_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise NotFoundError("Bot not found")

    token = decrypt_token(bot.token_encrypted)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
    return resp.json()


@router.post("/{bot_id}/set-webhook")
async def set_webhook(bot_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise NotFoundError("Bot not found")

    token = decrypt_token(bot.token_encrypted)
    from app.settings import settings
    base_url = settings.APP_ALLOWED_ORIGINS[0] if settings.APP_ALLOWED_ORIGINS else "https://api.marketplace.uz"
    webhook_url = f"{base_url}/webhook/{bot.id}/{bot.webhook_secret}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url, "secret_token": bot.webhook_secret},
        )
    bot.webhook_url = webhook_url
    return resp.json()


@router.post("/{bot_id}/rotate-secret")
async def rotate_webhook_secret(bot_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise NotFoundError("Bot not found")

    new_secret = generate_webhook_secret()
    token = decrypt_token(bot.token_encrypted)

    from app.settings import settings
    base_url = settings.APP_ALLOWED_ORIGINS[0] if settings.APP_ALLOWED_ORIGINS else "https://api.marketplace.uz"
    new_url = f"{base_url}/webhook/{bot.id}/{new_secret}"

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": new_url, "secret_token": new_secret},
        )

    bot.webhook_secret = new_secret
    bot.webhook_url = new_url
    return {"message": "Webhook secret rotated"}

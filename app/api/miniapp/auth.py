import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import create_access_token, decrypt_token
from app.models.bot import Bot, BotSettings
from app.models.customer import Customer
from app.settings import settings

router = APIRouter()


def validate_telegram_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> bool:
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return False

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return False

    try:
        auth_date = int(parsed.get("auth_date", 0))
    except ValueError:
        return False

    if time.time() - auth_date > max_age:
        return False

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed_hash, received_hash)


class InitPayload(BaseModel):
    bot_id: int
    init_data: str


@router.post("/init")
async def miniapp_init(payload: InitPayload, db: DB):
    result = await db.execute(select(Bot).where(Bot.id == payload.bot_id, Bot.is_active == True))
    bot = result.scalar_one_or_none()
    if not bot:
        raise NotFoundError("Bot not found")

    token = decrypt_token(bot.token_encrypted)

    # In dev mode, skip initData validation
    if not settings.is_development:
        if not validate_telegram_init_data(payload.init_data, token):
            raise ForbiddenError("Invalid initData signature")

    # Parse user from initData
    tg_user = {}
    try:
        parsed = dict(parse_qsl(payload.init_data))
        user_json = parsed.get("user", "{}")
        tg_user = json.loads(user_json)
    except Exception:
        if not settings.is_development:
            raise BadRequestError("Failed to parse initData")
        tg_user = {"id": 0, "first_name": "Test", "language_code": "uz"}

    tg_user_id = tg_user.get("id", 0)
    full_name = f"{tg_user.get('first_name', '')} {tg_user.get('last_name', '')}".strip()
    language = tg_user.get("language_code", "uz")[:2]

    # Upsert customer
    cust_result = await db.execute(
        select(Customer).where(
            Customer.seller_id == bot.seller_id,
            Customer.telegram_user_id == tg_user_id,
        )
    )
    customer = cust_result.scalar_one_or_none()
    if customer:
        customer.full_name = full_name or customer.full_name
        customer.telegram_username = tg_user.get("username") or customer.telegram_username
        customer.language = language
    else:
        customer = Customer(
            seller_id=bot.seller_id,
            telegram_user_id=tg_user_id,
            telegram_username=tg_user.get("username"),
            full_name=full_name or None,
            language=language,
        )
        db.add(customer)

    await db.flush()
    await db.refresh(customer)

    # Get bot settings for theme
    settings_result = await db.execute(select(BotSettings).where(BotSettings.bot_id == bot.id))
    bot_settings = settings_result.scalar_one_or_none()

    jwt_token = create_access_token({
        "sub": customer.id,
        "type": "miniapp",
        "customer_id": customer.id,
        "seller_id": bot.seller_id,
        "bot_id": bot.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    })

    theme = {}
    if bot_settings:
        theme = {
            "primary_color": bot_settings.brand_primary_color,
            "accent_color": bot_settings.brand_accent_color,
            "logo_url": bot_settings.brand_logo_url,
            "banner_url": bot_settings.brand_banner_url,
        }

    return {
        "jwt": jwt_token,
        # Convenience top-level fields for frontend
        "seller_id": bot.seller_id,
        "customer_id": customer.id,
        "bot_id": bot.id,
        "customer": {
            "id": customer.id,
            "full_name": customer.full_name,
            "phone": customer.phone,
            "language": customer.language,
        },
        "seller": {
            "id": bot.seller_id,
        },
        "theme": theme,
        "settings": {
            "payment_methods": bot_settings.payment_methods if bot_settings else ["cash"],
            "delivery_methods": bot_settings.delivery_methods if bot_settings else ["courier"],
            "min_order_amount": bot_settings.min_order_amount if bot_settings else 0,
            "delivery_fee": bot_settings.delivery_fee if bot_settings else 0,
            "currency": bot_settings.currency if bot_settings else "UZS",
        },
    }


class DevAuthPayload(BaseModel):
    bot_id: int = 1


@router.post("/dev-auth")
async def dev_auth(payload: DevAuthPayload, db: DB):
    """Development-only endpoint — skips initData validation."""
    if not settings.is_development:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Dev auth only available in development mode")

    result = await db.execute(select(Bot).where(Bot.id == payload.bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        # Return a minimal mock response if no bot exists in dev DB
        from app.core.security import create_access_token
        token = create_access_token({
            "sub": 0, "type": "miniapp",
            "customer_id": 0, "seller_id": 0, "bot_id": payload.bot_id,
        })
        return {
            "jwt": token,
            "seller_id": 0, "customer_id": 0, "bot_id": payload.bot_id,
            "customer": {"id": 0, "full_name": "Dev User", "phone": None, "language": "uz"},
            "theme": {"primary_color": "#2563eb"},
            "settings": {"payment_methods": ["cash"], "delivery_methods": ["courier"], "min_order_amount": 0, "delivery_fee": 0, "currency": "UZS"},
        }

    customer_result = await db.execute(
        select(Customer).where(Customer.seller_id == bot.seller_id, Customer.telegram_user_id == 0)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        customer = Customer(
            seller_id=bot.seller_id,
            telegram_user_id=0,
            full_name="Dev User",
            language="uz",
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)

    settings_result = await db.execute(select(BotSettings).where(BotSettings.bot_id == bot.id))
    bot_settings = settings_result.scalar_one_or_none()

    from app.core.security import create_access_token
    from datetime import timedelta
    jwt_token = create_access_token({
        "sub": customer.id, "type": "miniapp",
        "customer_id": customer.id, "seller_id": bot.seller_id, "bot_id": bot.id,
    })

    theme = {}
    if bot_settings:
        theme = {"primary_color": bot_settings.brand_primary_color}

    return {
        "jwt": jwt_token,
        "seller_id": bot.seller_id,
        "customer_id": customer.id,
        "bot_id": bot.id,
        "customer": {"id": customer.id, "full_name": customer.full_name, "phone": customer.phone, "language": customer.language},
        "theme": theme,
        "settings": {
            "payment_methods": bot_settings.payment_methods if bot_settings else ["cash"],
            "delivery_methods": bot_settings.delivery_methods if bot_settings else ["courier"],
            "min_order_amount": bot_settings.min_order_amount if bot_settings else 0,
            "delivery_fee": bot_settings.delivery_fee if bot_settings else 0,
            "currency": "UZS",
        },
    }

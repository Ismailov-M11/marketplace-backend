import hmac as _hmac
from contextlib import asynccontextmanager

import sentry_sdk
from aiogram import Bot
from aiogram.types import Update
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.database import engine
from app.core.exceptions import AppException
from app.core.logging import setup_logging, get_logger
from app.core.redis import close_redis
from app.settings import settings

# Import all models so Alembic can detect them
import app.models  # noqa: F401

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
    logger.info("Application starting", env=settings.APP_ENV)
    yield
    await close_redis()
    await engine.dispose()
    logger.info("Application shutdown")


app = FastAPI(
    title="Marketplace Bot Platform API",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_ALLOWED_ORIGINS + [settings.MINIAPP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.__class__.__name__.upper(), "message": exc.detail}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

from app.api.public import health, applications as pub_applications
from app.api.admin import auth as admin_auth, applications as admin_apps, sellers, bots
from app.api.seller import auth as seller_auth, catalog, orders, settings as seller_settings, dashboard
from app.api.miniapp import auth as miniapp_auth, catalog as miniapp_catalog, cart as miniapp_cart, checkout as miniapp_checkout, orders as miniapp_orders

PREFIX = "/api/v1"

# Public
app.include_router(health.router, prefix=f"{PREFIX}/public", tags=["Public"])
app.include_router(pub_applications.router, prefix=f"{PREFIX}/public", tags=["Public"])

# Admin
app.include_router(admin_auth.router, prefix=f"{PREFIX}/admin/auth", tags=["Admin Auth"])
app.include_router(admin_apps.router, prefix=f"{PREFIX}/admin/applications", tags=["Admin Applications"])
app.include_router(sellers.router, prefix=f"{PREFIX}/admin/sellers", tags=["Admin Sellers"])
app.include_router(bots.router, prefix=f"{PREFIX}/admin/bots", tags=["Admin Bots"])

# Seller
app.include_router(seller_auth.router, prefix=f"{PREFIX}/seller/auth", tags=["Seller Auth"])
app.include_router(dashboard.router, prefix=f"{PREFIX}/seller", tags=["Seller Dashboard"])
app.include_router(catalog.router, prefix=f"{PREFIX}/seller", tags=["Seller Catalog"])
app.include_router(orders.router, prefix=f"{PREFIX}/seller/orders", tags=["Seller Orders"])
app.include_router(seller_settings.router, prefix=f"{PREFIX}/seller", tags=["Seller Settings"])

# Mini App
app.include_router(miniapp_auth.router, prefix=f"{PREFIX}/miniapp", tags=["Mini App Auth"])
app.include_router(miniapp_catalog.router, prefix=f"{PREFIX}/miniapp", tags=["Mini App Catalog"])
app.include_router(miniapp_cart.router, prefix=f"{PREFIX}/miniapp", tags=["Mini App Cart"])
app.include_router(miniapp_checkout.router, prefix=f"{PREFIX}/miniapp", tags=["Mini App Checkout"])
app.include_router(miniapp_orders.router, prefix=f"{PREFIX}/miniapp", tags=["Mini App Orders"])


# ── Telegram webhooks ─────────────────────────────────────────────────────────

@app.post("/webhook/{bot_id}/{secret}")
async def telegram_webhook(bot_id: int, secret: str, request: Request):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.bot import Bot as BotModel
    from app.core.security import decrypt_token
    from app.bots.dispatcher import get_dispatcher

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BotModel).where(BotModel.id == bot_id, BotModel.is_active == True)
        )
        bot_obj = result.scalar_one_or_none()

    if not bot_obj:
        raise HTTPException(status_code=404)

    # Constant-time comparison
    if not _hmac.compare_digest(secret, bot_obj.webhook_secret):
        raise HTTPException(status_code=403)

    token = decrypt_token(bot_obj.token_encrypted)
    bot = Bot(token=token)

    update_data = await request.json()
    update = Update.model_validate(update_data)

    dp = get_dispatcher()
    await dp.feed_update(bot, update)

    return {"ok": True}

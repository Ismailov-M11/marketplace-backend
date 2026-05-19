from datetime import datetime, timezone

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select, update

from app.api.deps import DB, CurrentAdmin, Paginate
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import encrypt_token, generate_temp_password, generate_webhook_secret, hash_password
from app.models.admin_user import AdminUser
from app.models.seller import Seller, SellerApplication, SellerUser
from app.models.bot import Bot, BotSettings
from app.schemas.common import PaginatedResponse
from app.schemas.seller import ApplicationApprove, ApplicationOut, ApplicationReject
from app.utils.slug import make_slug
import httpx

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ApplicationOut])
async def list_applications(
    db: DB,
    admin: CurrentAdmin,
    pagination: Paginate,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = None,
):
    stmt = select(SellerApplication)
    if status_filter:
        stmt = stmt.where(SellerApplication.status == status_filter)
    if q:
        stmt = stmt.where(
            SellerApplication.company_name.ilike(f"%{q}%") |
            SellerApplication.full_name.ilike(f"%{q}%") |
            SellerApplication.phone.ilike(f"%{q}%")
        )

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar() or 0

    stmt = stmt.order_by(SellerApplication.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(application_id: int, db: DB, admin: CurrentAdmin):
    result = await db.execute(select(SellerApplication).where(SellerApplication.id == application_id))
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application not found")
    return app


@router.post("/{application_id}/approve", status_code=status.HTTP_201_CREATED)
async def approve_application(
    application_id: int, body: ApplicationApprove, db: DB, admin: CurrentAdmin
):
    result = await db.execute(
        select(SellerApplication).where(
            SellerApplication.id == application_id,
            SellerApplication.status.in_(["pending", "in_review"])
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application not found or already processed")

    # Validate bot token with Telegram
    async with httpx.AsyncClient() as client:
        tg_resp = await client.get(f"https://api.telegram.org/bot{body.telegram_token}/getMe")
        if not tg_resp.is_success or not tg_resp.json().get("ok"):
            raise BadRequestError("Invalid Telegram bot token")
        bot_info = tg_resp.json()["result"]

    # Create seller
    seller_slug = make_slug(body.username.replace("bot", "").replace("_bot", ""))
    seller = Seller(
        slug=seller_slug,
        company_name=app.company_name,
        display_name=app.company_name,
        inn=app.inn,
        phone=app.phone,
        email=app.email,
        status="active",
        plan=body.plan,
        application_id=app.id,
    )
    db.add(seller)
    await db.flush()

    # Create owner user
    temp_password = body.owner_password or generate_temp_password()
    owner = SellerUser(
        seller_id=seller.id,
        email=app.email,
        phone=app.phone,
        full_name=app.full_name,
        password_hash=hash_password(temp_password),
        role="owner",
        must_change_password=not bool(body.owner_password),
    )
    db.add(owner)

    # Encrypt and save bot
    webhook_secret = generate_webhook_secret()
    from app.settings import settings
    webhook_url = f"https://{(settings.allowed_origins[0] if settings.allowed_origins else 'api.marketplace.uz').replace('http://', '').replace('https://', '')}/webhook/{0}/{webhook_secret}"

    bot = Bot(
        seller_id=seller.id,
        telegram_bot_id=bot_info["id"],
        username=bot_info["username"],
        title=bot_info["first_name"],
        token_encrypted=encrypt_token(body.telegram_token),
        webhook_secret=webhook_secret,
        webhook_url=webhook_url,
        is_active=True,
    )
    db.add(bot)
    await db.flush()

    # Fix webhook URL with real bot id
    bot.webhook_url = f"/webhook/{bot.id}/{webhook_secret}"

    # Default bot settings
    db.add(BotSettings(
        bot_id=bot.id,
        default_language="uz",
        enabled_languages=["uz", "ru"],
        currency="UZS",
        payment_methods=["cash"],
        delivery_methods=["courier", "pickup"],
        min_order_amount=0,
        delivery_fee=0,
    ))

    # Update application
    app.status = "approved"
    app.seller_id = seller.id
    app.reviewed_by = admin.id
    app.reviewed_at = datetime.now(timezone.utc)

    await db.flush()

    # Register webhook in background (don't fail if Telegram is down)
    try:
        async with httpx.AsyncClient() as client:
            from app.settings import settings as s
            base_url = s.allowed_origins[0] if s.allowed_origins else "https://api.marketplace.uz"
            await client.post(
                f"https://api.telegram.org/bot{body.telegram_token}/setWebhook",
                json={"url": f"{base_url}/webhook/{bot.id}/{webhook_secret}", "secret_token": webhook_secret},
            )
    except Exception:
        pass

    return {
        "seller_id": seller.id,
        "bot_id": bot.id,
        "temp_password": temp_password if not body.owner_password else None,
        "message": "Application approved. Seller and bot created.",
    }


@router.post("/{application_id}/reject")
async def reject_application(
    application_id: int, body: ApplicationReject, db: DB, admin: CurrentAdmin
):
    result = await db.execute(
        select(SellerApplication).where(
            SellerApplication.id == application_id,
            SellerApplication.status.in_(["pending", "in_review"])
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        raise NotFoundError("Application not found or already processed")

    app.status = "rejected"
    app.rejected_reason = body.reason
    app.reviewed_by = admin.id
    app.reviewed_at = datetime.now(timezone.utc)

    return {"message": "Application rejected"}

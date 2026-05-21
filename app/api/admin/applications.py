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

    # Use password from application if available, otherwise admin-provided or temp
    if app.password_hash and not body.owner_password:
        owner_hash = app.password_hash
        temp_password = None
        must_change = False
    else:
        temp_password = body.owner_password or generate_temp_password()
        owner_hash = hash_password(temp_password)
        must_change = not bool(body.owner_password)

    owner = SellerUser(
        seller_id=seller.id,
        email=app.email,
        phone=app.phone,
        full_name=app.full_name,
        password_hash=owner_hash,
        role="owner",
        must_change_password=must_change,
    )
    db.add(owner)

    # Encrypt and save bot
    webhook_secret = generate_webhook_secret()
    from app.settings import settings

    bot = Bot(
        seller_id=seller.id,
        telegram_bot_id=bot_info["id"],
        username=bot_info["username"],
        title=bot_info["first_name"],
        token_encrypted=encrypt_token(body.telegram_token),
        webhook_secret=webhook_secret,
        webhook_url="",
        is_active=True,
    )
    db.add(bot)
    await db.flush()

    bot.webhook_url = f"{settings.backend_url_clean}/webhook/{bot.id}/{webhook_secret}"

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

    # Create initial catalog + product if submitted with application
    d = app.initial_data or {}
    if d.get("catalog_name_uz") and d.get("product_name_uz"):
        import re
        from app.models.product import Category, Product, ProductVariant, ProductImage

        cat_name_uz = d["catalog_name_uz"]
        cat_name_ru = d.get("catalog_name_ru") or cat_name_uz
        cat_slug = re.sub(r"[^a-z0-9]+", "-", cat_name_ru.lower().strip()).strip("-") or "catalog"
        category = Category(
            seller_id=seller.id,
            name_uz=cat_name_uz,
            name_ru=cat_name_ru,
            slug=cat_slug,
            is_active=True,
        )
        db.add(category)
        await db.flush()

        product = Product(
            seller_id=seller.id,
            category_id=category.id,
            name_uz=d["product_name_uz"],
            name_ru=d.get("product_name_ru") or d["product_name_uz"],
            description_uz=d.get("product_description_uz"),
            description_ru=d.get("product_description_ru") or d.get("product_description_uz"),
            sku=d.get("product_sku"),
            is_featured=bool(d.get("product_is_featured", False)),
            is_active=True,
        )
        db.add(product)
        await db.flush()

        variants = d.get("product_variants") or []
        for idx, v in enumerate(variants):
            db.add(ProductVariant(
                product_id=product.id,
                seller_id=seller.id,
                name_uz=v.get("name_uz") or None,
                name_ru=v.get("name_ru") or None,
                sku=v.get("sku") or None,
                price=int((v.get("price") or 0) * 100),
                old_price=int(v["old_price"] * 100) if v.get("old_price") else None,
                stock_quantity=int(v.get("stock_quantity") or 0),
                track_stock=bool(v.get("track_stock", True)),
                is_default=bool(v.get("is_default", idx == 0)),
                is_active=True,
                sort_order=idx,
            ))

        if d.get("product_image"):
            db.add(ProductImage(
                product_id=product.id,
                seller_id=seller.id,
                url=d["product_image"],
                sort_order=0,
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
            await client.post(
                f"https://api.telegram.org/bot{body.telegram_token}/setWebhook",
                json={"url": bot.webhook_url, "secret_token": webhook_secret},
            )
    except Exception:
        pass

    return {
        "seller_id": seller.id,
        "bot_id": bot.id,
        "temp_password": temp_password,
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

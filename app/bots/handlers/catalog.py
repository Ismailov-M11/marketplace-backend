from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.product import Category, Product, ProductVariant
from app.models.seller import Seller

router = Router()


def format_price(tiyins: int) -> str:
    sums = tiyins // 100
    return f"{sums:,} сум".replace(",", " ")


@router.message(F.text.in_(["📦 Katalog", "📦 Каталог"]))
async def show_catalog(message: Message, seller: Seller | None = None, lang: str = "uz"):
    if not seller:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Category).where(
                Category.seller_id == seller.id,
                Category.is_active == True,
                Category.parent_id.is_(None),
                Category.deleted_at.is_(None),
            ).order_by(Category.sort_order)
        )
        categories = result.scalars().all()

    if not categories:
        text = "Hozircha kategoriyalar yo'q." if lang == "uz" else "Категории пока отсутствуют."
        await message.answer(text)
        return

    buttons = [
        [InlineKeyboardButton(
            text=c.name_uz if lang == "uz" else c.name_ru,
            callback_data=f"cat:{c.id}"
        )]
        for c in categories
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "Kategoriyani tanlang:" if lang == "uz" else "Выберите категорию:"
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("cat:"))
async def show_category_products(cb: CallbackQuery, seller: Seller | None = None, lang: str = "uz"):
    cat_id = int(cb.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product)
            .options(selectinload(Product.variants), selectinload(Product.images))
            .where(
                Product.seller_id == seller.id,
                Product.category_id == cat_id,
                Product.is_active == True,
                Product.deleted_at.is_(None),
            ).limit(20)
        )
        products = result.scalars().all()

    if not products:
        text = "Bu kategoriyada mahsulot yo'q." if lang == "uz" else "В этой категории нет товаров."
        await cb.message.answer(text)
        await cb.answer()
        return

    for p in products:
        default_variant = next((v for v in p.variants if v.is_default and v.is_active), None)
        if not default_variant and p.variants:
            default_variant = p.variants[0]

        name = p.name_uz if lang == "uz" else p.name_ru
        price_text = format_price(default_variant.price) if default_variant else "—"

        buttons = [[InlineKeyboardButton(text=f"🛒 +", callback_data=f"add:{default_variant.id}:1")] if default_variant else []]
        buttons.append([InlineKeyboardButton(text="📋 Batafsil" if lang == "uz" else "📋 Подробнее", callback_data=f"product:{p.id}")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = f"*{name}*\n💰 {price_text}"
        if p.description_uz and lang == "uz":
            text += f"\n\n{p.description_uz[:200]}"
        elif p.description_ru and lang == "ru":
            text += f"\n\n{p.description_ru[:200]}"

        await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb)

    await cb.answer()


@router.callback_query(F.data.startswith("add:"))
async def add_to_cart(cb: CallbackQuery, seller: Seller | None = None, lang: str = "uz"):
    parts = cb.data.split(":")
    variant_id = int(parts[1])
    quantity = int(parts[2]) if len(parts) > 2 else 1

    # Import here to avoid circular deps
    from app.models.customer import Cart, CartItem, Customer

    tg_user_id = cb.from_user.id
    async with AsyncSessionLocal() as session:
        cust_result = await session.execute(
            select(Customer).where(
                Customer.seller_id == seller.id,
                Customer.telegram_user_id == tg_user_id,
            )
        )
        customer = cust_result.scalar_one_or_none()
        if not customer:
            customer = Customer(
                seller_id=seller.id,
                telegram_user_id=tg_user_id,
                full_name=cb.from_user.full_name,
                language=lang,
            )
            session.add(customer)
            await session.flush()

        cart_result = await session.execute(
            select(Cart).options(selectinload(Cart.items)).where(Cart.customer_id == customer.id)
        )
        cart = cart_result.scalar_one_or_none()
        if not cart:
            cart = Cart(customer_id=customer.id, seller_id=seller.id)
            session.add(cart)
            await session.flush()

        variant_result = await session.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = variant_result.scalar_one_or_none()
        if not variant:
            await cb.answer("Mahsulot topilmadi" if lang == "uz" else "Товар не найден", show_alert=True)
            return

        existing = next((i for i in cart.items if i.variant_id == variant_id), None)
        if existing:
            existing.quantity += quantity
        else:
            session.add(CartItem(
                cart_id=cart.id, variant_id=variant_id,
                quantity=quantity, price_snapshot=variant.price,
            ))
        await session.commit()

    text = "Savatchaga qo'shildi ✅" if lang == "uz" else "Добавлено в корзину ✅"
    await cb.answer(text)

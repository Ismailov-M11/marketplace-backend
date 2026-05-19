from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.customer import Cart, CartItem, Customer
from app.models.product import ProductVariant
from app.models.seller import Seller

router = Router()


def format_price(tiyins: int) -> str:
    return f"{tiyins // 100:,} сум".replace(",", " ")


@router.message(F.text.in_(["🛒 Savat", "🛒 Корзина"]))
async def show_cart(message: Message, seller: Seller | None = None, lang: str = "uz"):
    if not seller:
        return

    tg_user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        cust_result = await session.execute(
            select(Customer).where(
                Customer.seller_id == seller.id,
                Customer.telegram_user_id == tg_user_id,
            )
        )
        customer = cust_result.scalar_one_or_none()
        if not customer:
            text = "Savat bo'sh." if lang == "uz" else "Корзина пуста."
            await message.answer(text)
            return

        cart_result = await session.execute(
            select(Cart).options(selectinload(Cart.items)).where(Cart.customer_id == customer.id)
        )
        cart = cart_result.scalar_one_or_none()

        if not cart or not cart.items:
            text = "Savat bo'sh." if lang == "uz" else "Корзина пуста."
            await message.answer(text)
            return

        lines = []
        total = 0
        for item in cart.items:
            variant_result = await session.execute(
                select(ProductVariant).where(ProductVariant.id == item.variant_id)
            )
            variant = variant_result.scalar_one_or_none()
            if variant:
                item_total = item.price_snapshot * item.quantity
                total += item_total
                lines.append(f"• {variant.name_ru or 'Товар'} x{item.quantity} = {format_price(item_total)}")

    cart_text = "🛒 Savat:\n" if lang == "uz" else "🛒 Корзина:\n"
    cart_text += "\n".join(lines)
    cart_text += f"\n\n💰 Jami: {format_price(total)}" if lang == "uz" else f"\n\n💰 Итого: {format_price(total)}"

    order_text = "✅ Buyurtma berish" if lang == "uz" else "✅ Оформить заказ"
    clear_text = "🗑 Tozalash" if lang == "uz" else "🗑 Очистить"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=order_text, callback_data="checkout:start")],
        [InlineKeyboardButton(text=clear_text, callback_data="cart:clear")],
    ])
    await message.answer(cart_text, reply_markup=kb)

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

router = Router()


class CheckoutState(StatesGroup):
    waiting_phone = State()
    waiting_address = State()
    waiting_payment = State()
    waiting_confirm = State()


@router.callback_query(F.data == "checkout:start")
async def checkout_start(cb: CallbackQuery, state: FSMContext, lang: str = "uz"):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamimni ulashish" if lang == "uz" else "📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    text = "Telefon raqamingizni yuboring:" if lang == "uz" else "Отправьте ваш номер телефона:"
    await cb.message.answer(text, reply_markup=kb)
    await state.set_state(CheckoutState.waiting_phone)
    await cb.answer()


@router.message(CheckoutState.waiting_phone)
async def checkout_phone(message: Message, state: FSMContext, lang: str = "uz"):
    phone = None
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        phone = message.text

    await state.update_data(phone=phone)

    text = "Manzilingizni kiriting (yoki Lokatsiya yuboring):" if lang == "uz" else "Введите ваш адрес (или отправьте геолокацию):"
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await state.set_state(CheckoutState.waiting_address)


@router.message(CheckoutState.waiting_address)
async def checkout_address(message: Message, state: FSMContext, lang: str = "uz"):
    address = message.text or ""
    if message.location:
        address = f"{message.location.latitude},{message.location.longitude}"

    await state.update_data(address=address)

    if lang == "uz":
        text = "To'lov usulini tanlang:"
        buttons = [["💵 Naqd pul", "💳 Click", "💳 Payme"]]
    else:
        text = "Выберите способ оплаты:"
        buttons = [["💵 Наличные", "💳 Click", "💳 Payme"]]

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in buttons],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer(text, reply_markup=kb)
    await state.set_state(CheckoutState.waiting_payment)


@router.message(CheckoutState.waiting_payment)
async def checkout_payment(message: Message, state: FSMContext, lang: str = "uz"):
    payment_map = {
        "💵 Naqd pul": "cash", "💵 Наличные": "cash",
        "💳 Click": "click", "💳 Payme": "payme",
    }
    payment = payment_map.get(message.text, "cash")
    await state.update_data(payment=payment)

    data = await state.get_data()
    if lang == "uz":
        summary = (
            f"✅ Buyurtmani tasdiqlang:\n"
            f"📍 Manzil: {data.get('address', '—')}\n"
            f"💳 To'lov: {data.get('payment', '—')}\n\n"
            f"Tasdiqlaysizmi?"
        )
        buttons = [["✅ Tasdiqlash", "❌ Bekor qilish"]]
    else:
        summary = (
            f"✅ Подтвердите заказ:\n"
            f"📍 Адрес: {data.get('address', '—')}\n"
            f"💳 Оплата: {data.get('payment', '—')}\n\n"
            f"Подтверждаете?"
        )
        buttons = [["✅ Подтвердить", "❌ Отмена"]]

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in buttons],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await message.answer(summary, reply_markup=kb)
    await state.set_state(CheckoutState.waiting_confirm)


@router.message(CheckoutState.waiting_confirm)
async def checkout_confirm(message: Message, state: FSMContext, seller=None, lang: str = "uz"):
    confirm_words = ["✅ Tasdiqlash", "✅ Подтвердить"]
    if message.text not in confirm_words:
        text = "Buyurtma bekor qilindi." if lang == "uz" else "Заказ отменён."
        await message.answer(text, reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    data = await state.get_data()
    # In a real implementation, create order here
    # For now, just acknowledge
    text = "🎉 Buyurtmangiz qabul qilindi!" if lang == "uz" else "🎉 Ваш заказ принят!"
    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await state.clear()

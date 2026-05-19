from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.models.seller import Seller
from app.models.bot import BotSettings

router = Router()

MENU_UZ = [
    ["📦 Katalog", "🛒 Savat"],
    ["👤 Profil", "ℹ️ Do'kon haqida"],
]

MENU_RU = [
    ["📦 Каталог", "🛒 Корзина"],
    ["👤 Профиль", "ℹ️ О магазине"],
]


def main_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    rows = MENU_UZ if lang == "uz" else MENU_RU
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    seller: Seller | None = None,
    bot_settings: BotSettings | None = None,
    lang: str = "uz",
):
    if not seller:
        await message.answer("Bot is not configured yet.")
        return

    welcome = ""
    if bot_settings:
        welcome = (bot_settings.welcome_message_uz if lang == "uz" else bot_settings.welcome_message_ru) or ""

    if not welcome:
        welcome = f"Xush kelibsiz, {seller.display_name}!" if lang == "uz" else f"Добро пожаловать в {seller.display_name}!"

    await message.answer(welcome, reply_markup=main_menu(lang))

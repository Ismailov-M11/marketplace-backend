from typing import Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.bot import Bot, BotSettings
from app.models.seller import Seller


class BotContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        bot = data.get("bot")
        if bot:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Bot).where(Bot.telegram_bot_id == bot.id, Bot.is_active == True)
                )
                bot_obj = result.scalar_one_or_none()
                if bot_obj:
                    seller_result = await session.execute(
                        select(Seller).where(Seller.id == bot_obj.seller_id)
                    )
                    seller = seller_result.scalar_one_or_none()

                    settings_result = await session.execute(
                        select(BotSettings).where(BotSettings.bot_id == bot_obj.id)
                    )
                    bot_settings = settings_result.scalar_one_or_none()

                    data["seller"] = seller
                    data["bot_obj"] = bot_obj
                    data["bot_settings"] = bot_settings
                    data["lang"] = bot_settings.default_language if bot_settings else "uz"

        return await handler(event, data)

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.settings import settings
from app.bots.handlers import start_router, catalog_router, cart_router, checkout_router
from app.bots.middlewares.bot_context import BotContextMiddleware

_dp: Dispatcher | None = None


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        storage = RedisStorage.from_url(settings.REDIS_URL)
        _dp = Dispatcher(storage=storage)
        _dp.message.middleware(BotContextMiddleware())
        _dp.callback_query.middleware(BotContextMiddleware())
        _dp.include_router(start_router)
        _dp.include_router(catalog_router)
        _dp.include_router(cart_router)
        _dp.include_router(checkout_router)
    return _dp

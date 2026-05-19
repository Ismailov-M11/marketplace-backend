from app.bots.handlers.start import router as start_router
from app.bots.handlers.catalog import router as catalog_router
from app.bots.handlers.cart import router as cart_router
from app.bots.handlers.checkout import router as checkout_router

__all__ = ["start_router", "catalog_router", "cart_router", "checkout_router"]

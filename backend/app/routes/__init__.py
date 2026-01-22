"""
API Routes для Telegram Mini App.
"""

from .users import router as users_router
from .shops import router as shops_router
from .categories import router as categories_router
from .products import router as products_router
from .cart import router as cart_router
from .favorites import router as favorites_router
from .orders import router as orders_router
from .reviews import router as reviews_router
from .subscriptions import router as subscriptions_router
from .geocode import router as geocode_router
from .promo import router as promo_router
from .banners import router as banners_router
from .admin import router as admin_router

__all__ = [
    "users_router",
    "shops_router",
    "categories_router",
    "products_router",
    "cart_router",
    "favorites_router",
    "orders_router",
    "reviews_router",
    "subscriptions_router",
    "geocode_router",
    "promo_router",
    "banners_router",
    "admin_router",
]







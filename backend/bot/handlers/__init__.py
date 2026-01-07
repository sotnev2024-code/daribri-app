"""
Обработчики команд бота.
"""

from aiogram import Router

from .start import router as start_router
from .add_shop import router as add_shop_router
from .admin import router as admin_router
from .subscription import router as subscription_router
from .banners import router as banners_router
from .subscriptions_admin import router as subscriptions_admin_router
from .users_admin import router as users_admin_router
from .orders import router as orders_router

router = Router()

# Регистрируем только необходимые роутеры
router.include_router(start_router)
router.include_router(add_shop_router)
router.include_router(admin_router)
router.include_router(users_admin_router)
router.include_router(subscription_router)
router.include_router(banners_router)
router.include_router(subscriptions_admin_router)
router.include_router(orders_router)

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
from .shops_admin import router as shops_admin_router
from .products_admin import router as products_admin_router
from .orders_admin import router as orders_admin_router
from .analytics_admin import router as analytics_admin_router
from .categories_admin import router as categories_admin_router
from .reminders import router as reminders_router

router = Router()

# Регистрируем только необходимые роутеры
# ВАЖНО: Специфичные админ-роутеры должны быть зарегистрированы ПЕРЕД общим admin_router,
# чтобы их обработчики проверялись первыми
router.include_router(start_router)
router.include_router(add_shop_router)
router.include_router(subscription_router)
router.include_router(banners_router)
router.include_router(orders_router)
router.include_router(reminders_router)
# Специфичные админ-роутеры (должны быть перед общим admin_router)
router.include_router(shops_admin_router)
router.include_router(products_admin_router)
router.include_router(orders_admin_router)
router.include_router(users_admin_router)
router.include_router(analytics_admin_router)
router.include_router(categories_admin_router)
router.include_router(subscriptions_admin_router)
# Общий админ-роутер (в конце, чтобы обрабатывать только те callback'и, которые не обработаны выше)
router.include_router(admin_router)

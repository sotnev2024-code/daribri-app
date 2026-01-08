"""
Сервис для управления подписками и автоматической деактивации/активации товаров.
"""

from datetime import datetime
from typing import Optional, Tuple
from ..services.database import DatabaseService


class SubscriptionManager:
    """Менеджер подписок для управления активацией товаров."""
    
    @staticmethod
    async def has_active_subscription(db: DatabaseService, shop_id: int) -> bool:
        """Проверяет, есть ли у магазина активная подписка."""
        subscription = await db.fetch_one(
            """SELECT id FROM shop_subscriptions 
               WHERE shop_id = ? AND is_active = 1 AND end_date > datetime('now')
               ORDER BY end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        return subscription is not None
    
    @staticmethod
    async def check_and_update_products_status(db: DatabaseService, shop_id: int) -> Tuple[int, int]:
        """
        Проверяет подписку и обновляет статус товаров магазина.
        Возвращает (активированных, деактивированных) товаров.
        """
        has_active = await SubscriptionManager.has_active_subscription(db, shop_id)
        
        if has_active:
            # Подписка активна - активируем все товары магазина
            result = await db.execute(
                "UPDATE products SET is_active = 1 WHERE shop_id = ? AND is_active = 0",
                (shop_id,)
            )
            activated = result.rowcount if result else 0
            
            # Деактивируем только те, у которых quantity = 0
            result = await db.execute(
                "UPDATE products SET is_active = 0 WHERE shop_id = ? AND quantity = 0",
                (shop_id,)
            )
            deactivated = result.rowcount if result else 0
            
            await db.commit()
            return (activated, deactivated)
        else:
            # Подписка неактивна - деактивируем все товары
            result = await db.execute(
                "UPDATE products SET is_active = 0 WHERE shop_id = ? AND is_active = 1",
                (shop_id,)
            )
            deactivated = result.rowcount if result else 0
            await db.commit()
            return (0, deactivated)
    
    @staticmethod
    async def activate_shop_products(db: DatabaseService, shop_id: int) -> int:
        """
        Активирует все товары магазина (кроме тех, у которых quantity = 0).
        Вызывается при активации подписки.
        """
        result = await db.execute(
            """UPDATE products 
               SET is_active = 1 
               WHERE shop_id = ? AND quantity > 0""",
            (shop_id,)
        )
        activated = result.rowcount if result else 0
        await db.commit()
        return activated
    
    @staticmethod
    async def deactivate_shop_products(db: DatabaseService, shop_id: int) -> int:
        """
        Деактивирует все товары магазина.
        Вызывается при истечении подписки.
        """
        result = await db.execute(
            "UPDATE products SET is_active = 0 WHERE shop_id = ? AND is_active = 1",
            (shop_id,)
        )
        deactivated = result.rowcount if result else 0
        await db.commit()
        return deactivated
    
    @staticmethod
    async def check_all_expired_subscriptions(db: DatabaseService) -> int:
        """
        Проверяет все истекшие подписки и деактивирует товары магазинов.
        Возвращает количество магазинов с деактивированными товарами.
        """
        # Находим все магазины с истекшими подписками
        shops_with_expired = await db.fetch_all(
            """SELECT DISTINCT s.id as shop_id
               FROM shops s
               LEFT JOIN shop_subscriptions ss ON s.id = ss.shop_id 
                   AND ss.is_active = 1 
                   AND ss.end_date > datetime('now')
               WHERE ss.id IS NULL AND s.is_active = 1"""
        )
        
        deactivated_shops = 0
        for shop in shops_with_expired:
            shop_id = shop["shop_id"]
            deactivated_count = await SubscriptionManager.deactivate_shop_products(db, shop_id)
            if deactivated_count > 0:
                deactivated_shops += 1
        
        return deactivated_shops



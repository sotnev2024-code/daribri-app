"""
API Routes для подписок.
"""

import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
from aiogram.types import LabeledPrice

from ..models.subscription import SubscriptionPlan, ShopSubscription
from ..models.user import User
from ..services.database import DatabaseService, get_db
from ..services.telegram_notifier import TelegramNotifier
from .users import get_current_user

router = APIRouter()


def parse_plan(plan: dict) -> dict:
    """Парсит план подписки, преобразуя features из JSON строки в dict."""
    plan_copy = dict(plan)
    if isinstance(plan_copy.get("features"), str):
        try:
            plan_copy["features"] = json.loads(plan_copy["features"])
        except (json.JSONDecodeError, TypeError):
            plan_copy["features"] = {}
    elif plan_copy.get("features") is None:
        plan_copy["features"] = {}
    
    # Убеждаемся, что created_at это datetime объект
    if "created_at" in plan_copy and plan_copy["created_at"]:
        if isinstance(plan_copy["created_at"], str):
            try:
                plan_copy["created_at"] = datetime.fromisoformat(plan_copy["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                plan_copy["created_at"] = datetime.now()
    elif "created_at" not in plan_copy or plan_copy.get("created_at") is None:
        plan_copy["created_at"] = datetime.now()
    
    return plan_copy


@router.get("/test")
async def test_subscription_router():
    """Тестовый эндпоинт для проверки работы роутера подписок."""
    return {
        "status": "ok",
        "message": "Subscription router is working!",
        "endpoints": {
            "request_payment": "/api/subscriptions/request-payment/{plan_id}"
        }
    }


@router.get("/plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans(
    db: DatabaseService = Depends(get_db)
):
    """Получает список планов подписки."""
    try:
        # Проверяем существование таблицы
        tables = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='subscription_plans'")
        if not tables:
            print("[WARNING] subscription_plans table does not exist")
            return []
        
        plans = await db.fetch_all(
            "SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY price"
        )
        
        if not plans:
            print("[INFO] No active subscription plans found")
            return []
        
        result = []
        for plan in plans:
            try:
                parsed = parse_plan(plan)
                result.append(SubscriptionPlan(**parsed))
            except Exception as e:
                print(f"Error parsing plan {plan.get('id')}: {e}")
                import traceback
                traceback.print_exc()
                # Пропускаем проблемный план вместо падения всего запроса
                continue
        return result
    except Exception as e:
        print(f"Error fetching subscription plans: {e}")
        import traceback
        traceback.print_exc()
        # Возвращаем пустой список вместо ошибки
        return []


@router.get("/my", response_model=Optional[ShopSubscription])
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает текущую подписку магазина пользователя."""
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        return None
    
    subscription = await db.fetch_one(
        """SELECT ss.*, sp.name as plan_name
           FROM shop_subscriptions ss
           JOIN subscription_plans sp ON ss.plan_id = sp.id
           WHERE ss.shop_id = ? AND ss.is_active = 1 AND ss.end_date > datetime('now')
           ORDER BY ss.end_date DESC
           LIMIT 1""",
        (shop["id"],)
    )
    
    if not subscription:
        return None
    
    # Вычисляем оставшиеся дни
    end_date = datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
    days_remaining = (end_date - datetime.now(end_date.tzinfo)).days
    
    return ShopSubscription(**subscription, days_remaining=max(0, days_remaining))


@router.post("/subscribe/{plan_id}", response_model=ShopSubscription)
async def subscribe(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Оформляет подписку на план."""
    # Проверяем магазин
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        raise HTTPException(status_code=400, detail="You need to create a shop first")
    
    # Проверяем план
    plan = await db.fetch_one(
        "SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1",
        (plan_id,)
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Деактивируем старые подписки
    await db.update(
        "shop_subscriptions",
        {"is_active": False},
        "shop_id = ?",
        (shop["id"],)
    )
    
    # Создаём новую подписку
    start_date = datetime.now()
    end_date = start_date + timedelta(days=plan["duration_days"])
    
    subscription_id = await db.insert("shop_subscriptions", {
        "shop_id": shop["id"],
        "plan_id": plan_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "is_active": True,
        "payment_id": f"pay_{datetime.now().timestamp()}"  # Заглушка для payment_id
    })
    
    subscription = await db.fetch_one(
        """SELECT ss.*, sp.name as plan_name
           FROM shop_subscriptions ss
           JOIN subscription_plans sp ON ss.plan_id = sp.id
           WHERE ss.id = ?""",
        (subscription_id,)
    )
    
    # Вычисляем оставшиеся дни
    end_date = datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
    days_remaining = max(0, (end_date - datetime.now(end_date.tzinfo)).days)
    
    # Активируем товары магазина при активации подписки
    from ..services.subscription_manager import SubscriptionManager
    activated = await SubscriptionManager.activate_shop_products(db, shop["id"])
    if activated > 0:
        print(f"[SUBSCRIPTION] Activated {activated} products for shop {shop['id']}")
    
    return ShopSubscription(**subscription, days_remaining=days_remaining)


@router.get("/history", response_model=List[ShopSubscription])
async def get_subscription_history(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает историю подписок."""
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        return []
    
    subscriptions = await db.fetch_all(
        """SELECT ss.*, sp.name as plan_name
           FROM shop_subscriptions ss
           JOIN subscription_plans sp ON ss.plan_id = sp.id
           WHERE ss.shop_id = ?
           ORDER BY ss.created_at DESC""",
        (shop["id"],)
    )
    
    return [ShopSubscription(**sub) for sub in subscriptions]


@router.get("/usage")
async def get_subscription_usage(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает статистику использования подписки (количество товаров и т.д.)."""
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        return {
            "products_count": 0,
            "promotions_count": 0,
            "max_products": 0,
            "max_promotions": 0
        }
    
    # Получаем текущую подписку
    subscription = await db.fetch_one(
        """SELECT ss.*, sp.name as plan_name, sp.max_products
           FROM shop_subscriptions ss
           JOIN subscription_plans sp ON ss.plan_id = sp.id
           WHERE ss.shop_id = ? AND ss.is_active = 1 AND ss.end_date > datetime('now')
           ORDER BY ss.end_date DESC
           LIMIT 1""",
        (shop["id"],)
    )
    
    if not subscription:
        return {
            "products_count": 0,
            "promotions_count": 0,
            "max_products": 0,
            "max_promotions": 0
        }
    
    # Количество товаров магазина
    products_result = await db.fetch_one(
        "SELECT COUNT(*) as count FROM products WHERE shop_id = ?",
        (shop["id"],)
    )
    products_count = products_result["count"] if products_result else 0
    
    # Количество товаров в трендах
    promotions_result = await db.fetch_one(
        "SELECT COUNT(*) as count FROM products WHERE shop_id = ? AND is_trending = 1",
        (shop["id"],)
    )
    promotions_count = promotions_result["count"] if promotions_result else 0
    
    max_products = subscription.get("max_products", 50)
    max_promotions = 20  # По умолчанию
    
    return {
        "products_count": products_count,
        "promotions_count": promotions_count,
        "max_products": max_products,
        "max_promotions": max_promotions
    }


@router.post("/request-payment/{plan_id}", tags=["Subscriptions"])
async def request_subscription_payment(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Отправляет invoice для оплаты подписки через Telegram бота."""
    import sys
    print(f"[API] ========== request_subscription_payment CALLED ==========", file=sys.stderr, flush=True)
    print(f"[API] plan_id={plan_id}, user_id={current_user.id}", file=sys.stderr, flush=True)
    print(f"[API] ==========================================================", file=sys.stderr, flush=True)
    
    # Проверяем магазин
    shop = await db.fetch_one(
        "SELECT id, name FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        raise HTTPException(status_code=400, detail="You need to create a shop first")
    
    shop_id = shop["id"]
    shop_name = shop["name"]
    
    # Проверяем план
    plan = await db.fetch_one(
        "SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1",
        (plan_id,)
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Получаем бота
    bot = TelegramNotifier.get_bot()
    if not bot:
        raise HTTPException(status_code=500, detail="Bot is not configured")
    
    # Получаем настройки YooKassa
    from ..config import settings
    import os
    yookassa_token = os.getenv("API_KEY_YOOKASSA", "") or getattr(settings, "API_KEY_YOOKASSA", "")
    
    if not yookassa_token:
        raise HTTPException(status_code=500, detail="Payment system is not configured")
    
    # Получаем telegram_id пользователя
    telegram_id = current_user.telegram_id
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID not found")
    
    # Создаем invoice для оплаты
    invoice_payload = f"subscription_plan_{plan_id}_{shop_id}_{uuid.uuid4().hex[:8]}"
    
    # Цена в копейках (price в плане в рублях)
    price_rub = float(plan["price"])
    price_kopecks = int(price_rub * 100)
    
    prices = [LabeledPrice(label=f"Подписка: {plan['name']}", amount=price_kopecks)]
    
    # Формируем описание
    duration_text = f"{plan['duration_days']} {plan['duration_days'] == 1 and 'день' or (plan['duration_days'] < 5 and 'дня' or 'дней')}"
    description = f"Подписка для магазина \"{shop_name}\"\n\n"
    description += f"План: {plan['name']}\n"
    description += f"Длительность: {duration_text}\n"
    description += f"Макс. товаров: {plan['max_products']}\n"
    if plan.get('description'):
        description += f"\n{plan['description']}"
    
    try:
        await bot.send_invoice(
            chat_id=telegram_id,
            title=f"Подписка: {plan['name']}",
            description=description,
            payload=invoice_payload,
            provider_token=yookassa_token,
            currency="RUB",
            prices=prices,
            start_parameter=f"subscription_plan_{plan_id}"
        )
        
        return {
            "success": True,
            "message": "Invoice sent to Telegram chat",
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "price": price_rub
        }
    except Exception as e:
        print(f"Error sending invoice: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send invoice: {str(e)}")


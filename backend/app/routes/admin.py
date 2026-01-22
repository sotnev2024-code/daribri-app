"""
API Routes для администратора.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import os

from ..models.user import User
from ..models.shop import Shop, ShopUpdate
from ..models.product import Product
from ..models.order import Order, OrderWithItems
from ..services.database import DatabaseService, get_db
from .users import get_current_user
from ..config import settings

router = APIRouter()


def is_admin_user(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    admin_ids_str = os.getenv("ADMIN_IDS", "") or getattr(settings, "ADMIN_IDS", "")
    
    if admin_ids_str:
        try:
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
            return telegram_id in admin_ids
        except (ValueError, AttributeError):
            pass
    
    return False


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Проверяет, что текущий пользователь является администратором."""
    if not is_admin_user(current_user.telegram_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ==================== Магазины ====================

@router.get("/shops", response_model=List[dict])
async def get_all_shops(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает список всех магазинов с фильтрами."""
    conditions = []
    params = []
    
    if is_active is not None:
        conditions.append("s.is_active = ?")
        params.append(1 if is_active else 0)
    
    if is_verified is not None:
        conditions.append("s.is_verified = ?")
        params.append(1 if is_verified else 0)
    
    if search:
        conditions.append("(s.name LIKE ? OR s.description LIKE ? OR s.address LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT s.*, 
               u.telegram_id as owner_telegram_id,
               u.username as owner_username,
               (SELECT COUNT(*) FROM products WHERE shop_id = s.id) as products_count,
               (SELECT COUNT(*) FROM orders WHERE shop_id = s.id) as orders_count,
               (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE shop_id = s.id) as total_revenue
        FROM shops s
        LEFT JOIN users u ON s.owner_id = u.id
        WHERE {where_clause}
        ORDER BY s.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, skip])
    
    shops = await db.fetch_all(query, tuple(params))
    
    # Преобразуем Decimal в float для JSON
    result = []
    for shop in shops:
        shop_dict = dict(shop)
        if shop_dict.get("average_rating") is not None:
            if isinstance(shop_dict["average_rating"], Decimal):
                shop_dict["average_rating"] = float(shop_dict["average_rating"])
        if shop_dict.get("total_revenue") is not None:
            if isinstance(shop_dict["total_revenue"], Decimal):
                shop_dict["total_revenue"] = float(shop_dict["total_revenue"])
        result.append(shop_dict)
    
    return result


@router.get("/shops/{shop_id}", response_model=dict)
async def get_shop_details(
    shop_id: int,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает детали магазина."""
    shop = await db.fetch_one(
        """SELECT s.*, 
                  u.telegram_id as owner_telegram_id,
                  u.username as owner_username,
                  u.first_name as owner_first_name,
                  u.last_name as owner_last_name
           FROM shops s
           LEFT JOIN users u ON s.owner_id = u.id
           WHERE s.id = ?""",
        (shop_id,)
    )
    
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    shop_dict = dict(shop)
    if shop_dict.get("average_rating") is not None:
        if isinstance(shop_dict["average_rating"], Decimal):
            shop_dict["average_rating"] = float(shop_dict["average_rating"])
    
    return shop_dict


@router.patch("/shops/{shop_id}", response_model=Shop)
async def update_shop(
    shop_id: int,
    shop_update: ShopUpdate,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет данные магазина."""
    shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    update_data = {k: v for k, v in shop_update.model_dump().items() if v is not None}
    
    if update_data:
        await db.update("shops", update_data, "id = ?", (shop_id,))
        await db.commit()
    
    updated_shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
    return Shop(**updated_shop)


@router.get("/shops/{shop_id}/statistics", response_model=dict)
async def get_shop_statistics(
    shop_id: int,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает статистику магазина."""
    shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Количество товаров
    products_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ?",
        (shop_id,)
    )
    
    # Количество активных товаров
    active_products_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ? AND is_active = 1",
        (shop_id,)
    )
    
    # Количество заказов
    orders_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM orders WHERE shop_id = ?",
        (shop_id,)
    )
    
    # Общая выручка
    total_revenue = await db.fetch_one(
        "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE shop_id = ?",
        (shop_id,)
    )
    
    # Средний чек
    avg_order = await db.fetch_one(
        "SELECT COALESCE(AVG(total_amount), 0) as avg FROM orders WHERE shop_id = ?",
        (shop_id,)
    )
    
    # Заказы по статусам
    orders_by_status = await db.fetch_all(
        """SELECT status, COUNT(*) as cnt 
           FROM orders 
           WHERE shop_id = ? 
           GROUP BY status""",
        (shop_id,)
    )
    
    return {
        "shop_id": shop_id,
        "products_count": products_count["cnt"] if products_count else 0,
        "active_products_count": active_products_count["cnt"] if active_products_count else 0,
        "orders_count": orders_count["cnt"] if orders_count else 0,
        "total_revenue": float(total_revenue["total"]) if total_revenue and isinstance(total_revenue["total"], Decimal) else (total_revenue["total"] if total_revenue else 0),
        "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0),
        "orders_by_status": {row["status"]: row["cnt"] for row in orders_by_status}
    }


# ==================== Товары ====================

@router.get("/products", response_model=List[dict])
async def get_all_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    shop_id: Optional[int] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает список всех товаров с фильтрами."""
    conditions = []
    params = []
    
    if shop_id:
        conditions.append("p.shop_id = ?")
        params.append(shop_id)
    
    if category_id:
        conditions.append("p.category_id = ?")
        params.append(category_id)
    
    if is_active is not None:
        conditions.append("p.is_active = ?")
        params.append(1 if is_active else 0)
    
    if search:
        conditions.append("(p.name LIKE ? OR p.description LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT p.*, 
               s.name as shop_name,
               c.name as category_name
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.id
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE {where_clause}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, skip])
    
    products = await db.fetch_all(query, tuple(params))
    
    result = []
    for product in products:
        product_dict = dict(product)
        if product_dict.get("price") is not None:
            if isinstance(product_dict["price"], Decimal):
                product_dict["price"] = float(product_dict["price"])
        if product_dict.get("discount_price") is not None:
            if isinstance(product_dict["discount_price"], Decimal):
                product_dict["discount_price"] = float(product_dict["discount_price"])
        result.append(product_dict)
    
    return result


@router.get("/products/{product_id}", response_model=dict)
async def get_product_details(
    product_id: int,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает детали товара."""
    product = await db.fetch_one(
        """SELECT p.*, 
                  s.name as shop_name,
                  s.id as shop_id,
                  c.name as category_name
           FROM products p
           LEFT JOIN shops s ON p.shop_id = s.id
           LEFT JOIN categories c ON p.category_id = c.id
           WHERE p.id = ?""",
        (product_id,)
    )
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_dict = dict(product)
    if product_dict.get("price") is not None:
        if isinstance(product_dict["price"], Decimal):
            product_dict["price"] = float(product_dict["price"])
    if product_dict.get("discount_price") is not None:
        if isinstance(product_dict["discount_price"], Decimal):
            product_dict["discount_price"] = float(product_dict["discount_price"])
    
    return product_dict


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Удаляет товар."""
    product = await db.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    await db.commit()
    
    return {"message": "Product deleted successfully"}


@router.patch("/products/{product_id}/status")
async def update_product_status(
    product_id: int,
    is_active: bool,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Изменяет статус товара (активен/неактивен)."""
    product = await db.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.update(
        "products",
        {"is_active": 1 if is_active else 0},
        "id = ?",
        (product_id,)
    )
    await db.commit()
    
    return {"message": f"Product {'activated' if is_active else 'deactivated'} successfully"}


# ==================== Заказы ====================

@router.get("/orders", response_model=List[dict])
async def get_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    shop_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает список всех заказов с фильтрами."""
    conditions = []
    params = []
    
    if status:
        conditions.append("o.status = ?")
        params.append(status)
    
    if shop_id:
        conditions.append("o.shop_id = ?")
        params.append(shop_id)
    
    if user_id:
        conditions.append("o.user_id = ?")
        params.append(user_id)
    
    if start_date:
        conditions.append("DATE(o.created_at) >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("DATE(o.created_at) <= ?")
        params.append(end_date)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT o.*, 
               s.name as shop_name,
               u.telegram_id as user_telegram_id,
               u.username as user_username,
               u.first_name as user_first_name,
               u.last_name as user_last_name
        FROM orders o
        LEFT JOIN shops s ON o.shop_id = s.id
        LEFT JOIN users u ON o.user_id = u.id
        WHERE {where_clause}
        ORDER BY o.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, skip])
    
    orders = await db.fetch_all(query, tuple(params))
    
    result = []
    for order in orders:
        order_dict = dict(order)
        if order_dict.get("total_amount") is not None:
            if isinstance(order_dict["total_amount"], Decimal):
                order_dict["total_amount"] = float(order_dict["total_amount"])
        if order_dict.get("discount_amount") is not None:
            if isinstance(order_dict["discount_amount"], Decimal):
                order_dict["discount_amount"] = float(order_dict["discount_amount"])
        if order_dict.get("promo_discount_amount") is not None:
            if isinstance(order_dict["promo_discount_amount"], Decimal):
                order_dict["promo_discount_amount"] = float(order_dict["promo_discount_amount"])
        if order_dict.get("delivery_fee") is not None:
            if isinstance(order_dict["delivery_fee"], Decimal):
                order_dict["delivery_fee"] = float(order_dict["delivery_fee"])
        result.append(order_dict)
    
    return result


@router.get("/orders/{order_id}", response_model=dict)
async def get_order_details(
    order_id: int,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает детали заказа."""
    order = await db.fetch_one(
        """SELECT o.*, 
                  s.name as shop_name,
                  u.telegram_id as user_telegram_id,
                  u.username as user_username,
                  u.first_name as user_first_name,
                  u.last_name as user_last_name
           FROM orders o
           LEFT JOIN shops s ON o.shop_id = s.id
           LEFT JOIN users u ON o.user_id = u.id
           WHERE o.id = ?""",
        (order_id,)
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Получаем товары заказа
    items = await db.fetch_all(
        """SELECT oi.*, 
                  COALESCE(oi.product_name, p.name, 'Товар удалён') as product_name
           FROM order_items oi
           LEFT JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = ?""",
        (order_id,)
    )
    
    order_dict = dict(order)
    if order_dict.get("total_amount") is not None:
        if isinstance(order_dict["total_amount"], Decimal):
            order_dict["total_amount"] = float(order_dict["total_amount"])
    if order_dict.get("discount_amount") is not None:
        if isinstance(order_dict["discount_amount"], Decimal):
            order_dict["discount_amount"] = float(order_dict["discount_amount"])
    if order_dict.get("promo_discount_amount") is not None:
        if isinstance(order_dict["promo_discount_amount"], Decimal):
            order_dict["promo_discount_amount"] = float(order_dict["promo_discount_amount"])
    if order_dict.get("delivery_fee") is not None:
        if isinstance(order_dict["delivery_fee"], Decimal):
            order_dict["delivery_fee"] = float(order_dict["delivery_fee"])
    
    order_dict["items"] = []
    for item in items:
        item_dict = dict(item)
        if item_dict.get("price") is not None:
            if isinstance(item_dict["price"], Decimal):
                item_dict["price"] = float(item_dict["price"])
        if item_dict.get("discount_price") is not None:
            if isinstance(item_dict["discount_price"], Decimal):
                item_dict["discount_price"] = float(item_dict["discount_price"])
        order_dict["items"].append(item_dict)
    
    return order_dict


@router.get("/orders/statistics", response_model=dict)
async def get_orders_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает статистику по заказам."""
    conditions = []
    params = []
    
    if start_date:
        conditions.append("DATE(created_at) >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("DATE(created_at) <= ?")
        params.append(end_date)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # Общая выручка
    total_revenue = await db.fetch_one(
        f"SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE {where_clause}",
        tuple(params)
    )
    
    # Средний чек
    avg_order = await db.fetch_one(
        f"SELECT COALESCE(AVG(total_amount), 0) as avg FROM orders WHERE {where_clause}",
        tuple(params)
    )
    
    # Количество заказов
    orders_count = await db.fetch_one(
        f"SELECT COUNT(*) as cnt FROM orders WHERE {where_clause}",
        tuple(params)
    )
    
    # Заказы по статусам
    orders_by_status = await db.fetch_all(
        f"""SELECT status, COUNT(*) as cnt 
           FROM orders 
           WHERE {where_clause}
           GROUP BY status""",
        tuple(params)
    )
    
    return {
        "total_revenue": float(total_revenue["total"]) if total_revenue and isinstance(total_revenue["total"], Decimal) else (total_revenue["total"] if total_revenue else 0),
        "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0),
        "orders_count": orders_count["cnt"] if orders_count else 0,
        "orders_by_status": {row["status"]: row["cnt"] for row in orders_by_status}
    }


# ==================== Пользователи ====================

@router.get("/users", response_model=List[dict])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает список всех пользователей."""
    conditions = []
    params = []
    
    if search:
        conditions.append("(u.username LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ?)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT u.*,
               (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as orders_count,
               (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE user_id = u.id) as total_spent
        FROM users u
        WHERE {where_clause}
        ORDER BY u.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, skip])
    
    users = await db.fetch_all(query, tuple(params))
    
    result = []
    for user in users:
        user_dict = dict(user)
        if user_dict.get("total_spent") is not None:
            if isinstance(user_dict["total_spent"], Decimal):
                user_dict["total_spent"] = float(user_dict["total_spent"])
        result.append(user_dict)
    
    return result


@router.get("/users/{user_id}", response_model=dict)
async def get_user_details(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает детали пользователя."""
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Статистика пользователя
    orders_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM orders WHERE user_id = ?",
        (user_id,)
    )
    
    total_spent = await db.fetch_one(
        "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE user_id = ?",
        (user_id,)
    )
    
    user_dict = dict(user)
    user_dict["orders_count"] = orders_count["cnt"] if orders_count else 0
    user_dict["total_spent"] = float(total_spent["total"]) if total_spent and isinstance(total_spent["total"], Decimal) else (total_spent["total"] if total_spent else 0)
    
    return user_dict


@router.get("/users/{user_id}/orders", response_model=List[dict])
async def get_user_orders(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает заказы пользователя."""
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = await db.fetch_all(
        """SELECT o.*, s.name as shop_name
           FROM orders o
           LEFT JOIN shops s ON o.shop_id = s.id
           WHERE o.user_id = ?
           ORDER BY o.created_at DESC
           LIMIT ? OFFSET ?""",
        (user_id, limit, skip)
    )
    
    result = []
    for order in orders:
        order_dict = dict(order)
        if order_dict.get("total_amount") is not None:
            if isinstance(order_dict["total_amount"], Decimal):
                order_dict["total_amount"] = float(order_dict["total_amount"])
        result.append(order_dict)
    
    return result


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_blocked: bool,
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Блокирует/разблокирует пользователя."""
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Если в таблице users нет поля is_blocked, используем is_active или создаем поле
    # Для простоты, будем использовать существующее поле или добавим новое через миграцию
    # Пока используем is_active как индикатор блокировки (инвертированный)
    await db.update(
        "users",
        {"is_active": 0 if is_blocked else 1},  # Временно используем is_active
        "id = ?",
        (user_id,)
    )
    await db.commit()
    
    return {"message": f"User {'blocked' if is_blocked else 'unblocked'} successfully"}


# ==================== Аналитика ====================

@router.get("/analytics/platform", response_model=dict)
async def get_platform_statistics(
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает общую статистику платформы."""
    # Активные магазины
    active_shops = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM shops WHERE is_active = 1"
    )
    
    # Всего магазинов
    total_shops = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM shops"
    )
    
    # Активные пользователи (сделавшие хотя бы один заказ за последние 30 дней)
    active_users = await db.fetch_one(
        """SELECT COUNT(DISTINCT user_id) as cnt 
           FROM orders 
           WHERE created_at >= datetime('now', '-30 days')"""
    )
    
    # Всего пользователей
    total_users = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM users"
    )
    
    # Всего товаров
    total_products = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products"
    )
    
    # Активные товары
    active_products = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products WHERE is_active = 1"
    )
    
    return {
        "active_shops": active_shops["cnt"] if active_shops else 0,
        "total_shops": total_shops["cnt"] if total_shops else 0,
        "active_users": active_users["cnt"] if active_users else 0,
        "total_users": total_users["cnt"] if total_users else 0,
        "total_products": total_products["cnt"] if total_products else 0,
        "active_products": active_products["cnt"] if active_products else 0
    }


@router.get("/analytics/revenue", response_model=dict)
async def get_revenue_report(
    period: str = Query("month", regex="^(day|week|month)$"),
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает финансовый отчет по выручке."""
    period_map = {
        "day": "-1 day",
        "week": "-7 days",
        "month": "-30 days"
    }
    
    period_sql = period_map.get(period, "-30 days")
    
    # Выручка за период
    revenue = await db.fetch_one(
        f"""SELECT COALESCE(SUM(total_amount), 0) as total 
           FROM orders 
           WHERE created_at >= datetime('now', '{period_sql}')"""
    )
    
    # Количество заказов за период
    orders_count = await db.fetch_one(
        f"""SELECT COUNT(*) as cnt 
           FROM orders 
           WHERE created_at >= datetime('now', '{period_sql}')"""
    )
    
    # Средний чек за период
    avg_order = await db.fetch_one(
        f"""SELECT COALESCE(AVG(total_amount), 0) as avg 
           FROM orders 
           WHERE created_at >= datetime('now', '{period_sql}')"""
    )
    
    return {
        "period": period,
        "revenue": float(revenue["total"]) if revenue and isinstance(revenue["total"], Decimal) else (revenue["total"] if revenue else 0),
        "orders_count": orders_count["cnt"] if orders_count else 0,
        "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0)
    }


@router.get("/analytics/top-shops", response_model=List[dict])
async def get_top_shops(
    limit: int = Query(10, ge=1, le=50),
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает топ магазинов по выручке."""
    shops = await db.fetch_all(
        """SELECT s.id, s.name, s.is_active, s.is_verified,
                  COALESCE(SUM(o.total_amount), 0) as revenue,
                  COUNT(o.id) as orders_count
           FROM shops s
           LEFT JOIN orders o ON s.id = o.shop_id
           GROUP BY s.id
           ORDER BY revenue DESC
           LIMIT ?""",
        (limit,)
    )
    
    result = []
    for shop in shops:
        shop_dict = dict(shop)
        if shop_dict.get("revenue") is not None:
            if isinstance(shop_dict["revenue"], Decimal):
                shop_dict["revenue"] = float(shop_dict["revenue"])
        result.append(shop_dict)
    
    return result


@router.get("/analytics/top-products", response_model=List[dict])
async def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает топ товаров по продажам."""
    products = await db.fetch_all(
        """SELECT p.id, p.name, p.price, s.name as shop_name,
                  SUM(oi.quantity) as sold_quantity,
                  SUM(oi.price * oi.quantity) as revenue
           FROM products p
           LEFT JOIN order_items oi ON p.id = oi.product_id
           LEFT JOIN shops s ON p.shop_id = s.id
           GROUP BY p.id
           HAVING sold_quantity > 0
           ORDER BY sold_quantity DESC
           LIMIT ?""",
        (limit,)
    )
    
    result = []
    for product in products:
        product_dict = dict(product)
        if product_dict.get("price") is not None:
            if isinstance(product_dict["price"], Decimal):
                product_dict["price"] = float(product_dict["price"])
        if product_dict.get("revenue") is not None:
            if isinstance(product_dict["revenue"], Decimal):
                product_dict["revenue"] = float(product_dict["revenue"])
        result.append(product_dict)
    
    return result


# ==================== Промокоды ====================

@router.get("/promos/statistics", response_model=dict)
async def get_promo_statistics(
    admin_user: User = Depends(get_admin_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает статистику использования промокодов."""
    # Всего промокодов
    total_promos = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM promos"
    )
    
    # Активных промокодов
    active_promos = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM promos WHERE is_active = 1"
    )
    
    # Общее количество использований
    total_uses = await db.fetch_one(
        "SELECT COALESCE(SUM(usage_count), 0) as total FROM promos"
    )
    
    # Промокоды по типам
    promos_by_type = await db.fetch_all(
        """SELECT promo_type, COUNT(*) as cnt 
           FROM promos 
           GROUP BY promo_type"""
    )
    
    # Топ промокодов по использованию
    top_promos = await db.fetch_all(
        """SELECT code, promo_type, usage_count, current_uses
           FROM promos
           ORDER BY usage_count DESC
           LIMIT 10"""
    )
    
    return {
        "total_promos": total_promos["cnt"] if total_promos else 0,
        "active_promos": active_promos["cnt"] if active_promos else 0,
        "total_uses": total_uses["total"] if total_uses else 0,
        "promos_by_type": {row["promo_type"]: row["cnt"] for row in promos_by_type},
        "top_promos": [
            {
                "code": p["code"],
                "promo_type": p["promo_type"],
                "usage_count": p["usage_count"] or 0,
                "current_uses": p["current_uses"] or 0
            }
            for p in top_promos
        ]
    }


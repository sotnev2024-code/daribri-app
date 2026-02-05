"""
API Routes для магазинов.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel

from ..models.shop import Shop, ShopCreate, ShopUpdate, ShopWithStats
from ..models.user import User
from ..services.database import DatabaseService, get_db
from ..services.media import get_media_service
from .users import get_current_user, get_current_user_optional

router = APIRouter()


class ShopStatistics(BaseModel):
    """Статистика магазина за период."""
    period_start: str
    period_end: str
    total_orders: int
    total_revenue: float
    total_net_profit: Optional[float] = None  # Чистый доход (доход - себестоимость)
    average_order_value: float
    orders_by_status: dict
    revenue_by_day: List[dict]
    orders_by_day: List[dict]
    top_products: List[dict]
    orders_by_status_count: dict


# Функция get_shop_statistics используется напрямую в main.py
# для регистрации маршрута /api/shops/my/statistics перед подключением роутера
# Это необходимо, чтобы маршрут не перехватывался маршрутом /{shop_id}
async def get_shop_statistics(
    start_date: Optional[str],
    end_date: Optional[str],
    current_user: User,
    db: DatabaseService
):
    """Получает статистику магазина за указанный период."""
    print(f"[STATISTICS] Endpoint called: start_date={start_date}, end_date={end_date}, user_id={current_user.id}")
    # Проверяем, что у пользователя есть магазин
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    shop_id = shop["id"]
    
    # Устанавливаем период (по умолчанию - последние 30 дней)
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    else:
        end_dt = datetime.now()
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    else:
        start_dt = datetime.now().replace(day=1)  # По умолчанию с начала текущего месяца
    
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    
    # Общая статистика заказов (только доставленные)
    total_orders_result = await db.fetch_one(
        """SELECT 
               COUNT(*) as total_orders,
               COALESCE(SUM(total_amount), 0) as total_revenue,
               COALESCE(AVG(total_amount), 0) as avg_order_value
           FROM orders
           WHERE shop_id = ? AND status = 'delivered' AND DATE(created_at) BETWEEN ? AND ?""",
        (shop_id, start_str, end_str)
    )
    
    total_orders = total_orders_result["total_orders"] or 0
    total_revenue = float(total_orders_result["total_revenue"] or 0)
    average_order_value = float(total_orders_result["avg_order_value"] or 0)
    
    # Рассчитываем чистую прибыль (доход - себестоимость)
    # Чистая прибыль = сумма (количество * (цена продажи - себестоимость)) 
    # ТОЛЬКО для товаров с указанной себестоимостью
    # Если у товара нет себестоимости - он не учитывается в расчете
    net_profit_result = await db.fetch_one(
        """SELECT 
               COALESCE(SUM(oi.quantity * (oi.price - p.cost_price)), 0) as total_net_profit,
               COUNT(*) as items_with_cost_price
           FROM order_items oi
           JOIN orders o ON oi.order_id = o.id
           LEFT JOIN products p ON oi.product_id = p.id
           WHERE o.shop_id = ? AND o.status = 'delivered' 
           AND DATE(o.created_at) BETWEEN ? AND ?
           AND p.cost_price IS NOT NULL AND p.cost_price > 0""",
        (shop_id, start_str, end_str)
    )
    # Если есть товары с себестоимостью - возвращаем сумму, иначе None
    if net_profit_result and net_profit_result.get("items_with_cost_price", 0) > 0:
        total_net_profit = float(net_profit_result["total_net_profit"] or 0)
    else:
        total_net_profit = None
    
    # Заказы по статусам
    orders_by_status = await db.fetch_all(
        """SELECT status, COUNT(*) as count
           FROM orders
           WHERE shop_id = ? AND DATE(created_at) BETWEEN ? AND ?
           GROUP BY status""",
        (shop_id, start_str, end_str)
    )
    orders_by_status_dict = {row["status"]: row["count"] for row in orders_by_status}
    
    # Заказы по дням (только доставленные)
    orders_by_day = await db.fetch_all(
        """SELECT 
               DATE(created_at) as date,
               COUNT(*) as count
           FROM orders
           WHERE shop_id = ? AND status = 'delivered' AND DATE(created_at) BETWEEN ? AND ?
           GROUP BY DATE(created_at)
           ORDER BY date""",
        (shop_id, start_str, end_str)
    )
    orders_by_day_list = [
        {"date": row["date"], "count": row["count"]}
        for row in orders_by_day
    ]
    
    # Доходы по дням (только доставленные)
    revenue_by_day = await db.fetch_all(
        """SELECT 
               DATE(o.created_at) as date,
               COALESCE(SUM(o.total_amount), 0) as revenue,
               COALESCE(SUM(CASE 
                   WHEN p.cost_price IS NOT NULL AND p.cost_price > 0 
                   THEN oi.quantity * (oi.price - p.cost_price) 
                   ELSE 0 
               END), 0) as net_profit
           FROM orders o
           LEFT JOIN order_items oi ON o.id = oi.order_id
           LEFT JOIN products p ON oi.product_id = p.id
           WHERE o.shop_id = ? AND o.status = 'delivered' AND DATE(o.created_at) BETWEEN ? AND ?
           GROUP BY DATE(o.created_at)
           ORDER BY date""",
        (shop_id, start_str, end_str)
    )
    revenue_by_day_list = [
        {
            "date": row["date"], 
            "revenue": float(row["revenue"] or 0),
            "net_profit": float(row["net_profit"] or 0) if row.get("net_profit") is not None else None
        }
        for row in revenue_by_day
    ]
    
    # Топ товаров (только доставленные заказы)
    top_products = await db.fetch_all(
        """SELECT 
               COALESCE(oi.product_name, p.name) as product_name,
               SUM(oi.quantity) as total_quantity,
               SUM(oi.quantity * oi.price) as total_revenue,
               COALESCE(SUM(CASE 
                   WHEN p.cost_price IS NOT NULL AND p.cost_price > 0 
                   THEN oi.quantity * (oi.price - p.cost_price) 
                   ELSE 0 
               END), 0) as net_profit
           FROM order_items oi
           LEFT JOIN products p ON oi.product_id = p.id
           JOIN orders o ON oi.order_id = o.id
           WHERE o.shop_id = ? AND o.status = 'delivered' AND DATE(o.created_at) BETWEEN ? AND ?
           GROUP BY oi.product_id, COALESCE(oi.product_name, p.name)
           ORDER BY total_quantity DESC
           LIMIT 10""",
        (shop_id, start_str, end_str)
    )
    top_products_list = [
        {
            "product_name": row["product_name"] or "Неизвестный товар",
            "total_quantity": row["total_quantity"],
            "total_revenue": float(row["total_revenue"] or 0),
            "net_profit": float(row["net_profit"] or 0) if row.get("net_profit") is not None else None
        }
        for row in top_products
    ]
    
    return ShopStatistics(
        period_start=start_str,
        period_end=end_str,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_net_profit=total_net_profit if total_net_profit and total_net_profit > 0 else None,
        average_order_value=average_order_value,
        orders_by_status=orders_by_status_dict,
        revenue_by_day=revenue_by_day_list,
        orders_by_day=orders_by_day_list,
        top_products=top_products_list,
        orders_by_status_count=orders_by_status_dict
    )


@router.get("/", response_model=List[Shop])
async def get_shops(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: DatabaseService = Depends(get_db)
):
    """Получает список активных магазинов."""
    if search:
        shops = await db.fetch_all(
            """SELECT * FROM shops 
               WHERE is_active = 1 AND name LIKE ? 
               ORDER BY average_rating DESC 
               LIMIT ? OFFSET ?""",
            (f"%{search}%", limit, skip)
        )
    else:
        shops = await db.fetch_all(
            """SELECT * FROM shops 
               WHERE is_active = 1 
               ORDER BY average_rating DESC 
               LIMIT ? OFFSET ?""",
            (limit, skip)
        )
    return [Shop(**shop) for shop in shops]


# ВРЕМЕННО: Маршрут /my перенесен в main.py чтобы не конфликтовать с /my/statistics
# TODO: Вернуть обратно после решения проблемы с порядком маршрутов
# @router.get("/my", response_model=Optional[ShopWithStats])
# async def get_my_shop(
#     current_user: User = Depends(get_current_user),
#     db: DatabaseService = Depends(get_db)
# ):
#     """Получает магазин текущего пользователя."""
#     shop = await db.fetch_one(
#         "SELECT * FROM shops WHERE owner_id = ?",
#         (current_user.id,)
#     )
#     if not shop:
#         return None
#     
#     # Получаем статистику
#     products_count = await db.fetch_one(
#         "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ? AND is_active = 1 AND quantity > 0",
#         (shop["id"],)
#     )
#     orders_count = await db.fetch_one(
#         "SELECT COUNT(*) as cnt FROM orders WHERE shop_id = ?",
#         (shop["id"],)
#     )
#     subscription = await db.fetch_one(
#         """SELECT * FROM shop_subscriptions 
#            WHERE shop_id = ? AND is_active = 1 AND end_date > datetime('now')""",
#         (shop["id"],)
#     )
#     
#     return ShopWithStats(
#         **shop,
#         products_count=products_count["cnt"],
#         orders_count=orders_count["cnt"],
#         subscription_active=subscription is not None
#     )


@router.post("/", response_model=Shop)
async def create_shop(
    shop_data: ShopCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Создаёт новый магазин."""
    try:
        # Проверяем, нет ли уже магазина
        existing = await db.fetch_one(
            "SELECT id FROM shops WHERE owner_id = ?",
            (current_user.id,)
        )
        if existing:
            raise HTTPException(status_code=400, detail="User already has a shop")
        
        # Подготавливаем данные, заменяя пустые строки на None
        shop_dict = shop_data.model_dump()
        for key, value in shop_dict.items():
            if isinstance(value, str) and value.strip() == "":
                shop_dict[key] = None
        
        shop_dict["owner_id"] = current_user.id
        
        shop_id = await db.insert("shops", shop_dict)
        
        shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
        if not shop:
            raise HTTPException(status_code=500, detail="Failed to retrieve created shop")
        
        return Shop(**shop)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating shop: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating shop: {str(e)}")


@router.get("/{shop_id}", response_model=ShopWithStats)
async def get_shop(
    shop_id: int,
    db: DatabaseService = Depends(get_db)
):
    """Получает магазин по ID."""
    shop = await db.fetch_one(
        "SELECT * FROM shops WHERE id = ? AND is_active = 1",
        (shop_id,)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Явно конвертируем pickup_enabled из INTEGER в boolean
    if "pickup_enabled" in shop:
        shop["pickup_enabled"] = bool(shop["pickup_enabled"]) if shop["pickup_enabled"] is not None else True
    
    products_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ? AND is_active = 1 AND quantity > 0",
        (shop_id,)
    )
    orders_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM orders WHERE shop_id = ? AND status = 'delivered'",
        (shop_id,)
    )
    
    return ShopWithStats(
        **shop,
        products_count=products_count["cnt"],
        orders_count=orders_count["cnt"],
        subscription_active=False
    )


@router.patch("/{shop_id}", response_model=Shop)
async def update_shop(
    shop_id: int,
    shop_data: ShopUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет информацию о магазине."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[SHOP UPDATE] Received update request for shop_id={shop_id}, user_id={current_user.id}")
    logger.info(f"[SHOP UPDATE] Shop data received: {shop_data.model_dump(exclude_unset=True)}")
    
    # Проверяем, что пользователь является владельцем
    shop = await db.fetch_one(
        "SELECT * FROM shops WHERE id = ? AND owner_id = ?",
        (shop_id, current_user.id)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found or access denied")
    
    update_data = shop_data.model_dump(exclude_unset=True)
    logger.info(f"[SHOP UPDATE] Parsed update_data (before processing): {update_data}")
    
    # Заменяем пустые строки на None
    for key, value in update_data.items():
        if isinstance(value, str) and value.strip() == "":
            update_data[key] = None
            logger.info(f"[SHOP UPDATE] Converted empty string to None for field: {key}")
    
    logger.info(f"[SHOP UPDATE] Final update_data: {update_data}")
    
    if not update_data:
        logger.warning("[SHOP UPDATE] No data to update")
        return Shop(**shop)
    
    # Обновляем данные
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values()) + [shop_id]
    
    logger.info(f"[SHOP UPDATE] Executing SQL: UPDATE shops SET {set_clause} WHERE id = ?")
    logger.info(f"[SHOP UPDATE] Values: {values}")
    
    await db.execute(
        f"UPDATE shops SET {set_clause} WHERE id = ?",
        tuple(values)
    )
    await db.commit()
    
    updated_shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
    logger.info(f"[SHOP UPDATE] Shop updated successfully. New address: {updated_shop.get('address')}")
    return Shop(**updated_shop)


@router.post("/{shop_id}/photo")
async def upload_shop_photo(
    shop_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Загружает фото магазина."""
    # Проверяем права доступа
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE id = ? AND owner_id = ?",
        (shop_id, current_user.id)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found or access denied")
    
    # Проверяем, что файл был передан
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Photo file is required")
    
    # Логируем информацию о файле для отладки
    print(f"[SHOP PHOTO] Received file: filename={file.filename}, content_type={file.content_type}")
    
    media_service = get_media_service()
    photo_url, _ = await media_service.save_shop_photo(file, shop_id)
    
    # Обновляем URL фото в базе данных
    await db.execute(
        "UPDATE shops SET photo_url = ? WHERE id = ?",
        (photo_url, shop_id)
    )
    await db.commit()
    
    return {"photo_url": photo_url}


@router.get("/{shop_id}/products", response_model=List)
async def get_shop_products(
    shop_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: DatabaseService = Depends(get_db)
):
    """Получает товары магазина."""
    shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Если пользователь - владелец магазина, показываем все товары (включая неактивные)
    # Иначе показываем только активные товары
    is_owner = current_user and current_user.id == shop["owner_id"]
    
    # Получаем данные магазина для добавления в товары
    shop_name = shop.get("name")
    shop_rating = shop.get("average_rating")
    shop_reviews_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM shop_reviews WHERE shop_id = ?",
        (shop_id,)
    )
    shop_reviews_count = shop_reviews_count["cnt"] if shop_reviews_count else 0
    
    if is_owner:
        products = await db.fetch_all(
            "SELECT * FROM products WHERE shop_id = ? ORDER BY created_at DESC",
            (shop_id,)
        )
    else:
        products = await db.fetch_all(
            "SELECT * FROM products WHERE shop_id = ? AND is_active = 1 AND quantity > 0 ORDER BY created_at DESC",
            (shop_id,)
        )
    
    # Получаем медиа для каждого товара
    result = []
    for product in products:
        media = await db.fetch_all(
            "SELECT * FROM product_media WHERE product_id = ? ORDER BY is_primary DESC, id ASC",
            (product["id"],)
        )
        product_dict = dict(product)
        product_dict["media"] = [dict(m) for m in media]
        # Добавляем primary_image для удобства (первое изображение из media или первое с is_primary=1)
        primary_media = next((m for m in media if m.get("is_primary") == 1), None) or (media[0] if media else None)
        product_dict["primary_image"] = primary_media["url"] if primary_media else None
        
        # Добавляем данные магазина для отображения в карточке товара
        product_dict["shop_name"] = shop_name
        
        # Преобразуем рейтинг из Decimal в float
        if shop_rating is not None:
            from decimal import Decimal
            if isinstance(shop_rating, Decimal):
                product_dict["shop_rating"] = float(shop_rating)
            elif isinstance(shop_rating, (int, float)):
                product_dict["shop_rating"] = float(shop_rating)
            elif isinstance(shop_rating, str):
                try:
                    product_dict["shop_rating"] = float(shop_rating)
                except (ValueError, TypeError):
                    product_dict["shop_rating"] = None
            else:
                product_dict["shop_rating"] = None
        else:
            product_dict["shop_rating"] = None
            
        product_dict["shop_reviews_count"] = int(shop_reviews_count) if shop_reviews_count else 0
        
        result.append(product_dict)
    
    return result

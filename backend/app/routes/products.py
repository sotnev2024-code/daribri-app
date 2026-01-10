"""
API Routes для товаров.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from typing import List, Optional

from ..models.product import Product, ProductCreate, ProductUpdate, ProductWithMedia, ProductMedia
from ..models.user import User
from ..services.database import DatabaseService, get_db
from ..services.media import get_media_service
from .users import get_current_user

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    trending: Optional[bool] = None,
    discounted: Optional[bool] = None,
    in_stock: Optional[bool] = Query(None, description="Только товары в наличии (quantity > 0)"),
    db: DatabaseService = Depends(get_db)
):
    """Получает список товаров с фильтрацией."""
    # Добавляем проверку подписки: показываем только товары магазинов с активной подпиской
    conditions = [
        "p.is_active = 1", 
        "s.is_active = 1",
        """EXISTS (
            SELECT 1 FROM shop_subscriptions ss 
            WHERE ss.shop_id = s.id 
            AND ss.is_active = 1 
            AND ss.end_date > datetime('now')
        )"""
    ]
    params = []
    
    # По умолчанию показываем только товары в наличии
    if in_stock is None or in_stock:
        conditions.append("p.quantity > 0")
    
    if category_id:
        # Включаем подкатегории
        subcats = await db.fetch_all(
            "SELECT id FROM categories WHERE parent_id = ?", (category_id,)
        )
        cat_ids = [category_id] + [s["id"] for s in subcats]
        placeholders = ",".join(["?" for _ in cat_ids])
        conditions.append(f"p.category_id IN ({placeholders})")
        params.extend(cat_ids)
    
    if search:
        # Используем LOWER для регистронезависимого поиска кириллицы
        search_lower = search.lower()
        conditions.append("(LOWER(p.name) LIKE ? OR LOWER(p.description) LIKE ?)")
        params.extend([f"%{search_lower}%", f"%{search_lower}%"])
    
    if min_price is not None:
        conditions.append("COALESCE(p.discount_price, p.price) >= ?")
        params.append(min_price)
    
    if max_price is not None:
        conditions.append("COALESCE(p.discount_price, p.price) <= ?")
        params.append(max_price)
    
    if trending:
        conditions.append("p.is_trending = 1")
    
    if discounted:
        conditions.append("p.discount_price IS NOT NULL")
    
    where_clause = " AND ".join(conditions)
    params.extend([limit, skip])
    
    products = await db.fetch_all(
        f"""SELECT p.*, 
                   s.name as shop_name,
                   s.id as shop_id,
                   s.average_rating as shop_rating,
                   c.name as category_name
            FROM products p
            JOIN shops s ON p.shop_id = s.id
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE {where_clause}
            ORDER BY p.is_trending DESC, p.created_at DESC
            LIMIT ? OFFSET ?""",
        tuple(params)
    )
    
    # Получаем все медиа для каждого товара
    result = []
    for product in products:
        product_dict = dict(product)
        media = await db.fetch_all(
            """SELECT id, media_type, url, is_primary, sort_order 
               FROM product_media 
               WHERE product_id = ? 
               ORDER BY 
                   CASE WHEN media_type = 'video' THEN 0 ELSE 1 END,
                   is_primary DESC, 
                   sort_order""",
            (product["id"],)
        )
        product_dict["media"] = [dict(m) for m in media]
        product_dict["primary_image"] = media[0]["url"] if media else None
        result.append(product_dict)
    
    return result


@router.get("/trending", response_model=List[dict])
async def get_trending_products(
    limit: int = Query(10, ge=1, le=50),
    db: DatabaseService = Depends(get_db)
):
    """Получает трендовые товары."""
    products = await db.fetch_all(
        """SELECT p.*, 
                  s.name as shop_name,
                  (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as primary_image
           FROM products p
           JOIN shops s ON p.shop_id = s.id
           WHERE p.is_active = 1 AND p.is_trending = 1 AND p.quantity > 0 AND s.is_active = 1
           AND EXISTS (
               SELECT 1 FROM shop_subscriptions ss 
               WHERE ss.shop_id = s.id 
               AND ss.is_active = 1 
               AND ss.end_date > datetime('now')
           )
           ORDER BY p.views_count DESC
           LIMIT ?""",
        (limit,)
    )
    return products


@router.get("/discounted", response_model=List[dict])
async def get_discounted_products(
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_db)
):
    """Получает товары со скидкой."""
    products = await db.fetch_all(
        """SELECT p.*, 
                  s.name as shop_name,
                  (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as primary_image
           FROM products p
           JOIN shops s ON p.shop_id = s.id
           WHERE p.is_active = 1 AND p.discount_price IS NOT NULL AND p.quantity > 0 AND s.is_active = 1
           ORDER BY p.discount_percent DESC
           LIMIT ?""",
        (limit,)
    )
    return products


@router.get("/{product_id}", response_model=ProductWithMedia)
async def get_product(
    product_id: int,
    x_telegram_id: Optional[int] = Query(None),
    db: DatabaseService = Depends(get_db)
):
    """Получает товар по ID с медиа и информацией о магазине.
    Для владельца магазина возвращает товар даже если он неактивен.
    """
    # Сначала проверяем, является ли пользователь владельцем
    is_owner = False
    if x_telegram_id:
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?", (x_telegram_id,)
        )
        if user:
            product_check = await db.fetch_one(
                """SELECT s.owner_id FROM products p
                   JOIN shops s ON p.shop_id = s.id
                   WHERE p.id = ?""",
                (product_id,)
            )
            if product_check and product_check["owner_id"] == user["id"]:
                is_owner = True
    
    # Если владелец - показываем товар даже если неактивен, иначе только активный
    if is_owner:
        product = await db.fetch_one(
            """SELECT p.*, 
                      s.name as shop_name,
                      s.photo_url as shop_photo,
                      s.average_rating as shop_rating,
                      c.name as category_name
               FROM products p
               JOIN shops s ON p.shop_id = s.id
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE p.id = ?""",
            (product_id,)
        )
    else:
        product = await db.fetch_one(
            """SELECT p.*, 
                      s.name as shop_name,
                      s.photo_url as shop_photo,
                      s.average_rating as shop_rating,
                      c.name as category_name
               FROM products p
               JOIN shops s ON p.shop_id = s.id
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE p.id = ? AND p.is_active = 1""",
            (product_id,)
        )
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Получаем количество отзывов магазина
    reviews_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM shop_reviews WHERE shop_id = ?",
        (product["shop_id"],)
    )
    
    # Увеличиваем счётчик просмотров
    await db.execute(
        "UPDATE products SET views_count = views_count + 1 WHERE id = ?",
        (product_id,)
    )
    await db.commit()
    
    # Получаем медиа (видео сначала)
    media = await db.fetch_all(
        """SELECT * FROM product_media 
           WHERE product_id = ? 
           ORDER BY 
               CASE WHEN media_type = 'video' THEN 0 ELSE 1 END,
               is_primary DESC, 
               sort_order""",
        (product_id,)
    )
    
    # Проверяем избранное и корзину
    is_favorite = False
    in_cart = False
    
    if x_telegram_id:
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?", (x_telegram_id,)
        )
        if user:
            fav = await db.fetch_one(
                "SELECT id FROM favorites WHERE user_id = ? AND product_id = ?",
                (user["id"], product_id)
            )
            is_favorite = fav is not None
            
            cart = await db.fetch_one(
                "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
                (user["id"], product_id)
            )
            in_cart = cart is not None
    
    try:
        # Преобразуем словарь product в нужный формат
        product_dict = dict(product)
        
        # Удаляем поля, которые не нужны в Product (они будут добавлены отдельно)
        product_dict.pop('shop_name', None)
        product_dict.pop('shop_photo', None)
        product_dict.pop('shop_rating', None)
        product_dict.pop('category_name', None)
        
        return ProductWithMedia(
            **product_dict,
            shop_reviews_count=reviews_count["cnt"] if reviews_count else 0,
            media=[ProductMedia(**m) for m in media],
            shop_name=product.get('shop_name'),
            shop_photo=product.get('shop_photo'),
            shop_rating=product.get('shop_rating'),
            category_name=product.get('category_name'),
            is_favorite=is_favorite,
            in_cart=in_cart
        )
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to create ProductWithMedia: {e}")
        print(f"[ERROR] Product dict keys: {list(product.keys())}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing product: {str(e)}")


@router.post("/", response_model=Product)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Создаёт новый товар."""
    # Проверяем магазин пользователя
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE owner_id = ? AND is_active = 1",
        (current_user.id,)
    )
    if not shop:
        raise HTTPException(status_code=400, detail="User does not have an active shop")
    
    # Проверяем подписку
    subscription = await db.fetch_one(
        """SELECT sp.max_products 
           FROM shop_subscriptions ss
           JOIN subscription_plans sp ON ss.plan_id = sp.id
           WHERE ss.shop_id = ? AND ss.is_active = 1 AND ss.end_date > datetime('now')""",
        (shop["id"],)
    )
    if not subscription:
        raise HTTPException(status_code=403, detail="Active subscription required")
    
    # Проверяем лимит товаров
    products_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ?",
        (shop["id"],)
    )
    if products_count["cnt"] >= subscription["max_products"]:
        raise HTTPException(status_code=403, detail="Product limit reached")
    
    # Создаём товар
    product_dict = product_data.model_dump(exclude={"media"})
    product_dict["shop_id"] = shop["id"]
    
    # Конвертируем Decimal в float для SQLite
    if product_dict.get("price") is not None:
        product_dict["price"] = float(product_dict["price"])
    if product_dict.get("discount_price") is not None:
        product_dict["discount_price"] = float(product_dict["discount_price"])
    
    product_id = await db.insert("products", product_dict)
    
    # Добавляем медиа
    if product_data.media:
        for i, media in enumerate(product_data.media):
            await db.insert("product_media", {
                "product_id": product_id,
                **media.model_dump(),
                "is_primary": i == 0 if not any(m.is_primary for m in product_data.media) else media.is_primary
            })
    
    product = await db.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
    return Product(**product)


@router.post("/{product_id}/media", response_model=dict)
async def upload_product_media(
    product_id: int,
    files: List[UploadFile] = File(...),
    is_primary: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
):
    """Загружает медиа файлы для товара."""
    # Проверяем владельца товара
    product = await db.fetch_one(
        """SELECT p.* FROM products p
           JOIN shops s ON p.shop_id = s.id
           WHERE p.id = ? AND s.owner_id = ?""",
        (product_id, current_user.id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or access denied")
    
    media_service = get_media_service()
    uploaded_media = []
    
    try:
        for i, file in enumerate(files):
            # Первый файл помечается как primary, если is_primary=True
            file_is_primary = is_primary and i == 0
            
            # Сохраняем файл на диск
            url, file_path = await media_service.save_media(
                file=file,
                product_id=product_id,
                is_primary=file_is_primary
            )
            
            # Сохраняем информацию в БД
            media_record = await db.insert("product_media", {
                "product_id": product_id,
                "media_type": "photo" if file.content_type and file.content_type.startswith("image/") else "video",
                "url": url,
                "thumbnail_url": None,
                "sort_order": i,
                "is_primary": file_is_primary
            })
            
            uploaded_media.append({
                "id": media_record,
                "url": url,
                "media_type": "photo" if file.content_type and file.content_type.startswith("image/") else "video"
            })
        
        return {
            "success": True,
            "message": f"Загружено {len(uploaded_media)} файлов",
            "media": uploaded_media
        }
    
    except HTTPException:
        raise
    except Exception as e:
        # Если ошибка, удаляем уже загруженные файлы
        for media in uploaded_media:
            await media_service.delete_media(media["url"])
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")


@router.delete("/{product_id}/media/{media_id}", response_model=dict)
async def delete_product_media(
    product_id: int,
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
):
    """Удаляет медиа файл товара."""
    # Проверяем владельца товара
    product = await db.fetch_one(
        """SELECT p.* FROM products p
           JOIN shops s ON p.shop_id = s.id
           WHERE p.id = ? AND s.owner_id = ?""",
        (product_id, current_user.id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or access denied")
    
    # Получаем информацию о медиа
    media = await db.fetch_one(
        "SELECT * FROM product_media WHERE id = ? AND product_id = ?",
        (media_id, product_id)
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Удаляем файл с диска
    media_service = get_media_service()
    await media_service.delete_media(media["url"])
    
    # Удаляем запись из БД
    await db.execute(
        "DELETE FROM product_media WHERE id = ?",
        (media_id,)
    )
    
    return {"success": True, "message": "Медиа файл удалён"}


@router.patch("/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет товар."""
    # Проверяем владельца
    product = await db.fetch_one(
        """SELECT p.* FROM products p
           JOIN shops s ON p.shop_id = s.id
           WHERE p.id = ? AND s.owner_id = ?""",
        (product_id, current_user.id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or access denied")
    
    try:
        update_data = {k: v for k, v in product_update.model_dump().items() if v is not None}
        
        # Обновляем товар
        if update_data:
            # Формируем UPDATE запрос
            set_parts = []
            values = []
            
            for key, value in update_data.items():
                if key == "updated_at":
                    # updated_at обрабатываем отдельно через SQL функцию
                    set_parts.append("updated_at = datetime('now')")
                else:
                    set_parts.append(f"{key} = ?")
                    # Конвертируем Decimal в float для SQLite
                    from decimal import Decimal
                    if isinstance(value, Decimal):
                        values.append(float(value))
                    else:
                        values.append(value)
            
            # Всегда обновляем updated_at
            if "updated_at" not in update_data:
                set_parts.append("updated_at = datetime('now')")
            
            set_clause = ", ".join(set_parts)
            values.append(product_id)
            
            query = f"UPDATE products SET {set_clause} WHERE id = ?"
            print(f"[UPDATE] Query: {query}")
            print(f"[UPDATE] Values: {values}")
            
            cursor = await db.execute(query, tuple(values))
            await db.commit()
            
            print(f"[UPDATE] Product {product_id} updated: {list(update_data.keys())}, rows affected: {cursor.rowcount}")
        
        updated = await db.fetch_one("SELECT * FROM products WHERE id = ?", (product_id,))
        if not updated:
            raise HTTPException(status_code=404, detail="Product not found after update")
        
        return Product(**updated)
    except Exception as e:
        await db.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Ошибка обновления товара {product_id}: {e}")
        print(f"[ERROR] Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления товара: {str(e)}")


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Удаляет товар (деактивирует) и все его медиа файлы."""
    product = await db.fetch_one(
        """SELECT p.* FROM products p
           JOIN shops s ON p.shop_id = s.id
           WHERE p.id = ? AND s.owner_id = ?""",
        (product_id, current_user.id)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or access denied")
    
    try:
        # Проверяем, используется ли товар в заказах
        order_items_check = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM order_items WHERE product_id = ?",
            (product_id,)
        )
        has_order_items = order_items_check and order_items_check["cnt"] > 0
        
        if has_order_items:
            # Если товар используется в заказах, сохраняем название товара и обнуляем product_id
            # Это сохранит историю заказов с названием товара
            product_name = product.get("name", "Удаленный товар")
            cursor_order_items = await db.execute(
                """UPDATE order_items 
                   SET product_id = NULL, 
                       product_name = COALESCE(product_name, ?)
                   WHERE product_id = ?""",
                (product_name, product_id)
            )
            print(f"[DELETE] Updated {cursor_order_items.rowcount} order items (saved product name)")
        
        # Удаляем связанные записи в правильном порядке
        # 1. Удаляем из корзины всех пользователей
        cursor1 = await db.execute("DELETE FROM cart_items WHERE product_id = ?", (product_id,))
        print(f"[DELETE] Removed {cursor1.rowcount} cart items")
        
        # 2. Удаляем из избранного всех пользователей
        cursor2 = await db.execute("DELETE FROM favorites WHERE product_id = ?", (product_id,))
        print(f"[DELETE] Removed {cursor2.rowcount} favorites")
        
        # 3. Удаляем медиа файлы из базы данных
        cursor3 = await db.execute("DELETE FROM product_media WHERE product_id = ?", (product_id,))
        print(f"[DELETE] Removed {cursor3.rowcount} media records")
        
        # 4. Удаляем медиа файлы с диска
        try:
            media_service = get_media_service()
            await media_service.delete_product_media(product_id)
            print(f"[DELETE] Removed media files from disk")
        except Exception as media_error:
            print(f"[DELETE] Warning: Error removing media files: {media_error}")
            # Продолжаем даже если удаление файлов не удалось
        
        # 5. Полностью удаляем товар из базы данных
        cursor4 = await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        print(f"[DELETE] Removed product from database: {cursor4.rowcount} rows")
        
        await db.commit()
        print(f"[DELETE] Product {product_id} deleted successfully")
        
        message = "Product deleted"
        if has_order_items:
            message += f" (removed from {order_items_check['cnt']} order items)"
        
        return {"message": message}
    except Exception as e:
        await db.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Ошибка удаления товара {product_id}: {e}")
        print(f"[ERROR] Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления товара: {str(e)}")





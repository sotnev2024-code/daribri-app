"""
API Routes для избранного.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..models.favorite import Favorite, FavoriteCreate
from ..models.user import User
from ..services.database import DatabaseService, get_db
from .users import get_current_user

router = APIRouter()


@router.get("/")
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает избранные товары пользователя."""
    favorites = await db.fetch_all(
        """SELECT f.id as favorite_id, f.created_at as added_at,
                  p.*,
                  s.name as shop_name,
                  s.id as shop_id,
                  s.average_rating as shop_rating,
                  (SELECT COUNT(*) FROM shop_reviews WHERE shop_id = s.id) as shop_reviews_count,
                  c.name as category_name
           FROM favorites f
           JOIN products p ON f.product_id = p.id
           JOIN shops s ON p.shop_id = s.id
           LEFT JOIN categories c ON p.category_id = c.id
           WHERE f.user_id = ? AND p.is_active = 1
           ORDER BY f.created_at DESC""",
        (current_user.id,)
    )
    
    # Получаем все медиа для каждого товара и обрабатываем данные
    result = []
    for favorite in favorites:
        favorite_dict = dict(favorite)
        
        # Преобразуем Decimal в float для JSON сериализации
        if favorite_dict.get("shop_rating") is not None:
            from decimal import Decimal
            if isinstance(favorite_dict["shop_rating"], Decimal):
                favorite_dict["shop_rating"] = float(favorite_dict["shop_rating"])
            elif isinstance(favorite_dict["shop_rating"], str):
                try:
                    favorite_dict["shop_rating"] = float(favorite_dict["shop_rating"])
                except (ValueError, TypeError):
                    favorite_dict["shop_rating"] = None
        
        # Преобразуем shop_reviews_count в int
        if favorite_dict.get("shop_reviews_count") is not None:
            if isinstance(favorite_dict["shop_reviews_count"], str):
                try:
                    favorite_dict["shop_reviews_count"] = int(favorite_dict["shop_reviews_count"])
                except (ValueError, TypeError):
                    favorite_dict["shop_reviews_count"] = 0
            elif not isinstance(favorite_dict["shop_reviews_count"], int):
                favorite_dict["shop_reviews_count"] = int(favorite_dict["shop_reviews_count"]) if favorite_dict["shop_reviews_count"] else 0
        
        # Получаем все медиа для товара
        media = await db.fetch_all(
            """SELECT id, media_type, url, is_primary, sort_order 
               FROM product_media 
               WHERE product_id = ? 
               ORDER BY 
                   CASE WHEN media_type = 'video' THEN 0 ELSE 1 END,
                   is_primary DESC, 
                   sort_order""",
            (favorite["id"],)
        )
        favorite_dict["media"] = [dict(m) for m in media]
        favorite_dict["primary_image"] = media[0]["url"] if media else None
        result.append(favorite_dict)
    
    return result


@router.post("/", response_model=Favorite)
async def add_to_favorites(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Добавляет товар в избранное."""
    # Проверяем товар
    product = await db.fetch_one(
        "SELECT id FROM products WHERE id = ? AND is_active = 1",
        (favorite_data.product_id,)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Проверяем, есть ли уже в избранном
    existing = await db.fetch_one(
        "SELECT id FROM favorites WHERE user_id = ? AND product_id = ?",
        (current_user.id, favorite_data.product_id)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Product already in favorites")
    
    favorite_id = await db.insert("favorites", {
        "user_id": current_user.id,
        "product_id": favorite_data.product_id
    })
    
    favorite = await db.fetch_one("SELECT * FROM favorites WHERE id = ?", (favorite_id,))
    return Favorite(**favorite)


@router.delete("/{product_id}")
async def remove_from_favorites(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Удаляет товар из избранного."""
    result = await db.delete(
        "favorites",
        "user_id = ? AND product_id = ?",
        (current_user.id, product_id)
    )
    if result == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    return {"message": "Removed from favorites"}


@router.post("/toggle/{product_id}")
async def toggle_favorite(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Переключает статус избранного."""
    # Проверяем товар
    product = await db.fetch_one(
        "SELECT id FROM products WHERE id = ? AND is_active = 1",
        (product_id,)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    existing = await db.fetch_one(
        "SELECT id FROM favorites WHERE user_id = ? AND product_id = ?",
        (current_user.id, product_id)
    )
    
    if existing:
        await db.delete("favorites", "id = ?", (existing["id"],))
        return {"is_favorite": False}
    else:
        await db.insert("favorites", {
            "user_id": current_user.id,
            "product_id": product_id
        })
        return {"is_favorite": True}







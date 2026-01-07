"""
API Routes для отзывов.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from ..models.review import ShopReview, ShopReviewCreate
from ..models.user import User
from ..services.database import DatabaseService, get_db
from .users import get_current_user

router = APIRouter()


@router.get("/shop/{shop_id}", response_model=List[ShopReview])
async def get_shop_reviews(
    shop_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseService = Depends(get_db)
):
    """Получает отзывы о магазине."""
    reviews = await db.fetch_all(
        """SELECT r.*,
                  COALESCE(u.first_name, u.username, 'Пользователь') as user_name
           FROM shop_reviews r
           JOIN users u ON r.user_id = u.id
           WHERE r.shop_id = ?
           ORDER BY r.created_at DESC
           LIMIT ? OFFSET ?""",
        (shop_id, limit, skip)
    )
    return [ShopReview(**review) for review in reviews]


@router.get("/shop/{shop_id}/stats")
async def get_shop_review_stats(
    shop_id: int,
    db: DatabaseService = Depends(get_db)
):
    """Получает статистику отзывов магазина."""
    stats = await db.fetch_one(
        """SELECT 
              COUNT(*) as total,
              ROUND(AVG(rating), 2) as average,
              SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as five_star,
              SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as four_star,
              SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as three_star,
              SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as two_star,
              SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as one_star
           FROM shop_reviews
           WHERE shop_id = ?""",
        (shop_id,)
    )
    return stats


@router.post("/", response_model=ShopReview)
async def create_review(
    review_data: ShopReviewCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Создаёт отзыв о магазине."""
    # Проверяем магазин
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE id = ? AND is_active = 1",
        (review_data.shop_id,)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Проверяем, был ли заказ (для верифицированного отзыва)
    is_verified = False
    if review_data.order_id:
        order = await db.fetch_one(
            """SELECT id FROM orders 
               WHERE id = ? AND user_id = ? AND shop_id = ? AND status = 'delivered'""",
            (review_data.order_id, current_user.id, review_data.shop_id)
        )
        if order:
            is_verified = True
    
    # Проверяем, не оставлял ли уже отзыв
    existing = await db.fetch_one(
        "SELECT id FROM shop_reviews WHERE user_id = ? AND shop_id = ?",
        (current_user.id, review_data.shop_id)
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this shop")
    
    review_id = await db.insert("shop_reviews", {
        "shop_id": review_data.shop_id,
        "user_id": current_user.id,
        "order_id": review_data.order_id,
        "rating": review_data.rating,
        "comment": review_data.comment,
        "is_verified": is_verified
    })
    
    review = await db.fetch_one(
        """SELECT r.*, 
                  COALESCE(u.first_name, u.username, 'Пользователь') as user_name
           FROM shop_reviews r
           JOIN users u ON r.user_id = u.id
           WHERE r.id = ?""",
        (review_id,)
    )
    return ShopReview(**review)


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Удаляет отзыв."""
    review = await db.fetch_one(
        "SELECT id FROM shop_reviews WHERE id = ? AND user_id = ?",
        (review_id, current_user.id)
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    await db.delete("shop_reviews", "id = ?", (review_id,))
    return {"message": "Review deleted"}







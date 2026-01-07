"""
Модели отзывов.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ShopReviewBase(BaseModel):
    """Базовая модель отзыва о магазине."""
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ShopReviewCreate(ShopReviewBase):
    """Модель для создания отзыва."""
    shop_id: int
    order_id: Optional[int] = None


class ShopReview(ShopReviewBase):
    """Полная модель отзыва."""
    id: int
    shop_id: int
    user_id: int
    order_id: Optional[int] = None
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    # Дополнительные поля для отображения
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

    class Config:
        from_attributes = True







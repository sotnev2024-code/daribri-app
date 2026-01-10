"""
Модели магазина.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ShopBase(BaseModel):
    """Базовая модель магазина."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    photo_url: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    working_hours: Optional[str] = None


class ShopCreate(ShopBase):
    """Модель для создания магазина."""
    pass


class ShopUpdate(BaseModel):
    """Модель для обновления магазина."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    photo_url: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    working_hours: Optional[str] = None


class Shop(ShopBase):
    """Полная модель магазина."""
    id: int
    owner_id: int
    average_rating: Optional[Decimal] = Decimal("0.00")
    total_reviews: Optional[int] = 0
    redemption_rate: Optional[Decimal] = Decimal("0.00")
    is_verified: Optional[bool] = False
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Дополнительные поля из базы данных
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    telegram: Optional[str] = None
    instagram: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = 0
    views_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ShopWithStats(Shop):
    """Магазин с дополнительной статистикой."""
    products_count: int = 0
    orders_count: int = 0
    subscription_active: bool = False







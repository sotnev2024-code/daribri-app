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


class Shop(ShopBase):
    """Полная модель магазина."""
    id: int
    owner_id: int
    average_rating: Decimal = Decimal("0.00")
    total_reviews: int = 0
    redemption_rate: Decimal = Decimal("0.00")
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShopWithStats(Shop):
    """Магазин с дополнительной статистикой."""
    products_count: int = 0
    orders_count: int = 0
    subscription_active: bool = False







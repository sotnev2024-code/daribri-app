"""
Модели подписок.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SubscriptionPlanBase(BaseModel):
    """Базовая модель плана подписки."""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    duration_days: int = Field(..., ge=1)
    max_products: int = Field(50, ge=1)
    features: Optional[Dict[str, Any]] = None


class SubscriptionPlan(SubscriptionPlanBase):
    """Полная модель плана подписки."""
    id: int
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class ShopSubscriptionBase(BaseModel):
    """Базовая модель подписки магазина."""
    plan_id: int


class ShopSubscriptionCreate(ShopSubscriptionBase):
    """Модель для создания подписки."""
    shop_id: int


class ShopSubscription(ShopSubscriptionBase):
    """Полная модель подписки магазина."""
    id: int
    shop_id: int
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    payment_id: Optional[str] = None
    created_at: datetime
    # Дополнительные поля
    plan_name: Optional[str] = None
    days_remaining: Optional[int] = None

    class Config:
        from_attributes = True







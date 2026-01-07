"""
Модели промокодов.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class PromoType(str, Enum):
    """Тип промокода."""
    PERCENT = "percent"  # Скидка в процентах
    FIXED = "fixed"  # Скидка фиксированной суммой
    FREE_DELIVERY = "free_delivery"  # Бесплатная доставка


class PromoBase(BaseModel):
    """Базовая модель промокода."""
    code: str = Field(..., min_length=1, max_length=50, description="Код промокода")
    promo_type: PromoType = Field(..., description="Тип промокода")
    value: Decimal = Field(..., ge=0, description="Значение скидки (процент или сумма)")
    description: Optional[str] = None
    is_active: bool = True
    # Условия применения
    use_once: bool = False  # Можно использовать только один раз
    first_order_only: bool = False  # Только для первого заказа
    shop_id: Optional[int] = None  # Только для определенного магазина
    min_order_amount: Optional[Decimal] = Field(None, ge=0, description="Минимальная сумма заказа")
    valid_from: Optional[date] = None  # Дата начала действия
    valid_until: Optional[date] = None  # Дата окончания действия


class PromoCreate(PromoBase):
    """Модель для создания промокода."""
    pass


class Promo(PromoBase):
    """Полная модель промокода."""
    id: int
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0  # Количество использований

    class Config:
        from_attributes = True


class PromoValidate(BaseModel):
    """Модель для проверки промокода."""
    code: str
    shop_id: int
    total_amount: Decimal
    is_first_order: bool = False


class PromoValidationResult(BaseModel):
    """Результат проверки промокода."""
    valid: bool
    promo: Optional[Promo] = None
    discount_amount: Decimal = Decimal("0")
    discount_type: Optional[str] = None
    message: Optional[str] = None



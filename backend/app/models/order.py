"""
Модели заказа.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class OrderItemBase(BaseModel):
    """Базовая модель товара в заказе."""
    product_id: int
    quantity: int = Field(..., ge=1)


class OrderItemCreate(OrderItemBase):
    """Модель для добавления товара в заказ."""
    pass


class OrderItem(OrderItemBase):
    """Полная модель товара в заказе."""
    id: int
    order_id: int
    price: Decimal
    discount_price: Optional[Decimal] = None
    # Дополнительные поля для отображения
    product_name: Optional[str] = None
    product_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    """Базовая модель заказа."""
    delivery_address: Optional[str] = None
    delivery_date: Optional[date] = None
    delivery_time: Optional[str] = None  # Время доставки
    delivery_type: Optional[str] = "delivery"  # 'delivery' или 'pickup'
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    comment: Optional[str] = None
    payment_method: Optional[str] = None
    promo_code: Optional[str] = None  # Промокод


class OrderCreate(OrderBase):
    """Модель для создания заказа."""
    shop_id: int
    items: List[OrderItemCreate]


class Order(OrderBase):
    """Полная модель заказа."""
    id: int
    user_id: int
    shop_id: int
    order_number: str
    status: str = "pending"
    total_amount: Decimal
    discount_amount: Decimal = Decimal("0")
    promo_discount_amount: Decimal = Decimal("0")  # Скидка по промокоду
    delivery_fee: Decimal = Decimal("0")  # Стоимость доставки
    payment_status: str = "pending"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderWithItems(Order):
    """Заказ с товарами."""
    items: List[OrderItem] = []
    shop_name: Optional[str] = None







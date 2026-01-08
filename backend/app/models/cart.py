"""
Модели корзины.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CartItemBase(BaseModel):
    """Базовая модель элемента корзины."""
    product_id: int
    quantity: int = Field(1, ge=1)


class CartItemCreate(CartItemBase):
    """Модель для добавления в корзину."""
    pass


class CartItemUpdate(BaseModel):
    """Модель для обновления элемента корзины."""
    quantity: int = Field(..., ge=1)
    
    @model_validator(mode='before')
    @classmethod
    def validate_quantity_before(cls, data):
        """Обрабатывает случай когда quantity приходит как объект."""
        if isinstance(data, dict) and 'quantity' in data:
            quantity_value = data['quantity']
            # Если quantity - это объект, извлекаем значение
            if isinstance(quantity_value, dict) and 'quantity' in quantity_value:
                print(f"[MODEL] Found nested quantity: {quantity_value}")
                data['quantity'] = quantity_value['quantity']
            elif not isinstance(quantity_value, int):
                try:
                    data['quantity'] = int(quantity_value)
                except (ValueError, TypeError) as e:
                    print(f"[MODEL] Error converting quantity to int: {e}")
                    raise ValueError(f"Invalid quantity: {quantity_value}")
        return data
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Валидатор для quantity."""
        if isinstance(v, dict):
            # Если все еще словарь, извлекаем значение
            if 'quantity' in v:
                return int(v['quantity'])
            else:
                raise ValueError(f"Invalid quantity format: dict without 'quantity' key: {v}")
        if not isinstance(v, int):
            try:
                return int(v)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid quantity type: {type(v)}, value: {v}")
        return v


class CartItem(CartItemBase):
    """Полная модель элемента корзины."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CartItemWithProduct(CartItem):
    """Элемент корзины с информацией о товаре."""
    product_name: str
    product_price: Decimal
    product_discount_price: Optional[Decimal] = None
    product_image_url: Optional[str] = None
    shop_id: int
    shop_name: str
    is_available: bool = True







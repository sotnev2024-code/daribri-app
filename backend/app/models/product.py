"""
Модели товара.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class ProductMediaBase(BaseModel):
    """Базовая модель медиа файла товара."""
    media_type: str = Field(..., pattern="^(photo|video)$")
    url: str  # URL или base64 данные изображения
    thumbnail_url: Optional[str] = None
    sort_order: int = 0
    is_primary: bool = False


class ProductMedia(ProductMediaBase):
    """Полная модель медиа файла."""
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    """Базовая модель товара."""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    discount_price: Optional[Decimal] = Field(None, ge=0)
    discount_percent: Optional[int] = Field(None, ge=0, le=100)
    quantity: int = Field(0, ge=0)
    is_trending: bool = False
    category_id: Optional[int] = None


class ProductCreate(ProductBase):
    """Модель для создания товара."""
    media: Optional[List[ProductMediaBase]] = None


class ProductUpdate(BaseModel):
    """Модель для обновления товара."""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    discount_price: Optional[Decimal] = Field(None, ge=0)
    discount_percent: Optional[int] = Field(None, ge=0, le=100)
    quantity: Optional[int] = Field(None, ge=0)
    is_trending: Optional[bool] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None


class Product(ProductBase):
    """Полная модель товара."""
    id: int
    shop_id: int
    is_active: bool = True
    views_count: int = 0
    sales_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductWithMedia(Product):
    """Товар с медиа файлами."""
    media: List[ProductMedia] = []
    shop_name: Optional[str] = None
    shop_photo: Optional[str] = None
    shop_description: Optional[str] = None
    shop_rating: Optional[float] = None
    shop_reviews_count: int = 0
    category_name: Optional[str] = None
    is_favorite: bool = False
    in_cart: bool = False





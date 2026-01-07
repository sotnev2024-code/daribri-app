"""
Модели баннеров.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BannerBase(BaseModel):
    """Базовая модель баннера."""
    title: str = Field(..., max_length=255, description="Заголовок баннера")
    emoji: Optional[str] = Field(None, max_length=10, description="Эмодзи для баннера")
    description: Optional[str] = Field(None, max_length=500, description="Описание баннера")
    image_url: Optional[str] = Field(None, max_length=500, description="URL изображения (опционально)")
    link_type: str = Field("none", description="Тип ссылки: none, category, product, shop, external")
    link_value: Optional[str] = Field(None, max_length=500, description="Значение ссылки (ID категории/товара/магазина или внешний URL)")
    display_order: int = Field(0, ge=0, description="Порядок отображения (меньше = выше)")
    is_active: bool = Field(True, description="Активен ли баннер")


class BannerCreate(BannerBase):
    """Модель для создания баннера."""
    pass


class BannerUpdate(BaseModel):
    """Модель для обновления баннера."""
    title: Optional[str] = Field(None, max_length=255)
    emoji: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    link_type: Optional[str] = Field(None, description="Тип ссылки: none, category, product, shop, external")
    link_value: Optional[str] = Field(None, max_length=500)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class Banner(BannerBase):
    """Полная модель баннера."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


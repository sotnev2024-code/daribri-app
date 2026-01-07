"""
Модели категории товаров.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    """Базовая модель категории."""
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    icon: Optional[str] = None
    description: Optional[str] = None
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    """Модель для создания категории."""
    parent_id: Optional[int] = None


class Category(CategoryBase):
    """Полная модель категории."""
    id: int
    parent_id: Optional[int] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryWithChildren(Category):
    """Категория с подкатегориями."""
    children: List["CategoryWithChildren"] = []
    products_count: int = 0


# Для разрешения forward reference
CategoryWithChildren.model_rebuild()







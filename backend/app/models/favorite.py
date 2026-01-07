"""
Модели избранного.
"""

from datetime import datetime
from pydantic import BaseModel


class FavoriteBase(BaseModel):
    """Базовая модель избранного."""
    product_id: int


class FavoriteCreate(FavoriteBase):
    """Модель для добавления в избранное."""
    pass


class Favorite(FavoriteBase):
    """Полная модель избранного."""
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True







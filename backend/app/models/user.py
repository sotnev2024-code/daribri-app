"""
Модели пользователя.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Базовая модель пользователя."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    language_code: str = "ru"
    is_premium: bool = False


class UserCreate(UserBase):
    """Модель для создания пользователя."""
    pass


class UserUpdate(BaseModel):
    """Модель для обновления пользователя."""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    language_code: Optional[str] = None


class User(UserBase):
    """Полная модель пользователя."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True







"""
Модели для напоминаний о событиях.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReminderBase(BaseModel):
    """Базовая модель напоминания."""
    event_date: date = Field(..., description="Дата события")
    event_description: str = Field(..., max_length=500, description="Описание события")
    is_sent: bool = Field(default=False, description="Отправлено ли напоминание")


class ReminderCreate(ReminderBase):
    """Модель для создания напоминания."""
    user_id: int = Field(..., description="ID пользователя")


class Reminder(ReminderBase):
    """Полная модель напоминания."""
    id: int
    user_id: int
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


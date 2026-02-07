"""
Middleware для бота.
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject


class AuthMiddleware(BaseMiddleware):
    """Middleware для авторизации пользователей."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обрабатывает событие."""
        # Бот отвечает только в личных сообщениях (private)
        # Игнорируем сообщения из групп, супергрупп и каналов
        if isinstance(event, Message):
            if event.chat.type != "private":
                return  # Игнорируем, не передаём обработчику
        elif isinstance(event, CallbackQuery):
            if event.message and event.message.chat.type != "private":
                return  # Игнорируем callback из групп
        
        # Получаем пользователя
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user:
            # Добавляем данные пользователя в контекст
            data["telegram_user"] = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
                "is_premium": user.is_premium or False
            }
        
        return await handler(event, data)







"""
Telegram Bot - точка входа.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .handlers import router
from .middlewares import AuthMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main(bot_token: str, webapp_url: str):
    """Запуск бота."""
    from aiogram.fsm.storage.memory import MemoryStorage
    
    # Создаём хранилище состояний для FSM
    storage = MemoryStorage()
    
    # Создаём бота
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создаём диспетчер с хранилищем состояний
    dp = Dispatcher(storage=storage)
    
    # Добавляем middleware
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Регистрируем роутеры
    dp.include_router(router)
    
    # Сохраняем webapp_url в bot для использования в хендлерах
    bot.webapp_url = webapp_url
    
    logger.info("Bot starting...")
    
    try:
        # Удаляем webhook если был
        await bot.delete_webhook(drop_pending_updates=True)
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def run_bot(bot_token: str, webapp_url: str):
    """Синхронная обёртка для запуска бота."""
    asyncio.run(main(bot_token, webapp_url))


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")
    
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    run_bot(BOT_TOKEN, WEBAPP_URL)


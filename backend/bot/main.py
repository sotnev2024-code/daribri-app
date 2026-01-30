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
    
    # Запускаем периодическую проверку напоминаний в фоне
    from backend.app.services.reminder_service import reminder_service
    reminder_task = asyncio.create_task(reminder_service.start_periodic_check(interval_minutes=5))
    logger.info("Reminder service started (checking every 5 minutes)")
    
    try:
        # Удаляем webhook если был (с несколькими попытками)
        try:
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.warning(f"Found active webhook: {webhook_info.url}, deleting...")
                await bot.delete_webhook(drop_pending_updates=True)
                # Ждем немного, чтобы Telegram обработал запрос
                await asyncio.sleep(1)
                # Проверяем еще раз
                webhook_info = await bot.get_webhook_info()
                if webhook_info.url:
                    logger.warning(f"Webhook still active, trying again...")
                    await bot.delete_webhook(drop_pending_updates=True)
                    await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"Error checking/deleting webhook: {e}")
        
        # Запускаем polling
        await dp.start_polling(bot, allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"])
    finally:
        # Отменяем задачу проверки напоминаний
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
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


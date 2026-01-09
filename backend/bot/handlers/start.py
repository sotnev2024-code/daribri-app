"""
Обработчик команды /start.
"""

from aiogram import Router, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

router = Router()


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    from backend.app.config import settings
    
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, command: CommandObject):
    """Обработчик команды /start с поддержкой deep link."""
    # Создаём или обновляем пользователя в базе
    try:
        db = await get_db()
        
        user = await db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        
        if not user:
            # Создаём нового пользователя
            user_id = await db.insert("users", {
                "telegram_id": message.from_user.id,
                "username": message.from_user.username or f"user_{message.from_user.id}",
                "first_name": message.from_user.first_name or "",
                "last_name": message.from_user.last_name or "",
                "language_code": message.from_user.language_code or "ru",
                "is_premium": message.from_user.is_premium or False
            })
            print(f"[START] Created new user with ID: {user_id}, telegram_id: {message.from_user.id}")
        else:
            # Обновляем данные существующего пользователя
            await db.update(
                "users",
                {
                    "username": message.from_user.username or f"user_{message.from_user.id}",
                    "first_name": message.from_user.first_name or "",
                    "last_name": message.from_user.last_name or "",
                    "language_code": message.from_user.language_code or "ru",
                    "is_premium": message.from_user.is_premium or False
                },
                "telegram_id = ?",
                (message.from_user.id,)
            )
        
        await db.disconnect()
    except Exception as e:
        print(f"[START] Error saving user: {e}")
        # Продолжаем выполнение даже если не удалось сохранить
    
    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
    
    # Проверяем deep link параметр
    deep_link = command.args
    product_id = None
    
    if deep_link and deep_link.startswith('product_'):
        try:
            product_id = int(deep_link.replace('product_', ''))
            # Добавляем параметр товара к URL
            webapp_url_with_product = f"{webapp_url}?product={product_id}"
        except ValueError:
            webapp_url_with_product = webapp_url
    else:
        webapp_url_with_product = webapp_url
    
    # Если пришли по ссылке на товар
    if product_id:
        welcome_text = """
<b>🎁 Вам отправили подарок!</b>

Нажмите кнопку ниже, чтобы посмотреть товар.
"""
        button_text = "🎁 Посмотреть товар"
    else:
        welcome_text = """
<b>👋 Добро пожаловать в Дарибри!</b>

Здесь вы найдёте:
🌸 Свежие букеты и цветы
🪴 Комнатные растения
🍰 Сладости и выпечку
🎁 Подарочные наборы

<i>Нажмите кнопку ниже, чтобы открыть каталог</i>
"""
        button_text = "🛒 Открыть каталог"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=button_text,
            web_app=WebAppInfo(url=webapp_url_with_product)
        )]
    ])
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard
    )







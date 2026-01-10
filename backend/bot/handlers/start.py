"""
Обработчик команды /start.
"""

from aiogram import Router, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, FSInputFile
from pathlib import Path

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
        try:
            # Получаем данные товара
            db = await get_db()
            
            product = await db.fetch_one(
                """SELECT p.*, s.name as shop_name
                   FROM products p
                   JOIN shops s ON p.shop_id = s.id
                   WHERE p.id = ? AND p.is_active = 1""",
                (product_id,)
            )
            
            if product:
                # Получаем первую фотографию (не видео)
                media = await db.fetch_all(
                    """SELECT url, media_type 
                       FROM product_media 
                       WHERE product_id = ? AND media_type = 'photo'
                       ORDER BY is_primary DESC, sort_order ASC
                       LIMIT 1""",
                    (product_id,)
                )
                
                # Формируем текст карточки товара
                product_name = product.get("name", "Товар")
                price = product.get("discount_price") or product.get("price", 0)
                formatted_price = f"{float(price):,.0f}".replace(",", " ") + " ₽"
                description = product.get("description", "").strip()
                
                # Формируем подпись
                caption = f"<b>{product_name}</b>\n\n💰 {formatted_price}"
                if description:
                    # Ограничиваем описание до 800 символов (лимит Telegram для подписи)
                    caption += f"\n\n{description[:800]}" + ("..." if len(description) > 800 else "")
                
                button_text = "Посмотреть товар"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=button_text,
                        web_app=WebAppInfo(url=webapp_url_with_product)
                    )]
                ])
                
                # Если есть фото, отправляем фото с подписью
                if media and len(media) > 0:
                    photo_url = media[0]["url"]
                    photo_sent = False
                    
                    # Пробуем отправить как локальный файл (если файл существует)
                    if photo_url.startswith("/media/"):
                        from backend.app.config import settings
                        # Путь к файлу: /media/products/5/filename.jpg -> uploads/products/5/filename.jpg
                        photo_path_str = photo_url.replace("/media/", "")
                        photo_path = settings.UPLOADS_DIR / photo_path_str
                        
                        if photo_path.exists() and photo_path.is_file():
                            try:
                                await message.answer_photo(
                                    photo=FSInputFile(str(photo_path)),
                                    caption=caption,
                                    reply_markup=keyboard
                                )
                                photo_sent = True
                            except Exception as file_error:
                                print(f"[START] Error sending photo from file: {file_error}")
                                import traceback
                                traceback.print_exc()
                                # Пробуем через URL
                                pass
                    
                    # Если не удалось отправить как файл, пробуем через URL
                    if not photo_sent:
                        if photo_url.startswith("/"):
                            # Относительный URL - формируем полный URL
                            # Используем webapp_url как базовый URL (он обычно указывает на домен)
                            base_url = webapp_url.replace('/?', '').replace('?product=', '').rstrip('/')
                            if 'localhost' in base_url or '127.0.0.1' in base_url:
                                base_url = 'https://daribri.ru'
                            full_photo_url = f"{base_url}{photo_url}"
                        else:
                            # Абсолютный URL
                            full_photo_url = photo_url
                        
                        try:
                            await message.answer_photo(
                                photo=full_photo_url,
                                caption=caption,
                                reply_markup=keyboard
                            )
                            photo_sent = True
                        except Exception as url_error:
                            print(f"[START] Error sending photo from URL: {url_error}")
                            import traceback
                            traceback.print_exc()
                            # Если не удалось отправить фото, отправляем текстовое сообщение
                            await message.answer(
                                caption,
                                reply_markup=keyboard
                            )
                else:
                    # Если нет фото, отправляем текстовое сообщение
                    await message.answer(
                        caption,
                        reply_markup=keyboard
                    )
                
                await db.disconnect()
                return
            else:
                await db.disconnect()
        except Exception as e:
            print(f"[START] Error loading product {product_id}: {e}")
            import traceback
            traceback.print_exc()
            try:
                await db.disconnect()
            except:
                pass
        
        # Если товар не найден или произошла ошибка, отправляем обычное сообщение
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
        reply_markup=keyboard,
        parse_mode="HTML"
    )







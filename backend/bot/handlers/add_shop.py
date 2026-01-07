"""
Обработчик команды /add_shop для заявок на добавление магазина.
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, 
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import uuid
import hashlib
from pathlib import Path
import aiofiles
import os
import io

router = Router()


class ShopRequestStates(StatesGroup):
    """Состояния для формы заявки на магазин."""
    waiting_for_name = State()
    waiting_for_photo = State()
    waiting_for_description = State()
    waiting_for_address = State()
    waiting_for_phone = State()
    waiting_for_owner_name = State()
    waiting_for_owner_phone = State()
    waiting_for_owner_telegram = State()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    db = DatabaseService()
    await db.connect()
    return db


@router.message(Command("add_shop"))
async def cmd_add_shop(message: Message, state: FSMContext):
    """Информация о создании магазина и подписке."""
    await state.clear()
    
    # Проверяем, есть ли у пользователя уже какая-либо заявка (любого статуса)
    try:
        db = await get_db()
        
        # Проверяем наличие любой заявки от этого пользователя
        existing_request = await db.fetch_one(
            "SELECT id, name, status, created_at FROM shop_requests WHERE telegram_user_id = ? ORDER BY created_at DESC LIMIT 1",
            (message.from_user.id,)
        )
        
        await db.disconnect()
        
        if existing_request:
            # У пользователя уже есть заявка
            from datetime import datetime
            
            status = existing_request['status']
            status_info = {
                "pending": ("⏳ На рассмотрении", "Ваша заявка находится на рассмотрении. Дождитесь решения."),
                "approved": ("✅ Одобрена", "Ваша заявка была одобрена. Если у вас есть вопросы, свяжитесь с поддержкой."),
                "rejected": ("❌ Отклонена", "Ваша заявка была отклонена. Если у вас есть вопросы, свяжитесь с поддержкой.")
            }
            
            status_emoji_text, status_message = status_info.get(status, ("📝 Обработана", "Ваша заявка уже была обработана."))
            
            created_at = existing_request['created_at']
            # Парсим дату создания для красивого отображения
            try:
                if isinstance(created_at, str):
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_date = created_at
                date_str = created_date.strftime("%d.%m.%Y %H:%M")
            except:
                date_str = str(created_at)
            
            text = f"""
<b>{status_emoji_text} У вас уже есть заявка</b>

Вы не можете подать новую заявку.

<b>Ваша заявка:</b>
📝 #{existing_request['id']} - {existing_request['name']}
📊 Статус: {status_emoji_text}
📅 Дата подачи: {date_str}

{status_message}
"""
            await message.answer(text)
            return
        
    except Exception as check_error:
        print(f"Error checking existing request: {check_error}")
        # Продолжаем, если ошибка при проверке
    
    # Показываем информационное сообщение
    info_text = """
<b>🏪 Создание магазина</b>

Станьте продавцом на нашей платформе и начните продавать свои товары!

<b>Что нужно сделать:</b>

1️⃣ <b>Подайте заявку</b>
   Заполните форму с информацией о вашем магазине

2️⃣ <b>Дождитесь одобрения</b>
   Мы рассмотрим вашу заявку в течение 24 часов

3️⃣ <b>Оформите подписку</b>
   Выберите подходящий тарифный план

4️⃣ <b>Начните продавать</b>
   Добавляйте товары и получайте заказы

<b>Преимущества:</b>
✨ Доступ к тысячам покупателей
📊 Удобная панель управления
💳 Гибкая система подписки
📈 Детальная аналитика продаж

Готовы начать? Нажмите кнопку ниже, чтобы заполнить заявку!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать создание магазина", callback_data="start_shop_request")]
    ])
    
    await message.answer(
        info_text,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "start_shop_request")
async def start_shop_request_process(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс подачи заявки на магазин после нажатия кнопки."""
    await state.clear()
    
    # Проверяем еще раз на всякий случай
    try:
        db = await get_db()
        
        existing_request = await db.fetch_one(
            "SELECT id FROM shop_requests WHERE telegram_user_id = ? LIMIT 1",
            (callback.from_user.id,)
        )
        
        await db.disconnect()
        
        if existing_request:
            await callback.answer("❌ У вас уже есть заявка", show_alert=True)
            return
        
    except Exception as check_error:
        print(f"Error checking existing request: {check_error}")
    
    text = """
<b>📝 Заявка на добавление магазина</b>

Вы можете подать заявку на добавление вашего магазина в нашу платформу.

Для этого нужно заполнить форму с информацией о магазине и контактными данными владельца.

<b>Шаг 1/8: Название магазина</b>

Введите название вашего магазина:
"""
    
    await callback.message.edit_text(text)
    await callback.message.answer(
        "Введите название вашего магазина:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_name)
    await callback.answer()


@router.message(ShopRequestStates.waiting_for_name, F.text != "❌ Отменить")
async def process_name(message: Message, state: FSMContext):
    """Обрабатывает название магазина."""
    name = message.text.strip()
    
    if len(name) < 3:
        await message.answer("❌ Название магазина должно содержать минимум 3 символа. Попробуйте еще раз:")
        return
    
    await state.update_data(name=name)
    
    await message.answer(
        "<b>Шаг 2/8: Фотография магазина</b>\n\nОтправьте фотографию магазина:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_photo)


@router.message(ShopRequestStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает фотографию магазина и сохраняет её как файл."""
    photo = message.photo[-1]  # Берем фото наибольшего размера
    file_id = photo.file_id
    
    try:
        # Получаем файл от Telegram
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        if not file_path:
            raise ValueError("File path is empty")
        
        # Определяем расширение файла
        extension = Path(file_path).suffix or ".jpg"
        
        # Скачиваем файл
        # В aiogram 3.x используем bot.download_file() который возвращает BufferedIOBase
        downloaded_file = await bot.download_file(file_path)
        try:
            content = downloaded_file.read()
        finally:
            downloaded_file.close()
        
        if not content:
            raise ValueError("Downloaded file is empty")
        
        # Создаём хэш для уникального имени
        file_hash = hashlib.md5(content).hexdigest()[:12]
        
        # Путь к директории для заявок
        from backend.app.config import settings
        requests_photos_dir = Path(settings.UPLOADS_DIR) / "shop_requests"
        
        # Создаём директорию с правами на запись
        requests_photos_dir.mkdir(parents=True, exist_ok=True)
        
        # Проверяем права на запись
        if not os.access(requests_photos_dir, os.W_OK):
            raise PermissionError(f"No write permission to directory: {requests_photos_dir}")
        
        # Генерируем имя файла
        filename = f"request_photo_{file_hash}{extension}"
        file_path_local = requests_photos_dir / filename
        
        # Сохраняем файл на диск
        async with aiofiles.open(file_path_local, 'wb') as f:
            await f.write(content)
        
        # Проверяем, что файл действительно сохранен
        if not file_path_local.exists():
            raise IOError(f"File was not saved: {file_path_local}")
        
        # Сохраняем имя файла (будем использовать для копирования при одобрении)
        photo_url = filename
        
        # Сохраняем file_id (для отправки в группу) и URL файла в состоянии
        await state.update_data(photo_file_id=file_id, photo_url=photo_url)
        
        await message.answer(
            "<b>Шаг 3/8: Описание магазина</b>\n\nВведите описание вашего магазина:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ShopRequestStates.waiting_for_description)
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"Error saving photo: {error_msg}")
        print(f"Traceback: {error_trace}")
        await message.answer(
            f"❌ Произошла ошибка при загрузке фотографии: {error_msg}\n\nПопробуйте отправить фото еще раз:"
        )


@router.message(ShopRequestStates.waiting_for_photo)
async def process_photo_invalid(message: Message):
    """Обрабатывает неверный ввод фотографии."""
    await message.answer("❌ Пожалуйста, отправьте фотографию (не текст). Попробуйте еще раз:")


@router.message(ShopRequestStates.waiting_for_description, F.text != "❌ Отменить")
async def process_description(message: Message, state: FSMContext):
    """Обрабатывает описание магазина."""
    description = message.text.strip()
    
    if len(description) < 10:
        await message.answer("❌ Описание должно содержать минимум 10 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(description=description)
    
    await message.answer(
        "<b>Шаг 4/8: Адрес магазина</b>\n\nВведите адрес магазина:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_address)


@router.message(ShopRequestStates.waiting_for_address, F.text != "❌ Отменить")
async def process_address(message: Message, state: FSMContext):
    """Обрабатывает адрес магазина."""
    address = message.text.strip()
    
    if len(address) < 5:
        await message.answer("❌ Адрес должен содержать минимум 5 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(address=address)
    
    await message.answer(
        "<b>Шаг 5/8: Номер телефона магазина</b>\n\nВведите номер телефона магазина (например, +7 999 123-45-67):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_phone)


@router.message(ShopRequestStates.waiting_for_phone, F.text != "❌ Отменить")
async def process_phone(message: Message, state: FSMContext):
    """Обрабатывает номер телефона магазина."""
    phone = message.text.strip()
    
    # Простая проверка формата телефона
    if len(phone) < 10:
        await message.answer("❌ Номер телефона слишком короткий. Попробуйте еще раз:")
        return
    
    await state.update_data(phone=phone)
    
    await message.answer(
        "<b>Шаг 6/8: ФИО владельца</b>\n\nВведите ФИО владельца магазина (например, Иванов Иван Иванович):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_owner_name)


@router.message(ShopRequestStates.waiting_for_owner_name, F.text != "❌ Отменить")
async def process_owner_name(message: Message, state: FSMContext):
    """Обрабатывает ФИО владельца."""
    owner_name = message.text.strip()
    
    if len(owner_name) < 5:
        await message.answer("❌ ФИО должно содержать минимум 5 символов. Попробуйте еще раз:")
        return
    
    await state.update_data(owner_name=owner_name)
    
    await message.answer(
        "<b>Шаг 7/8: Номер телефона владельца</b>\n\nВведите номер телефона владельца (например, +7 999 123-45-67):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_owner_phone)


@router.message(ShopRequestStates.waiting_for_owner_phone, F.text != "❌ Отменить")
async def process_owner_phone(message: Message, state: FSMContext):
    """Обрабатывает номер телефона владельца."""
    owner_phone = message.text.strip()
    
    if len(owner_phone) < 10:
        await message.answer("❌ Номер телефона слишком короткий. Попробуйте еще раз:")
        return
    
    await state.update_data(owner_phone=owner_phone)
    
    await message.answer(
        "<b>Шаг 8/8: Telegram владельца</b>\n\nВведите Telegram аккаунт владельца (например, @username или username):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ShopRequestStates.waiting_for_owner_telegram)


@router.message(ShopRequestStates.waiting_for_owner_telegram, F.text != "❌ Отменить")
async def process_owner_telegram(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает Telegram владельца и сохраняет заявку."""
    owner_telegram = message.text.strip()
    
    # Убираем @ если есть
    if owner_telegram.startswith('@'):
        owner_telegram = owner_telegram[1:]
    
    if len(owner_telegram) < 3:
        await message.answer("❌ Telegram аккаунт слишком короткий. Попробуйте еще раз:")
        return
    
    # Получаем все данные из состояния
    data = await state.get_data()
    
    # Сохраняем заявку в базу данных
    try:
        db = await get_db()
        
        # Создаём таблицу если её нет
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                photo_file_id TEXT,
                photo_url TEXT,
                description TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                owner_phone TEXT NOT NULL,
                owner_telegram TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                group_message_id INTEGER,
                shop_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        
        # Сохраняем заявку
        request_id = await db.insert("shop_requests", {
            "telegram_user_id": message.from_user.id,
            "name": data["name"],
            "photo_file_id": data.get("photo_file_id"),
            "photo_url": data.get("photo_url"),
            "description": data["description"],
            "address": data["address"],
            "phone": data["phone"],
            "owner_name": data["owner_name"],
            "owner_phone": data["owner_phone"],
            "owner_telegram": owner_telegram,
            "status": "pending"
        })
        
        # Отправляем заявку в группу
        try:
            from backend.app.config import settings
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            group_id = settings.SHOP_REQUESTS_GROUP_ID
            topic_id = settings.SHOP_REQUESTS_TOPIC_ID
            
            # Формируем текст заявки
            request_text = f"""
<b>📝 Новая заявка на магазин #{request_id}</b>

<b>Информация о магазине:</b>
🏪 Название: {data['name']}
📍 Адрес: {data['address']}
📞 Телефон: {data['phone']}
📝 Описание: {data['description']}

<b>Владелец:</b>
👤 ФИО: {data['owner_name']}
📱 Телефон: {data['owner_phone']}
💬 Telegram: @{owner_telegram}

<b>От пользователя:</b> @{message.from_user.username or message.from_user.first_name} (ID: {message.from_user.id})
"""
            
            # Создаём клавиатуру с кнопками
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_shop_{request_id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_shop_{request_id}")
                ]
            ])
            
            # Отправляем сообщение в группу
            if data.get("photo_file_id"):
                # Если есть фото, отправляем с фото
                sent_message = await bot.send_photo(
                    chat_id=group_id,
                    photo=data["photo_file_id"],
                    caption=request_text,
                    reply_markup=keyboard,
                    message_thread_id=topic_id
                )
            else:
                # Если нет фото, отправляем только текст
                sent_message = await bot.send_message(
                    chat_id=group_id,
                    text=request_text,
                    reply_markup=keyboard,
                    message_thread_id=topic_id
                )
            
            # Сохраняем ID сообщения в базе
            await db.update(
                "shop_requests",
                {"group_message_id": sent_message.message_id},
                "id = ?",
                (request_id,)
            )
            await db.commit()
            
        except Exception as group_error:
            print(f"Error sending request to group: {group_error}")
            # Продолжаем даже если не удалось отправить в группу
        
        await db.disconnect()
        
        success_text = f"""
<b>✅ Заявка успешно отправлена!</b>

Ваша заявка на добавление магазина принята и находится на рассмотрении.

<b>Номер заявки:</b> #{request_id}

Мы свяжемся с вами в ближайшее время для уточнения деталей.

Спасибо за интерес к нашей платформе! 🌸
"""
        
        await message.answer(
            success_text,
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.clear()
        
    except Exception as e:
        print(f"Error saving shop request: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении заявки. Пожалуйста, попробуйте позже или свяжитесь с поддержкой.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


@router.message(F.text == "❌ Отменить")
async def cancel_handler(message: Message, state: FSMContext):
    """Обрабатывает отмену заявки."""
    await state.clear()
    await message.answer(
        "❌ Заявка отменена.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.callback_query(F.data.startswith("approve_shop_"))
async def approve_shop_request(callback: CallbackQuery, bot: Bot):
    """Обрабатывает одобрение заявки на магазин."""
    request_id = int(callback.data.split("_")[2])
    
    try:
        db = await get_db()
        
        # Получаем заявку
        request = await db.fetch_one(
            "SELECT * FROM shop_requests WHERE id = ?",
            (request_id,)
        )
        
        if not request:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return
        
        if request["status"] != "pending":
            await callback.answer("⚠️ Заявка уже обработана", show_alert=True)
            return
        
        # Получаем или создаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (request["telegram_user_id"],)
        )
        
        if not user:
            # Создаем пользователя (минимальные данные, так как мы не знаем полных данных)
            user_id = await db.insert("users", {
                "telegram_id": request["telegram_user_id"],
                "username": f"user_{request['telegram_user_id']}",
                "first_name": request["owner_name"].split()[0] if request["owner_name"] else "",
                "last_name": " ".join(request["owner_name"].split()[1:]) if len(request["owner_name"].split()) > 1 else "",
                "language_code": "ru",
                "is_premium": False
            })
        else:
            user_id = user["id"]
        
        # Проверяем, существует ли уже магазин для этого пользователя
        existing_shop = await db.fetch_one(
            "SELECT id FROM shops WHERE owner_id = ?",
            (user_id,)
        )
        
        shop_id = None
        if existing_shop:
            shop_id = existing_shop["id"]
            # Обновляем информацию о магазине из заявки
            shop_update_data = {
                "name": request["name"],
                "description": request["description"],
                "address": request["address"],
                "phone": request["phone"],
                "city": request["address"].split(",")[0] if request["address"] else None,
                "is_active": True
            }
            
            # Перемещаем фото если есть
            if request.get("photo_url"):
                # Копируем фото из shop_requests в shops/{shop_id}/
                from backend.app.config import settings
                import shutil
                
                # photo_url содержит только имя файла
                old_path = settings.UPLOADS_DIR / "shop_requests" / request["photo_url"]
                if old_path.exists():
                    shops_photos_dir = settings.UPLOADS_DIR / "shops" / str(shop_id)
                    shops_photos_dir.mkdir(parents=True, exist_ok=True)
                    new_filename = f"photo_{hashlib.md5(str(shop_id).encode()).hexdigest()[:12]}{old_path.suffix}"
                    new_path = shops_photos_dir / new_filename
                    shutil.copy2(old_path, new_path)
                    shop_update_data["photo_url"] = f"/media/shops/{shop_id}/{new_filename}"
            
            await db.update("shops", shop_update_data, "id = ?", (shop_id,))
        else:
            # Создаем магазин из заявки
            shop_photo_url = None
            if request.get("photo_url"):
                # Перемещаем фото из shop_requests в shops/{shop_id}/
                from backend.app.config import settings
                import shutil
                
                # photo_url содержит только имя файла
                old_path = settings.UPLOADS_DIR / "shop_requests" / request["photo_url"]
                if old_path.exists():
                    # Сначала создаем временный shop_id для создания директории
                    temp_shop_id = await db.insert("shops", {
                        "owner_id": user_id,
                        "name": request["name"],
                        "description": request["description"],
                        "address": request["address"],
                        "phone": request["phone"],
                        "city": request["address"].split(",")[0] if request["address"] else None,
                        "photo_url": None,
                        "is_active": True
                    })
                    shop_id = temp_shop_id
                    
                    shops_photos_dir = settings.UPLOADS_DIR / "shops" / str(shop_id)
                    shops_photos_dir.mkdir(parents=True, exist_ok=True)
                    new_filename = f"photo_{hashlib.md5(str(shop_id).encode()).hexdigest()[:12]}{old_path.suffix}"
                    new_path = shops_photos_dir / new_filename
                    shutil.copy2(old_path, new_path)
                    shop_photo_url = f"/media/shops/{shop_id}/{new_filename}"
                    
                    # Обновляем shop с photo_url
                    await db.update("shops", {"photo_url": shop_photo_url}, "id = ?", (shop_id,))
            else:
                shop_id = await db.insert("shops", {
                    "owner_id": user_id,
                    "name": request["name"],
                    "description": request["description"],
                    "address": request["address"],
                    "phone": request["phone"],
                    "city": request["address"].split(",")[0] if request["address"] else None,
                    "photo_url": None,
                    "is_active": True
                })
        
        # Обновляем статус заявки и сохраняем shop_id
        await db.update(
            "shop_requests",
            {"status": "approved", "shop_id": shop_id},
            "id = ?",
            (request_id,)
        )
        await db.commit()
        await db.disconnect()
        
        # Отправляем уведомление пользователю с кнопкой оплаты
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            notification_text = f"""
<b>✅ Заявка одобрена!</b>

Ваша заявка на добавление магазина <b>"{request['name']}"</b> была одобрена!

🎉 <b>Ваш магазин теперь доступен в приложении!</b>
Откройте каталог и перейдите в раздел "Профиль" - там вы найдете кнопку "Мой магазин".

Теперь вам нужно оформить подписку для размещения товаров.

<b>Подписка на 1 месяц:</b> 99 ₽

Нажмите кнопку ниже, чтобы оплатить подписку и начать продавать! 🌸

Также вы можете использовать команду /подписка в любое время.
"""
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить подписку", callback_data=f"pay_subscription_{request_id}")]
            ])
            await bot.send_message(
                chat_id=request["telegram_user_id"],
                text=notification_text,
                reply_markup=keyboard
            )
        except Exception as notify_error:
            print(f"Error sending notification: {notify_error}")
        
        # Обновляем сообщение в группе, убирая кнопки
        try:
            from backend.app.config import settings
            group_id = settings.SHOP_REQUESTS_GROUP_ID
            topic_id = settings.SHOP_REQUESTS_TOPIC_ID
            
            if request.get("group_message_id"):
                # Формируем обновленный текст
                updated_text = f"""
<b>📝 Заявка на магазин #{request_id} ✅ ОДОБРЕНА</b>

<b>Информация о магазине:</b>
🏪 Название: {request['name']}
📍 Адрес: {request['address']}
📞 Телефон: {request['phone']}
📝 Описание: {request['description']}

<b>Владелец:</b>
👤 ФИО: {request['owner_name']}
📱 Телефон: {request['owner_phone']}
💬 Telegram: @{request['owner_telegram']}

<b>Одобрено администратором</b>
"""
                
                # Обновляем сообщение без кнопок (убираем reply_markup)
                try:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=request["group_message_id"],
                        message_thread_id=topic_id,
                        text=updated_text,
                        reply_markup=None
                    )
                except Exception as edit_error:
                    # Если сообщение с фото, редактируем caption
                    if request.get("photo_file_id"):
                        try:
                            await bot.edit_message_caption(
                                chat_id=group_id,
                                message_id=request["group_message_id"],
                                message_thread_id=topic_id,
                                caption=updated_text,
                                reply_markup=None
                            )
                        except Exception as caption_error:
                            print(f"Error editing message caption: {caption_error}")
                            # Если не получается отредактировать, пытаемся просто убрать кнопки
                            try:
                                await bot.edit_message_reply_markup(
                                    chat_id=group_id,
                                    message_id=request["group_message_id"],
                                    message_thread_id=topic_id,
                                    reply_markup=None
                                )
                            except Exception as markup_error:
                                print(f"Error removing reply markup: {markup_error}")
                    else:
                        print(f"Error editing message text: {edit_error}")
                        # Если не получается отредактировать, пытаемся просто убрать кнопки
                        try:
                            await bot.edit_message_reply_markup(
                                chat_id=group_id,
                                message_id=request["group_message_id"],
                                message_thread_id=topic_id,
                                reply_markup=None
                            )
                        except Exception as markup_error:
                            print(f"Error removing reply markup: {markup_error}")
        except Exception as update_error:
            print(f"Error updating group message: {update_error}")
        
        await callback.answer("✅ Заявка одобрена")
        
    except Exception as e:
        print(f"Error approving shop request: {e}")
        await callback.answer("❌ Ошибка при одобрении заявки", show_alert=True)


@router.callback_query(F.data.startswith("reject_shop_"))
async def reject_shop_request(callback: CallbackQuery, bot: Bot):
    """Обрабатывает отклонение заявки на магазин."""
    request_id = int(callback.data.split("_")[2])
    
    try:
        db = await get_db()
        
        # Получаем заявку
        request = await db.fetch_one(
            "SELECT * FROM shop_requests WHERE id = ?",
            (request_id,)
        )
        
        if not request:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return
        
        if request["status"] != "pending":
            await callback.answer("⚠️ Заявка уже обработана", show_alert=True)
            return
        
        # Обновляем статус заявки
        await db.update(
            "shop_requests",
            {"status": "rejected"},
            "id = ?",
            (request_id,)
        )
        await db.commit()
        await db.disconnect()
        
        # Отправляем уведомление пользователю
        try:
            notification_text = f"""
<b>❌ Заявка отклонена</b>

К сожалению, ваша заявка на добавление магазина <b>"{request['name']}"</b> была отклонена.

Если у вас есть вопросы, пожалуйста, свяжитесь с поддержкой.
"""
            await bot.send_message(
                chat_id=request["telegram_user_id"],
                text=notification_text
            )
        except Exception as notify_error:
            print(f"Error sending notification: {notify_error}")
        
        # Обновляем сообщение в группе, убирая кнопки
        try:
            from backend.app.config import settings
            group_id = settings.SHOP_REQUESTS_GROUP_ID
            
            if request.get("group_message_id"):
                # Формируем обновленный текст
                updated_text = f"""
<b>📝 Заявка на магазин #{request_id} ❌ ОТКЛОНЕНА</b>

<b>Информация о магазине:</b>
🏪 Название: {request['name']}
📍 Адрес: {request['address']}
📞 Телефон: {request['phone']}
📝 Описание: {request['description']}

<b>Владелец:</b>
👤 ФИО: {request['owner_name']}
📱 Телефон: {request['owner_phone']}
💬 Telegram: @{request['owner_telegram']}

<b>Отклонено администратором</b>
"""
                
                # Обновляем сообщение без кнопок (убираем reply_markup)
                try:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=request["group_message_id"],
                        text=updated_text,
                        reply_markup=None
                    )
                except Exception as edit_error:
                    # Если сообщение с фото, редактируем caption
                    try:
                        await bot.edit_message_caption(
                            chat_id=group_id,
                            message_id=request["group_message_id"],
                            caption=updated_text,
                            reply_markup=None
                        )
                    except Exception as caption_error:
                        print(f"Error editing message caption: {caption_error}")
        except Exception as update_error:
            print(f"Error updating group message: {update_error}")
        
        await callback.answer("❌ Заявка отклонена")
        
    except Exception as e:
        print(f"Error rejecting shop request: {e}")
        await callback.answer("❌ Ошибка при отклонении заявки", show_alert=True)


@router.callback_query(F.data.startswith("pay_subscription_"))
async def handle_pay_subscription(callback: CallbackQuery, bot: Bot):
    """Создает платеж для подписки после одобрения заявки."""
    request_id = int(callback.data.split("_")[2])
    
    try:
        db = await get_db()
        
        # Получаем заявку
        request = await db.fetch_one(
            "SELECT * FROM shop_requests WHERE id = ?",
            (request_id,)
        )
        
        await db.disconnect()
        
        if not request:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return
        
        if request["status"] != "approved":
            await callback.answer("⚠️ Заявка не одобрена", show_alert=True)
            return
        
        # Получаем настройки YooKassa
        from backend.app.config import settings
        import os
        
        yookassa_token = os.getenv("API_KEY_YOOKASSA", "") or getattr(settings, "API_KEY_YOOKASSA", "")
        
        if not yookassa_token:
            await callback.answer("❌ Платежная система не настроена", show_alert=True)
            return
        
        # Создаем invoice для оплаты
        # Для Telegram Payments через YooKassa используем send_invoice
        invoice_payload = f"subscription_{request_id}_{uuid.uuid4().hex[:8]}"
        
        # Цена в копейках: 99 рублей = 9900 копеек
        prices = [LabeledPrice(label="Подписка на 1 месяц", amount=9900)]
        
        try:
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title="Подписка на размещение товаров",
                description=f"Подписка на 1 месяц для магазина \"{request['name']}\"\n\nПосле оплаты вы сможете добавлять товары и начать продавать!",
                payload=invoice_payload,
                provider_token=yookassa_token,
                currency="RUB",
                prices=prices,
                start_parameter=f"subscription_{request_id}"
            )
            await callback.answer()
        except Exception as invoice_error:
            print(f"Error sending invoice: {invoice_error}")
            await callback.answer("❌ Ошибка при создании платежа", show_alert=True)
            
    except Exception as e:
        print(f"Error handling pay subscription: {e}")
        await callback.answer("❌ Ошибка при создании платежа", show_alert=True)


@router.pre_checkout_query(F.invoice_payload.startswith("subscription_") & ~F.invoice_payload.startswith("subscription_direct_"))
async def pre_checkout_handler_add_shop(pre_checkout: PreCheckoutQuery, bot: Bot):
    """Обрабатывает запрос перед оплатой подписки после одобрения заявки."""
    # Все в порядке, подтверждаем платеж
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)


@router.message(
    F.successful_payment.invoice_payload.startswith("subscription_") 
    & ~F.successful_payment.invoice_payload.startswith("subscription_direct_")
    & ~F.successful_payment.invoice_payload.startswith("subscription_plan_")
)
async def successful_payment_handler_add_shop(message: Message, bot: Bot):
    """Обрабатывает успешную оплату подписки после одобрения заявки (старый формат: subscription_{request_id})."""
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    try:
        print(f"[ADD_SHOP] Processing subscription payment, payload: {payload}")
        # Извлекаем request_id из payload
        # Формат: subscription_{request_id}
        parts = payload.split("_")
        if len(parts) >= 2:
            try:
                request_id = int(parts[1])
                print(f"[ADD_SHOP] Parsed request_id={request_id}")
            except ValueError as e:
                await message.answer("❌ Ошибка обработки платежа. Обратитесь в поддержку.")
                print(f"[ADD_SHOP] Error parsing request_id from payload: {payload}, error: {e}")
                return
            
            db = await get_db()
            
            # Получаем заявку
            request = await db.fetch_one(
                "SELECT * FROM shop_requests WHERE id = ?",
                (request_id,)
            )
            
            if not request:
                await message.answer("❌ Заявка не найдена")
                return
            
            # Получаем shop_id из заявки (магазин уже создан при одобрении)
            from datetime import datetime, timedelta
            
            shop_id = request.get("shop_id")
            
            if not shop_id:
                await message.answer("❌ Магазин не найден. Обратитесь в поддержку.")
                return
            
            # Проверяем, что магазин существует
            shop = await db.fetch_one(
                "SELECT id FROM shops WHERE id = ?",
                (shop_id,)
            )
            
            if not shop:
                await message.answer("❌ Магазин не найден. Обратитесь в поддержку.")
                return
            
            # Получаем или создаем план подписки на 1 месяц
            plan = await db.fetch_one(
                "SELECT id FROM subscription_plans WHERE duration_days = 30 AND is_active = 1 LIMIT 1",
                ()
            )
            
            if not plan:
                # Создаем план подписки на 1 месяц (30 дней)
                plan_id = await db.insert("subscription_plans", {
                    "name": "Базовый план",
                    "description": "Подписка на 1 месяц",
                    "price": 1.0,
                    "duration_days": 30,
                    "max_products": 50,
                    "is_active": True,
                    "features": "{}"
                })
            else:
                plan_id = plan["id"]
            
            # Создаем подписку
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)
            
            subscription_id = await db.insert("shop_subscriptions", {
                "shop_id": shop_id,
                "plan_id": plan_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "is_active": True,
                "payment_id": payment.telegram_payment_charge_id or f"pay_{datetime.now().timestamp()}"
            })
            
            await db.commit()
            
            # Активируем товары магазина при активации подписки
            from backend.app.services.subscription_manager import SubscriptionManager
            activated = await SubscriptionManager.activate_shop_products(db, shop_id)
            if activated > 0:
                print(f"[SUBSCRIPTION] Activated {activated} products for shop {shop_id}")
            
            await db.disconnect()
            
            # Отправляем подтверждение
            success_text = f"""
<b>✅ Оплата успешно завершена!</b>

<b>Ваш магазин создан:</b>
🏪 {request['name']}

<b>Подписка активирована на 30 дней!</b>
📅 Действует до: {end_date.strftime('%d.%m.%Y')}

Теперь вы можете:
✨ Добавлять товары
📊 Управлять заказами
📈 Отслеживать статистику

Откройте каталог и начните продавать! 🚀
"""
            await message.answer(success_text)
            
    except Exception as e:
        print(f"Error processing successful payment: {e}")
        await message.answer("❌ Произошла ошибка при обработке платежа. Пожалуйста, свяжитесь с поддержкой.")


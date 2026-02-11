"""
Обработчик команды /post для публикации постов о магазине в Telegram канале.
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Optional

from backend.app.services.database import DatabaseService
from backend.app.config import settings

router = Router()


class PostStates(StatesGroup):
    """Состояния для создания поста."""
    waiting_for_channel = State()
    waiting_for_photo = State()
    waiting_for_text = State()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с кнопками пропустить и отменить."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def get_db():
    """Получает экземпляр базы данных."""
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


@router.message(Command("post", "пост"))
async def cmd_post(message: Message, state: FSMContext):
    """Команда для создания поста о магазине в канале."""
    print(f"[POST] Command received from user {message.from_user.id}")
    try:
        db = await get_db()
        
        # Проверяем, зарегистрирован ли пользователь
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы в системе.\n"
                "Используйте команду /start для регистрации."
            )
            await db.disconnect()
            return
        
        # Проверяем, есть ли у пользователя магазин
        shop = await db.fetch_one(
            "SELECT id, name FROM shops WHERE owner_id = ?",
            (user["id"],)
        )
        
        if not shop:
            await message.answer(
                "❌ У вас нет магазина.\n\n"
                "Для публикации постов необходимо сначала создать магазин.\n"
                "Используйте команду /add_shop для создания магазина."
            )
            await db.disconnect()
            return
        
        await db.disconnect()
        
        # Сохраняем ID магазина в состоянии
        await state.update_data(shop_id=shop["id"], shop_name=shop["name"])
        
        await message.answer(
            "📢 <b>Публикация поста о магазине</b>\n\n"
            "Для публикации поста в вашем Telegram канале необходимо:\n\n"
            "1️⃣ Добавить бота <b>@daribri_bot</b> администратором в ваш канал\n"
            "2️⃣ Дать боту права на публикацию сообщений\n\n"
            "После этого отправьте мне:\n"
            "• Пересланное сообщение из вашего канала, ИЛИ\n"
            "• Username канала (например: <code>@my_channel</code>)\n\n"
            "<i>Если канал приватный, используйте пересылку сообщения</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PostStates.waiting_for_channel)
        
    except Exception as e:
        print(f"[POST] Error in cmd_post: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(PostStates.waiting_for_channel)
async def process_channel(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает канал (через форвард или username)."""
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание поста отменено.", reply_markup=ReplyKeyboardRemove())
        return
    
    channel_id = None
    channel_username = None
    
    # Проверяем, переслано ли сообщение из канала
    if message.forward_from_chat:
        if message.forward_from_chat.type == "channel":
            channel_id = message.forward_from_chat.id
            channel_username = message.forward_from_chat.username
            print(f"[POST] Channel from forward: id={channel_id}, username={channel_username}")
    
    # Если не форвард, проверяем username в тексте
    if not channel_id and message.text:
        text = message.text.strip()
        # Убираем @ если есть
        if text.startswith("@"):
            text = text[1:]
        channel_username = text
        
        # Пытаемся получить информацию о канале
        try:
            chat = await bot.get_chat(f"@{channel_username}")
            if chat.type == "channel":
                channel_id = chat.id
                print(f"[POST] Channel from username: id={channel_id}, username={channel_username}")
        except Exception as e:
            print(f"[POST] Error getting channel by username: {e}")
            await message.answer(
                "❌ Не удалось найти канал.\n\n"
                "Попробуйте:\n"
                "• Переслать сообщение из канала, ИЛИ\n"
                "• Указать правильный username канала (например: <code>@my_channel</code>)\n\n"
                "<i>Убедитесь, что бот добавлен администратором в канал</i>",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            return
    
    if not channel_id:
        await message.answer(
            "❌ Не удалось определить канал.\n\n"
            "Попробуйте:\n"
            "• Переслать сообщение из канала, ИЛИ\n"
            "• Указать username канала (например: <code>@my_channel</code>)",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Проверяем, что бот является администратором канала
    try:
        bot_member = await bot.get_chat_member(channel_id, bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.answer(
                "❌ Бот не является администратором канала.\n\n"
                "Пожалуйста, добавьте бота <b>@daribri_bot</b> администратором в ваш канал "
                "и дайте ему права на публикацию сообщений.",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Проверяем права на публикацию
        if bot_member.status == "administrator" and not bot_member.can_post_messages:
            await message.answer(
                "❌ У бота нет прав на публикацию сообщений в канале.\n\n"
                "Пожалуйста, дайте боту права на публикацию сообщений в настройках канала.",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            return
            
    except Exception as e:
        print(f"[POST] Error checking bot permissions: {e}")
        await message.answer(
            "❌ Не удалось проверить права бота в канале.\n\n"
            "Убедитесь, что:\n"
            "• Бот добавлен администратором в канал\n"
            "• Бот имеет права на публикацию сообщений",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Сохраняем информацию о канале
    await state.update_data(channel_id=channel_id, channel_username=channel_username)
    
    # Сохраняем связь магазина с каналом в БД
    try:
        db = await get_db()
        data = await state.get_data()
        shop_id = data.get("shop_id")
        
        # Проверяем, существует ли уже связь
        existing = await db.fetch_one(
            "SELECT id FROM shop_channels WHERE shop_id = ? AND channel_id = ?",
            (shop_id, str(channel_id))
        )
        
        if not existing:
            # Создаём новую связь
            from datetime import datetime
            await db.insert("shop_channels", {
                "shop_id": shop_id,
                "channel_id": str(channel_id),
                "channel_username": channel_username,
                "created_at": datetime.now().isoformat()
            })
            await db.commit()
            print(f"[POST] Saved shop-channel link: shop_id={shop_id}, channel_id={channel_id}")
        
        await db.disconnect()
    except Exception as e:
        print(f"[POST] Error saving shop-channel link: {e}")
        # Продолжаем, даже если не удалось сохранить связь
    
    channel_display = f"@{channel_username}" if channel_username else f"ID: {channel_id}"
    
    await message.answer(
        f"✅ Канал определен: <b>{channel_display}</b>\n\n"
        "Теперь отправьте фото для поста (или нажмите 'Пропустить', если фото не нужно):",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PostStates.waiting_for_photo)


@router.message(PostStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Обрабатывает фото для поста."""
    # Сохраняем file_id фото
    photo = message.photo[-1]  # Берём фото наибольшего размера
    await state.update_data(photo_file_id=photo.file_id)
    
    await message.answer(
        "✅ Фото получено!\n\n"
        "Теперь введите текст поста:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PostStates.waiting_for_text)


@router.message(PostStates.waiting_for_photo, F.text)
async def process_photo_skip(message: Message, state: FSMContext):
    """Обрабатывает пропуск фото или отмену."""
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание поста отменено.", reply_markup=ReplyKeyboardRemove())
        return
    
    if message.text == "⏭ Пропустить":
        await message.answer(
            "✅ Фото пропущено.\n\n"
            "Теперь введите текст поста:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(PostStates.waiting_for_text)
    else:
        await message.answer(
            "Пожалуйста, отправьте фото или нажмите 'Пропустить'",
            reply_markup=get_skip_keyboard()
        )


@router.message(PostStates.waiting_for_photo)
async def process_photo_invalid(message: Message, state: FSMContext):
    """Обрабатывает некорректные сообщения в состоянии ожидания фото."""
    await message.answer(
        "Пожалуйста, отправьте фото или нажмите 'Пропустить'",
        reply_markup=get_skip_keyboard()
    )


@router.message(PostStates.waiting_for_text)
async def process_text(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает текст поста и публикует его в канал."""
    if not message.text:
        await message.answer(
            "Пожалуйста, отправьте текст поста.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание поста отменено.", reply_markup=ReplyKeyboardRemove())
        return
    
    text = message.text.strip()
    
    if len(text) > 4096:
        await message.answer(
            "❌ Текст слишком длинный (максимум 4096 символов).\n"
            "Пожалуйста, сократите текст.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    try:
        data = await state.get_data()
        shop_id = data.get("shop_id")
        shop_name = data.get("shop_name")
        channel_id = data.get("channel_id")
        channel_username = data.get("channel_username")
        photo_file_id = data.get("photo_file_id")
        
        if not shop_id or not channel_id:
            await message.answer("❌ Ошибка: данные не найдены. Начните заново с команды /post")
            await state.clear()
            return
        
        # Получаем username бота для создания ссылки на Mini App
        try:
            bot_info = await bot.get_me()
            bot_username = bot_info.username
        except Exception as e:
            print(f"[POST] Error getting bot info: {e}")
            bot_username = "Daribri_bot"  # Fallback
        
        # Создаём ссылку на Mini App с параметром shop
        # Формат: https://t.me/bot_username/app?shop=ID
        # Frontend обрабатывает параметр ?shop=ID из URL (app.js строка 1222)
        mini_app_url = f"https://t.me/{bot_username}/app?shop={shop_id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🛍 Открыть магазин", url=mini_app_url)
        ]])
        
        # Публикуем пост в канал
        if photo_file_id:
            # Пост с фото
            await bot.send_photo(
                chat_id=channel_id,
                photo=photo_file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Пост без фото
            await bot.send_message(
                chat_id=channel_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        channel_display = f"@{channel_username}" if channel_username else f"ID: {channel_id}"
        
        await message.answer(
            f"✅ <b>Пост успешно опубликован!</b>\n\n"
            f"📢 Канал: <b>{channel_display}</b>\n"
            f"🏪 Магазин: <b>{shop_name}</b>\n\n"
            f"Пост опубликован с кнопкой для перехода в ваш магазин.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        print(f"[POST] Error publishing post: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            f"❌ Произошла ошибка при публикации поста.\n\n"
            f"Ошибка: {str(e)}\n\n"
            f"Убедитесь, что:\n"
            f"• Бот является администратором канала\n"
            f"• У бота есть права на публикацию сообщений",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


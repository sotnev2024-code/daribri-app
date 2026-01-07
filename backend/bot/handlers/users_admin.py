"""
Обработчики управления пользователями и рассылки для администратора.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class BroadcastStates(StatesGroup):
    """Состояния для рассылки."""
    waiting_for_message = State()
    waiting_for_confirmation = State()


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    from backend.app.config import settings
    
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    from backend.app.config import settings
    import os
    admin_ids_str = os.getenv("ADMIN_IDS", "") or getattr(settings, "ADMIN_IDS", "")
    
    if admin_ids_str:
        try:
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
            return user_id in admin_ids
        except (ValueError, AttributeError):
            pass
    
    return True  # Временно разрешаем всем для разработки


async def show_users_menu(callback: CallbackQuery, bot: Bot):
    """Показывает меню управления пользователями."""
    try:
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
            return
        
        db = await get_db()
        
        # Получаем статистику пользователей
        total_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM users"
        )
        premium_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM users WHERE is_premium = 1"
        )
        
        await db.disconnect()
        
        menu_text = f"""
<b>👥 Управление пользователями</b>

<b>Статистика:</b>
👤 Всего пользователей: {total_count['cnt']}
⭐ Premium пользователей: {premium_count['cnt']}

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Создать рассылку", callback_data="admin_broadcast_create")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing users menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке меню пользователей.", show_alert=True)


@router.callback_query(F.data == "admin_users_menu")
async def callback_users_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки возврата в меню пользователей."""
    await show_users_menu(callback, bot)


@router.callback_query(F.data == "admin_broadcast_create")
async def start_broadcast(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начинает процесс создания рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    
    text = """
<b>📢 Создание рассылки</b>

Отправьте сообщение для рассылки:
• Только текст
• Текст с фотографией
• Только фотография

Сообщение будет отправлено всем пользователям бота.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_users_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.message(BroadcastStates.waiting_for_message, F.text | F.photo)
async def process_broadcast_message(message: Message, bot: Bot, state: FSMContext):
    """Обрабатывает сообщение для рассылки."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    # Сохраняем данные сообщения
    text = message.text or message.caption or ""
    photo_file_id = None
    
    if message.photo:
        # Берём фото наилучшего качества
        photo_file_id = message.photo[-1].file_id
    
    await state.update_data({
        "text": text,
        "photo_file_id": photo_file_id,
        "message_type": "photo" if photo_file_id else "text"
    })
    
    # Показываем превью
    await show_broadcast_preview(message, bot, state, text, photo_file_id)


async def show_broadcast_preview(message: Message, bot: Bot, state: FSMContext, text: str, photo_file_id: str = None):
    """Показывает превью рассылки."""
    db = await get_db()
    total_users = await db.fetch_one("SELECT COUNT(*) as cnt FROM users")
    await db.disconnect()
    
    preview_text = f"""
<b>📢 Превью рассылки</b>

<b>Получателей:</b> {total_users['cnt']} пользователей

<b>Содержание:</b>
{'-' * 30}
{text if text else '(только фото)'}
{'-' * 30}

Подтвердите отправку:
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="admin_broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="admin_broadcast_cancel")
        ]
    ])
    
    await state.set_state(BroadcastStates.waiting_for_confirmation)
    
    if photo_file_id:
        # Отправляем фото с подписью и превью
        await message.answer_photo(
            photo=photo_file_id,
            caption=preview_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(preview_text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_broadcast_confirm", BroadcastStates.waiting_for_confirmation)
async def confirm_broadcast(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждает и отправляет рассылку."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        await state.clear()
        return
    
    data = await state.get_data()
    text = data.get("text", "")
    photo_file_id = data.get("photo_file_id")
    
    await callback.message.edit_text("📤 Отправка рассылки...")
    await callback.answer()
    
    # Получаем всех пользователей
    db = await get_db()
    users = await db.fetch_all("SELECT telegram_id FROM users")
    await db.disconnect()
    
    total = len(users)
    sent = 0
    failed = 0
    
    for user in users:
        try:
            telegram_id = user["telegram_id"]
            
            if photo_file_id:
                # Отправляем фото с подписью
                if text:
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo_file_id,
                        caption=text
                    )
                else:
                    await bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo_file_id
                    )
            else:
                # Отправляем только текст
                if text:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=text
                    )
            
            sent += 1
        except Exception as e:
            print(f"Error sending to user {telegram_id}: {e}")
            failed += 1
    
    await state.clear()
    
    result_text = f"""
<b>✅ Рассылка завершена</b>

<b>Статистика:</b>
📤 Отправлено: {sent}
❌ Ошибок: {failed}
📊 Всего получателей: {total}
"""
    
    await callback.message.edit_text(result_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к пользователям", callback_data="admin_users_menu")]
    ]))


@router.callback_query(F.data == "admin_broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Отменяет рассылку."""
    await state.clear()
    
    try:
        await callback.message.edit_text("❌ Рассылка отменена.")
    except:
        await callback.message.answer("❌ Рассылка отменена.")
    
    await show_users_menu(callback, bot)
    await callback.answer()


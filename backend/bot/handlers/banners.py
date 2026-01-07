"""
Обработчики управления баннерами для администратора.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

router = Router()


class BannerCreateStates(StatesGroup):
    """Состояния для создания баннера."""
    waiting_for_title = State()
    waiting_for_description = State()


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


def get_cancel_keyboard():
    """Возвращает клавиатуру с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def show_banners_list(callback: CallbackQuery, bot: Bot):
    """Показывает список баннеров."""
    try:
        db = await get_db()
        
        banners = await db.fetch_all(
            "SELECT * FROM banners ORDER BY created_at DESC",
            ()
        )
        
        await db.disconnect()
        
        if not banners:
            text = "<b>🖼️ Баннеры</b>\n\nБаннеров не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать баннер", callback_data="admin_create_banner")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = "<b>🖼️ Баннеры</b>\n\n"
        keyboard_buttons = []
        
        for banner in banners:
            status_emoji = "✅" if banner.get("is_active") else "❌"
            text += f"{status_emoji} <b>#{banner['id']}</b>"
            if banner.get("title"):
                text += f" - {banner['title']}"
            text += f"\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{banner['id']} {'✅' if banner.get('is_active') else '❌'}",
                    callback_data=f"admin_view_banner_{banner['id']}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="➕ Создать баннер", callback_data="admin_create_banner")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing banners list: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке списка баннеров.", show_alert=True)


async def start_create_banner(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начинает процесс создания баннера."""
    await state.set_state(BannerCreateStates.waiting_for_title)
    await callback.message.edit_text(
        "<b>🖼️ Создание баннера</b>\n\nШаг 1/2: Введите заголовок баннера:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_banners")]
        ])
    )


@router.message(BannerCreateStates.waiting_for_title, F.text)
async def process_banner_title(message: Message, state: FSMContext):
    """Обрабатывает заголовок баннера."""
    title = message.text.strip()
    if not title:
        await message.answer("❌ Заголовок не может быть пустым. Попробуйте еще раз:")
        return
    
    await state.update_data(title=title)
    await state.set_state(BannerCreateStates.waiting_for_description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_banners")]
    ])
    await message.answer(
        "Шаг 2/2: Введите описание баннера:",
        reply_markup=keyboard
    )


@router.message(BannerCreateStates.waiting_for_description, F.text)
async def process_banner_description(message: Message, state: FSMContext):
    """Обрабатывает описание баннера."""
    description = message.text.strip()
    if not description:
        await message.answer("❌ Описание не может быть пустым. Попробуйте еще раз:")
        return
    
    await state.update_data(description=description)
    await finish_create_banner(message, state)


@router.message(F.text == "❌ Отменить")
async def cancel_banner_creation(message: Message, state: FSMContext):
    """Отменяет создание баннера."""
    current_state = await state.get_state()
    if current_state and "BannerCreateStates" in str(current_state):
        await state.clear()
        await message.answer(
            "❌ Создание баннера отменено.",
            reply_markup=ReplyKeyboardRemove()
        )




async def finish_create_banner(message: Message, state: FSMContext):
    """Завершает создание баннера."""
    try:
        data = await state.get_data()
        
        # Проверяем наличие обязательных полей
        if "title" not in data:
            await message.answer("❌ Ошибка: заголовок не найден. Попробуйте создать баннер заново.")
            await state.clear()
            return
        
        if "description" not in data:
            await message.answer("❌ Ошибка: описание не найдено. Попробуйте создать баннер заново.")
            await state.clear()
            return
        
        db = await get_db()
        
        # Форматируем дату для SQLite (используем isoformat как в других местах)
        now = datetime.now()
        
        banner_data = {
            "title": data["title"],
            "description": data["description"],
            "link_type": "none",
            "link_value": None,
            "display_order": 0,
            "is_active": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        print(f"[BANNER] Creating banner with data: {banner_data}")
        
        banner_id = await db.insert("banners", banner_data)
        await db.commit()
        await db.disconnect()
        
        await state.clear()
        await message.answer(
            f"✅ Баннер #{banner_id} успешно создан!",
            reply_markup=ReplyKeyboardRemove()
        )
        
    except Exception as e:
        print(f"Error creating banner: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            f"❌ Ошибка при создании баннера: {e}",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


async def delete_banner(callback: CallbackQuery, bot: Bot, banner_id: int):
    """Удаляет баннер."""
    try:
        db = await get_db()
        
        await db.delete("banners", "id = ?", (banner_id,))
        await db.commit()
        await db.disconnect()
        
        await callback.answer("✅ Баннер удален!", show_alert=True)
        await show_banners_list(callback, bot)
        
    except Exception as e:
        print(f"Error deleting banner: {e}")
        await callback.answer("❌ Ошибка при удалении баннера.", show_alert=True)


async def show_banner_details(callback: CallbackQuery, bot: Bot, banner_id: int):
    """Показывает детали баннера."""
    try:
        db = await get_db()
        
        banner = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
        await db.disconnect()
        
        if not banner:
            await callback.answer("❌ Баннер не найден.", show_alert=True)
            return
        
        status_emoji = "✅" if banner.get("is_active") else "❌"
        status_text = "Активен" if banner.get("is_active") else "Неактивен"
        
        text = f"""<b>🖼️ Баннер #{banner['id']}</b>

<b>Статус:</b> {status_emoji} {status_text}
<b>Заголовок:</b> {banner.get('title') or 'Не указан'}
<b>Описание:</b> {banner.get('description') or 'Не указано'}
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'❌ Деактивировать' if banner.get('is_active') else '✅ Активировать'}",
                    callback_data=f"admin_toggle_banner_{banner_id}"
                )
            ],
            [
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_delete_banner_{banner_id}")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="admin_banners")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing banner details: {e}")
        await callback.answer("❌ Ошибка при загрузке деталей баннера.", show_alert=True)


async def toggle_banner(callback: CallbackQuery, bot: Bot, banner_id: int):
    """Переключает активность баннера."""
    try:
        db = await get_db()
        
        banner = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
        if not banner:
            await callback.answer("❌ Баннер не найден.", show_alert=True)
            await db.disconnect()
            return
        
        new_status = 0 if banner.get("is_active") else 1
        await db.update("banners", {"is_active": new_status, "updated_at": datetime.now()}, "id = ?", (banner_id,))
        await db.commit()
        await db.disconnect()
        
        status_text = "активирован" if new_status else "деактивирован"
        await callback.answer(f"✅ Баннер {status_text}!", show_alert=True)
        await show_banners_list(callback, bot)
        
    except Exception as e:
        print(f"Error toggling banner: {e}")
        await callback.answer("❌ Ошибка при изменении статуса баннера.", show_alert=True)


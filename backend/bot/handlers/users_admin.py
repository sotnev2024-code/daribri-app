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
from decimal import Decimal
from backend.app.config import settings

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
            [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list")],
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


async def show_users_list(callback: CallbackQuery, bot: Bot, page: int = 0):
    """Показывает список пользователей с пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        limit = 10
        offset = page * limit
        
        users = await db.fetch_all(
            """SELECT u.*,
                      (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as orders_count,
                      (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE user_id = u.id) as total_spent
               FROM users u
               ORDER BY u.created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        
        await db.disconnect()
        
        # Преобразуем Decimal в float
        users_list = []
        for user in users:
            user_dict = dict(user)
            if user_dict.get("total_spent") is not None:
                if isinstance(user_dict["total_spent"], Decimal):
                    user_dict["total_spent"] = float(user_dict["total_spent"])
            users_list.append(user_dict)
        
        users = users_list
        
        if not users:
            text = "<b>👥 Пользователи</b>\n\nПользователей не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = "<b>👥 Пользователи</b>\n\n"
        keyboard_buttons = []
        
        for user in users:
            premium_emoji = "⭐" if user.get("is_premium") else ""
            text += f"{premium_emoji} <b>#{user['id']}</b> - {user.get('first_name', '')} {user.get('last_name', '')}\n"
            text += f"   @{user.get('username', 'не указан')}\n"
            text += f"   Заказов: {user.get('orders_count', 0)}, Потрачено: {user.get('total_spent', 0):.2f} ₽\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{user['id']} - {user.get('first_name', '')} {user.get('last_name', '')}",
                    callback_data=f"admin_user_view_{user['id']}"
                )
            ])
        
        # Пагинация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_users_list_{page-1}")
            )
        
        if len(users) == 10:  # Если получили полную страницу, есть еще пользователи
            nav_buttons.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_users_list_{page+1}")
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к меню", callback_data="admin_users_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing users list: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке списка пользователей.", show_alert=True)
        except:
            pass


async def show_user_details(callback: CallbackQuery, bot: Bot, user_id: int):
    """Показывает детали пользователя."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        
        if not user:
            await db.disconnect()
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Статистика пользователя
        orders_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM orders WHERE user_id = ?",
            (user_id,)
        )
        
        total_spent = await db.fetch_one(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE user_id = ?",
            (user_id,)
        )
        
        await db.disconnect()
        
        user_dict = dict(user)
        user_dict["orders_count"] = orders_count["cnt"] if orders_count else 0
        user_dict["total_spent"] = float(total_spent["total"]) if total_spent and isinstance(total_spent["total"], Decimal) else (total_spent["total"] if total_spent else 0)
        
        user = user_dict
        
        premium_emoji = "⭐" if user.get("is_premium") else ""
        blocked_emoji = "🚫" if not user.get("is_active", True) else ""
        
        text = f"""
<b>{premium_emoji} {blocked_emoji} Пользователь #{user_id}</b>

<b>Имя:</b> {user.get('first_name', 'Не указано')} {user.get('last_name', '')}
<b>Username:</b> @{user.get('username', 'не указан')}
<b>Telegram ID:</b> {user.get('telegram_id', 'не указан')}
<b>Premium:</b> {'Да' if user.get('is_premium') else 'Нет'}
<b>Статус:</b> {'Заблокирован' if not user.get('is_active', True) else 'Активен'}

<b>Статистика:</b>
📋 Заказов: {user.get('orders_count', 0)}
💰 Потрачено: {user.get('total_spent', 0):.2f} ₽
"""
        
        keyboard_buttons = []
        
        # Кнопка блокировки/разблокировки
        if user.get("is_active", True):
            keyboard_buttons.append([
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_user_block_{user_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin_user_unblock_{user_id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="📋 История заказов", callback_data=f"admin_user_orders_{user_id}")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_users_list_0")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing user details: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке пользователя.", show_alert=True)
        except:
            pass


async def toggle_user_status(callback: CallbackQuery, bot: Bot, user_id: int, block: bool):
    """Блокирует/разблокирует пользователя."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    db = None
    try:
        db = await get_db()
        
        # Проверяем существование пользователя
        user = await db.fetch_one("SELECT id FROM users WHERE id = ?", (user_id,))
        if not user:
            if db:
                await db.disconnect()
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Обновляем статус (используем is_active как индикатор блокировки)
        # Метод update уже вызывает commit() внутри, поэтому не нужно вызывать его снова
        try:
            result = await db.update(
                "users",
                {"is_active": 0 if block else 1},
                "id = ?",
                (user_id,)
            )
            print(f"[USERS_ADMIN] Updated user {user_id}: is_active = {0 if block else 1}, rows affected: {result}")
        except Exception as update_error:
            print(f"[USERS_ADMIN] Error updating user status: {update_error}")
            import traceback
            traceback.print_exc()
            if db:
                await db.disconnect()
            await callback.answer(f"❌ Ошибка при обновлении статуса: {str(update_error)}", show_alert=True)
            return
        
        if db:
            await db.disconnect()
        
        status_text = "заблокирован" if block else "разблокирован"
        await callback.answer(f"✅ Пользователь {status_text}", show_alert=True)
        
        # Обновляем детали пользователя
        await show_user_details(callback, bot, user_id)
        
    except Exception as e:
        print(f"[USERS_ADMIN] Error toggling user status: {e}")
        import traceback
        traceback.print_exc()
        if db:
            try:
                await db.disconnect()
            except:
                pass
        await callback.answer(f"❌ Ошибка при изменении статуса пользователя: {str(e)}", show_alert=True)


async def show_user_orders(callback: CallbackQuery, bot: Bot, user_id: int, page: int = 0):
    """Показывает историю заказов пользователя."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Проверяем существование пользователя
        user = await db.fetch_one("SELECT first_name, last_name FROM users WHERE id = ?", (user_id,))
        if not user:
            await db.disconnect()
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        limit = 10
        offset = page * limit
        
        orders = await db.fetch_all(
            """SELECT o.*, s.name as shop_name
               FROM orders o
               LEFT JOIN shops s ON o.shop_id = s.id
               WHERE o.user_id = ?
               ORDER BY o.created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset)
        )
        
        await db.disconnect()
        
        # Преобразуем Decimal в float
        orders_list = []
        for order in orders:
            order_dict = dict(order)
            if order_dict.get("total_amount") is not None:
                if isinstance(order_dict["total_amount"], Decimal):
                    order_dict["total_amount"] = float(order_dict["total_amount"])
            orders_list.append(order_dict)
        
        orders = orders_list
        
        if not orders:
            text = f"<b>📋 Заказы пользователя</b>\n\n"
            text += f"Пользователь: {user.get('first_name', '')} {user.get('last_name', '')}\n\n"
            text += "Заказов не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_view_{user_id}")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = f"<b>📋 Заказы пользователя</b>\n\n"
        text += f"Пользователь: {user.get('first_name', '')} {user.get('last_name', '')}\n\n"
        
        keyboard_buttons = []
        
        for order in orders:
            status_emoji = {
                "pending": "⏳",
                "confirmed": "✅",
                "processing": "🔄",
                "shipped": "📦",
                "delivered": "✓",
                "cancelled": "❌"
            }.get(order.get("status"), "📋")
            
            text += f"{status_emoji} <b>#{order['id']}</b> - {order.get('order_number', 'N/A')}\n"
            text += f"   Магазин: {order.get('shop_name', 'Неизвестно')}\n"
            text += f"   Сумма: {order.get('total_amount', 0):.2f} ₽\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{order['id']} - {order.get('order_number', 'N/A')}",
                    callback_data=f"admin_order_view_{order['id']}"
                )
            ])
        
        # Пагинация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_orders_{user_id}_{page-1}")
            )
        
        if len(orders) == 10:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_user_orders_{user_id}_{page+1}")
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_view_{user_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing user orders: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке заказов пользователя.", show_alert=True)
        except:
            pass


# Обработчики callback
@router.callback_query(F.data.startswith("admin_users_list"))
async def callback_users_list(callback: CallbackQuery, bot: Bot):
    """Обработчик списка пользователей."""
    parts = callback.data.split("_")
    page = int(parts[3]) if len(parts) > 3 else 0
    await show_users_list(callback, bot, page)


@router.callback_query(F.data.startswith("admin_user_view_"))
async def callback_user_view(callback: CallbackQuery, bot: Bot):
    """Обработчик просмотра пользователя."""
    user_id = int(callback.data.split("_")[3])
    await show_user_details(callback, bot, user_id)


@router.callback_query(F.data.startswith("admin_user_block_"))
async def callback_user_block(callback: CallbackQuery, bot: Bot):
    """Обработчик блокировки пользователя."""
    user_id = int(callback.data.split("_")[3])
    await toggle_user_status(callback, bot, user_id, True)


@router.callback_query(F.data.startswith("admin_user_unblock_"))
async def callback_user_unblock(callback: CallbackQuery, bot: Bot):
    """Обработчик разблокировки пользователя."""
    user_id = int(callback.data.split("_")[3])
    await toggle_user_status(callback, bot, user_id, False)


@router.callback_query(F.data.startswith("admin_user_orders_"))
async def callback_user_orders(callback: CallbackQuery, bot: Bot):
    """Обработчик заказов пользователя."""
    parts = callback.data.split("_")
    user_id = int(parts[3])
    page = int(parts[4]) if len(parts) > 4 else 0
    await show_user_orders(callback, bot, user_id, page)


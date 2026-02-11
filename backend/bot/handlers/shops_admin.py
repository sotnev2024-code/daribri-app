"""
Обработчики управления магазинами для администратора.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decimal import Decimal
import os
from backend.app.config import settings

router = Router()


class ShopEditStates(StatesGroup):
    """Состояния для редактирования магазина."""
    waiting_for_field = State()
    waiting_for_value = State()


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    admin_ids_str = os.getenv("ADMIN_IDS", "") or getattr(settings, "ADMIN_IDS", "")
    
    if admin_ids_str:
        try:
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
            return user_id in admin_ids
        except (ValueError, AttributeError):
            pass
    
    return True  # Временно разрешаем всем для разработки


async def show_shops_menu(callback: CallbackQuery, bot: Bot):
    """Показывает главное меню управления магазинами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Статистика магазинов
        total_shops = await db.fetch_one("SELECT COUNT(*) as cnt FROM shops")
        active_shops = await db.fetch_one("SELECT COUNT(*) as cnt FROM shops WHERE is_active = 1")
        verified_shops = await db.fetch_one("SELECT COUNT(*) as cnt FROM shops WHERE is_verified = 1")
        
        await db.disconnect()
        
        menu_text = f"""
<b>🏪 Управление магазинами</b>

<b>Статистика:</b>
📊 Всего магазинов: {total_shops['cnt']}
✅ Активных: {active_shops['cnt']}
⭐ Верифицированных: {verified_shops['cnt']}

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все магазины", callback_data="admin_shops_list_all")],
            [InlineKeyboardButton(text="✅ Активные", callback_data="admin_shops_list_active")],
            [InlineKeyboardButton(text="❌ Неактивные", callback_data="admin_shops_list_inactive")],
            [InlineKeyboardButton(text="⭐ Верифицированные", callback_data="admin_shops_list_verified")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing shops menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке меню магазинов.", show_alert=True)


async def show_shops_list(callback: CallbackQuery, bot: Bot, filter_type: str = "all", page: int = 0):
    """Показывает список магазинов с фильтрами и пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Определяем условия фильтрации
        conditions = []
        params = []
        
        if filter_type == "active":
            conditions.append("is_active = 1")
        elif filter_type == "inactive":
            conditions.append("is_active = 0")
        elif filter_type == "verified":
            conditions.append("is_verified = 1")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Получаем общее количество для пагинации
        total_count = await db.fetch_one(
            f"SELECT COUNT(*) as cnt FROM shops WHERE {where_clause}",
            tuple(params)
        )
        
        # Получаем магазины с пагинацией (по 10 на страницу)
        limit = 10
        offset = page * limit
        
        shops = await db.fetch_all(
            f"""SELECT s.*, 
                      (SELECT COUNT(*) FROM products WHERE shop_id = s.id) as products_count,
                      (SELECT COUNT(*) FROM orders WHERE shop_id = s.id) as orders_count
               FROM shops s
               WHERE {where_clause}
               ORDER BY s.created_at DESC
               LIMIT ? OFFSET ?""",
            tuple(params + [limit, offset])
        )
        
        await db.disconnect()
        
        filter_names = {
            "all": "Все магазины",
            "active": "Активные",
            "inactive": "Неактивные",
            "verified": "Верифицированные"
        }
        
        if not shops:
            text = f"<b>📋 {filter_names.get(filter_type, 'Магазины')}</b>\n\nМагазинов не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_shops_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = f"<b>📋 {filter_names.get(filter_type, 'Магазины')}</b>\n\n"
        keyboard_buttons = []
        
        for shop in shops:
            status_emoji = "✅" if shop.get("is_active", 0) else "❌"
            verified_emoji = "⭐" if shop.get("is_verified", 0) else ""
            
            text += f"{status_emoji} {verified_emoji} <b>#{shop['id']}</b> - {shop['name'][:30]}\n"
            text += f"   Товаров: {shop.get('products_count', 0)}, Заказов: {shop.get('orders_count', 0)}\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{shop['id']} - {shop['name'][:25]}",
                    callback_data=f"admin_shop_view_{shop['id']}"
                )
            ])
        
        # Пагинация
        total_pages = (total_count['cnt'] + limit - 1) // limit if total_count['cnt'] > 0 else 1
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_shops_list_{filter_type}_{page-1}")
            )
        
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_shops_list_{filter_type}_{page+1}")
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к меню", callback_data="admin_shops_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing shops list: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке списка магазинов.", show_alert=True)


async def show_shop_details(callback: CallbackQuery, bot: Bot, shop_id: int):
    """Показывает детали магазина."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        # Используем прямой доступ к базе данных
        db = await get_db()
        
        # Получаем данные магазина
        shop = await db.fetch_one(
            """SELECT s.*, 
                      u.telegram_id as owner_telegram_id,
                      u.username as owner_username,
                      u.first_name as owner_first_name,
                      u.last_name as owner_last_name
               FROM shops s
               LEFT JOIN users u ON s.owner_id = u.id
               WHERE s.id = ?""",
            (shop_id,)
        )
        
        if not shop:
            await db.disconnect()
            await callback.answer("❌ Магазин не найден", show_alert=True)
            return
        
        # Получаем статистику
        products_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ?",
            (shop_id,)
        )
        active_products_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ? AND is_active = 1",
            (shop_id,)
        )
        orders_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM orders WHERE shop_id = ?",
            (shop_id,)
        )
        total_revenue = await db.fetch_one(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE shop_id = ?",
            (shop_id,)
        )
        avg_order = await db.fetch_one(
            "SELECT COALESCE(AVG(total_amount), 0) as avg FROM orders WHERE shop_id = ?",
            (shop_id,)
        )
        
        # Получаем информацию о текущей подписке
        subscription = await db.fetch_one(
            """SELECT ss.*, sp.name as plan_name, sp.duration_days, sp.price as plan_price
               FROM shop_subscriptions ss
               JOIN subscription_plans sp ON ss.plan_id = sp.id
               WHERE ss.shop_id = ? AND ss.is_active = 1 AND ss.end_date > datetime('now')
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        await db.disconnect()
        
        stats = {
            "products_count": products_count["cnt"] if products_count else 0,
            "active_products_count": active_products_count["cnt"] if active_products_count else 0,
            "orders_count": orders_count["cnt"] if orders_count else 0,
            "total_revenue": float(total_revenue["total"]) if total_revenue and isinstance(total_revenue["total"], Decimal) else (total_revenue["total"] if total_revenue else 0),
            "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0)
        }
        
        status_emoji = "✅" if shop.get("is_active") else "❌"
        verified_emoji = "⭐" if shop.get("is_verified") else ""
        
        # Преобразуем Decimal в float для отображения
        avg_rating = shop.get('average_rating')
        if avg_rating is not None:
            if isinstance(avg_rating, Decimal):
                avg_rating = float(avg_rating)
            elif isinstance(avg_rating, str):
                try:
                    avg_rating = float(avg_rating)
                except:
                    avg_rating = 0
        else:
            avg_rating = 0
        
        text = f"""
<b>{status_emoji} {verified_emoji} Магазин #{shop_id}</b>

<b>Название:</b> {shop.get('name', 'Не указано')}
<b>Описание:</b> {shop.get('description', 'Не указано')[:100] or 'Не указано'}
<b>Адрес:</b> {shop.get('address', 'Не указано')}
<b>Телефон:</b> {shop.get('phone', 'Не указано')}
<b>Email:</b> {shop.get('email', 'Не указано')}

<b>Владелец:</b>
👤 Telegram: @{shop.get('owner_username', 'не указан')}
ID: {shop.get('owner_telegram_id', 'не указан')}

<b>Статистика:</b>
📦 Товаров: {stats.get('products_count', 0)}
📋 Заказов: {stats.get('orders_count', 0)}
💰 Выручка: {stats.get('total_revenue', 0):.2f} ₽
📊 Средний чек: {stats.get('average_order', 0):.2f} ₽

<b>Рейтинг:</b> {avg_rating:.1f} ⭐ ({shop.get('total_reviews', 0)} отзывов)

<b>Подписка:</b>
"""
        
        # Добавляем информацию о подписке
        if subscription:
            from datetime import datetime
            end_date = datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
            days_remaining = max(0, (end_date - datetime.now(end_date.tzinfo)).days)
            subscription_status = "✅ Активна" if days_remaining > 0 else "❌ Истекла"
            text += f"{subscription_status}\n"
            text += f"📋 План: {subscription.get('plan_name', 'Не указан')}\n"
            text += f"📅 Осталось дней: {days_remaining}\n"
            text += f"📆 До: {end_date.strftime('%d.%m.%Y')}\n"
        else:
            text += "❌ Нет активной подписки\n"
        
        text += "\n"
        
        keyboard_buttons = []
        
        # Кнопки управления статусом
        if shop.get("is_active"):
            keyboard_buttons.append([
                InlineKeyboardButton(text="❌ Заблокировать", callback_data=f"admin_shop_toggle_{shop_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Активировать", callback_data=f"admin_shop_toggle_{shop_id}")
            ])
        
        # Кнопка верификации
        if not shop.get("is_verified"):
            keyboard_buttons.append([
                InlineKeyboardButton(text="⭐ Верифицировать", callback_data=f"admin_shop_verify_{shop_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="❌ Снять верификацию", callback_data=f"admin_shop_unverify_{shop_id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_shop_edit_{shop_id}"),
            InlineKeyboardButton(text="📊 Статистика", callback_data=f"admin_shop_stats_{shop_id}")
        ])
        
        # Кнопки управления подпиской
        keyboard_buttons.append([
            InlineKeyboardButton(text="💳 Продлить подписку", callback_data=f"admin_shop_extend_subscription_{shop_id}"),
            InlineKeyboardButton(text="🔄 Поменять тариф", callback_data=f"admin_shop_change_plan_{shop_id}")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_shops_list_all_0")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing shop details: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке магазина.", show_alert=True)
        except:
            pass


async def toggle_shop_status(callback: CallbackQuery, bot: Bot, shop_id: int):
    """Блокирует/разблокирует магазин."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Получаем текущий статус
        shop = await db.fetch_one("SELECT is_active FROM shops WHERE id = ?", (shop_id,))
        
        if not shop:
            await db.disconnect()
            await callback.answer("❌ Магазин не найден", show_alert=True)
            return
        
        new_status = not shop.get("is_active", False)
        
        # Обновляем статус
        await db.update(
            "shops",
            {"is_active": 1 if new_status else 0},
            "id = ?",
            (shop_id,)
        )
        await db.commit()
        await db.disconnect()
        
        status_text = "активирован" if new_status else "заблокирован"
        await callback.answer(f"✅ Магазин {status_text}", show_alert=True)
        
        # Обновляем детали магазина
        await show_shop_details(callback, bot, shop_id)
        
    except Exception as e:
        print(f"Error toggling shop status: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при изменении статуса магазина.", show_alert=True)


async def toggle_shop_verification(callback: CallbackQuery, bot: Bot, shop_id: int, verify: bool):
    """Верифицирует/снимает верификацию магазина."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Проверяем существование магазина
        shop = await db.fetch_one("SELECT id FROM shops WHERE id = ?", (shop_id,))
        if not shop:
            await db.disconnect()
            await callback.answer("❌ Магазин не найден", show_alert=True)
            return
        
        # Обновляем верификацию
        await db.update(
            "shops",
            {"is_verified": 1 if verify else 0},
            "id = ?",
            (shop_id,)
        )
        await db.commit()
        await db.disconnect()
        
        status_text = "верифицирован" if verify else "верификация снята"
        await callback.answer(f"✅ Магазин {status_text}", show_alert=True)
        
        # Обновляем детали магазина
        await show_shop_details(callback, bot, shop_id)
        
    except Exception as e:
        print(f"Error toggling shop verification: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при изменении верификации магазина.", show_alert=True)


async def show_shop_statistics(callback: CallbackQuery, bot: Bot, shop_id: int):
    """Показывает статистику магазина."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Проверяем существование магазина
        shop = await db.fetch_one("SELECT name FROM shops WHERE id = ?", (shop_id,))
        if not shop:
            await db.disconnect()
            await callback.answer("❌ Магазин не найден", show_alert=True)
            return
        
        # Получаем статистику
        products_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ?",
            (shop_id,)
        )
        active_products_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ? AND is_active = 1",
            (shop_id,)
        )
        orders_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM orders WHERE shop_id = ?",
            (shop_id,)
        )
        total_revenue = await db.fetch_one(
            "SELECT COALESCE(SUM(total_amount), 0) as total FROM orders WHERE shop_id = ?",
            (shop_id,)
        )
        avg_order = await db.fetch_one(
            "SELECT COALESCE(AVG(total_amount), 0) as avg FROM orders WHERE shop_id = ?",
            (shop_id,)
        )
        orders_by_status = await db.fetch_all(
            """SELECT status, COUNT(*) as cnt 
               FROM orders 
               WHERE shop_id = ? 
               GROUP BY status""",
            (shop_id,)
        )
        
        await db.disconnect()
        
        stats = {
            "products_count": products_count["cnt"] if products_count else 0,
            "active_products_count": active_products_count["cnt"] if active_products_count else 0,
            "orders_count": orders_count["cnt"] if orders_count else 0,
            "total_revenue": float(total_revenue["total"]) if total_revenue and isinstance(total_revenue["total"], Decimal) else (total_revenue["total"] if total_revenue else 0),
            "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0),
            "orders_by_status": {row["status"]: row["cnt"] for row in orders_by_status}
        }
        
        text = f"""
<b>📊 Статистика магазина</b>

<b>Магазин:</b> {shop.get('name', f'#{shop_id}')}

<b>Товары:</b>
📦 Всего товаров: {stats.get('products_count', 0)}
✅ Активных: {stats.get('active_products_count', 0)}

<b>Заказы:</b>
📋 Всего заказов: {stats.get('orders_count', 0)}
💰 Общая выручка: {stats.get('total_revenue', 0):.2f} ₽
📊 Средний чек: {stats.get('average_order', 0):.2f} ₽

<b>Заказы по статусам:</b>
"""
        
        orders_by_status = stats.get('orders_by_status', {})
        for status, count in orders_by_status.items():
            status_emoji = {
                "pending": "⏳",
                "confirmed": "✅",
                "processing": "🔄",
                "shipped": "📦",
                "delivered": "✓",
                "cancelled": "❌"
            }.get(status, "📋")
            text += f"{status_emoji} {status}: {count}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_shop_view_{shop_id}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing shop statistics: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке статистики.", show_alert=True)


# Обработчики callback
@router.callback_query(F.data == "admin_shops_menu")
async def callback_shops_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки меню магазинов."""
    await show_shops_menu(callback, bot)


@router.callback_query(F.data.startswith("admin_shops_list_"))
async def callback_shops_list(callback: CallbackQuery, bot: Bot):
    """Обработчик списка магазинов."""
    parts = callback.data.split("_")
    filter_type = parts[3] if len(parts) > 3 else "all"
    page = int(parts[4]) if len(parts) > 4 else 0
    await show_shops_list(callback, bot, filter_type, page)


@router.callback_query(F.data.startswith("admin_shop_view_"))
async def callback_shop_view(callback: CallbackQuery, bot: Bot):
    """Обработчик просмотра магазина."""
    shop_id = int(callback.data.split("_")[3])
    await show_shop_details(callback, bot, shop_id)


@router.callback_query(F.data.startswith("admin_shop_toggle_"))
async def callback_shop_toggle(callback: CallbackQuery, bot: Bot):
    """Обработчик блокировки/разблокировки магазина."""
    shop_id = int(callback.data.split("_")[3])
    await toggle_shop_status(callback, bot, shop_id)


@router.callback_query(F.data.startswith("admin_shop_verify_"))
async def callback_shop_verify(callback: CallbackQuery, bot: Bot):
    """Обработчик верификации магазина."""
    shop_id = int(callback.data.split("_")[3])
    await toggle_shop_verification(callback, bot, shop_id, True)


@router.callback_query(F.data.startswith("admin_shop_unverify_"))
async def callback_shop_unverify(callback: CallbackQuery, bot: Bot):
    """Обработчик снятия верификации магазина."""
    shop_id = int(callback.data.split("_")[3])
    await toggle_shop_verification(callback, bot, shop_id, False)


@router.callback_query(F.data.startswith("admin_shop_stats_"))
async def callback_shop_stats(callback: CallbackQuery, bot: Bot):
    """Обработчик статистики магазина."""
    shop_id = int(callback.data.split("_")[3])
    await show_shop_statistics(callback, bot, shop_id)


async def start_edit_shop(callback: CallbackQuery, bot: Bot, shop_id: int, state: FSMContext):
    """Начинает процесс редактирования магазина."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        shop = await db.fetch_one("SELECT * FROM shops WHERE id = ?", (shop_id,))
        if not shop:
            await db.disconnect()
            await callback.answer("❌ Магазин не найден", show_alert=True)
            return
        
        await db.disconnect()
        
        text = f"""
<b>✏️ Редактирование магазина</b>

<b>Магазин:</b> {shop.get('name', 'N/A')}

Выберите поле для редактирования:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Название", callback_data=f"admin_shop_edit_field_{shop_id}_name")],
            [InlineKeyboardButton(text="📄 Описание", callback_data=f"admin_shop_edit_field_{shop_id}_description")],
            [InlineKeyboardButton(text="📍 Адрес", callback_data=f"admin_shop_edit_field_{shop_id}_address")],
            [InlineKeyboardButton(text="📞 Телефон", callback_data=f"admin_shop_edit_field_{shop_id}_phone")],
            [InlineKeyboardButton(text="📧 Email", callback_data=f"admin_shop_edit_field_{shop_id}_email")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_shop_view_{shop_id}")]
        ])
        
        await state.update_data(shop_id=shop_id)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error starting shop edit: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке магазина.", show_alert=True)


async def process_edit_shop_field(callback: CallbackQuery, bot: Bot, shop_id: int, field: str, state: FSMContext):
    """Обрабатывает выбор поля для редактирования."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    field_names = {
        "name": "название",
        "description": "описание",
        "address": "адрес",
        "phone": "телефон",
        "email": "email"
    }
    
    field_name = field_names.get(field, field)
    
    await state.update_data(edit_field=field)
    await state.set_state(ShopEditStates.waiting_for_value)
    
    text = f"""
<b>✏️ Редактирование магазина</b>

Введите новое значение для поля <b>"{field_name}"</b>:

Для отмены нажмите кнопку "❌ Отменить"
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_shop_view_{shop_id}")]
    ])
    
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=cancel_keyboard)
    await callback.answer()


async def process_edit_shop_value(message: Message, bot: Bot, state: FSMContext):
    """Обрабатывает новое значение поля магазина."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    try:
        data = await state.get_data()
        shop_id = data.get("shop_id")
        field = data.get("edit_field")
        
        if not shop_id or not field:
            await message.answer("❌ Ошибка: не указан магазин или поле.")
            await state.clear()
            return
        
        new_value = message.text.strip()
        
        # Проверяем отмену
        if new_value.lower() in ["❌ отменить", "отменить", "отмена", "cancel"]:
            await state.clear()
            await message.answer("❌ Редактирование отменено.", reply_markup=ReplyKeyboardRemove())
            return
        
        db = await get_db()
        
        # Обновляем поле
        await db.update(
            "shops",
            {field: new_value},
            "id = ?",
            (shop_id,)
        )
        await db.commit()
        await db.disconnect()
        
        await state.clear()
        
        field_names = {
            "name": "Название",
            "description": "Описание",
            "address": "Адрес",
            "phone": "Телефон",
            "email": "Email"
        }
        
        field_name = field_names.get(field, field)
        
        await message.answer(
            f"✅ {field_name} магазина успешно обновлено!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Показываем обновленные детали магазина через inline кнопку
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Просмотреть магазин", callback_data=f"admin_shop_view_{shop_id}")]
        ])
        await message.answer("Нажмите кнопку ниже, чтобы просмотреть обновленные данные магазина:", reply_markup=keyboard)
        
    except Exception as e:
        print(f"Error processing shop edit value: {e}")
        import traceback
        traceback.print_exc()
        await state.clear()
        await message.answer("❌ Ошибка при обновлении магазина.", reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data.startswith("admin_shop_edit_"))
async def callback_shop_edit(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обработчик редактирования магазина."""
    try:
        parts = callback.data.split("_")
        print(f"[SHOPS_ADMIN] Callback data: {callback.data}, parts: {parts}")
        
        if len(parts) >= 5 and parts[3] == "field":
            # Формат: admin_shop_edit_field_{shop_id}_{field}
            shop_id = int(parts[4])
            field = parts[5]
            print(f"[SHOPS_ADMIN] Edit field: shop_id={shop_id}, field={field}")
            await process_edit_shop_field(callback, bot, shop_id, field, state)
        else:
            # Формат: admin_shop_edit_{shop_id}
            shop_id = int(parts[3])
            print(f"[SHOPS_ADMIN] Start edit: shop_id={shop_id}")
            await start_edit_shop(callback, bot, shop_id, state)
    except Exception as e:
        print(f"[SHOPS_ADMIN] Error in callback_shop_edit: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при обработке редактирования.", show_alert=True)


@router.message(ShopEditStates.waiting_for_value)
async def handle_shop_edit_value(message: Message, bot: Bot, state: FSMContext):
    """Обработчик ввода нового значения для редактирования магазина."""
    await process_edit_shop_value(message, bot, state)


async def show_extend_subscription_menu(callback: CallbackQuery, bot: Bot, shop_id: int):
    """Показывает меню для продления подписки (выбор количества дней)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Получаем текущую подписку
        subscription = await db.fetch_one(
            """SELECT ss.*, sp.name as plan_name, sp.duration_days
               FROM shop_subscriptions ss
               JOIN subscription_plans sp ON ss.plan_id = sp.id
               WHERE ss.shop_id = ? AND ss.is_active = 1
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        if not subscription:
            await db.disconnect()
            await callback.answer("❌ У магазина нет активной подписки. Используйте 'Поменять тариф' для создания новой.", show_alert=True)
            return
        
        await db.disconnect()
        
        text = f"""
<b>💳 Продление подписки</b>

<b>Магазин:</b> #{shop_id}
<b>Текущий план:</b> {subscription.get('plan_name', 'Не указан')}

Выберите количество дней для продления:
"""
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="➕ 7 дней", callback_data=f"admin_shop_extend_days_{shop_id}_7")],
            [InlineKeyboardButton(text="➕ 14 дней", callback_data=f"admin_shop_extend_days_{shop_id}_14")],
            [InlineKeyboardButton(text="➕ 30 дней", callback_data=f"admin_shop_extend_days_{shop_id}_30")],
            [InlineKeyboardButton(text="➕ 60 дней", callback_data=f"admin_shop_extend_days_{shop_id}_60")],
            [InlineKeyboardButton(text="➕ 90 дней", callback_data=f"admin_shop_extend_days_{shop_id}_90")],
            [InlineKeyboardButton(text="➕ 180 дней", callback_data=f"admin_shop_extend_days_{shop_id}_180")],
            [InlineKeyboardButton(text="➕ 365 дней", callback_data=f"admin_shop_extend_days_{shop_id}_365")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_shop_view_{shop_id}")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing extend subscription menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке меню продления.", show_alert=True)


async def extend_subscription(callback: CallbackQuery, bot: Bot, shop_id: int, days: int):
    """Продлевает подписку на указанное количество дней."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from datetime import datetime, timedelta
        
        db = await get_db()
        
        # Получаем текущую подписку
        subscription = await db.fetch_one(
            """SELECT ss.*, sp.name as plan_name
               FROM shop_subscriptions ss
               JOIN subscription_plans sp ON ss.plan_id = sp.id
               WHERE ss.shop_id = ? AND ss.is_active = 1
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        if not subscription:
            await db.disconnect()
            await callback.answer("❌ У магазина нет активной подписки.", show_alert=True)
            return
        
        # Вычисляем новую дату окончания
        current_end_date = datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
        new_end_date = current_end_date + timedelta(days=days)
        
        # Обновляем подписку
        await db.update(
            "shop_subscriptions",
            {"end_date": new_end_date.isoformat()},
            "id = ?",
            (subscription["id"],)
        )
        await db.commit()
        await db.disconnect()
        
        await callback.answer(f"✅ Подписка продлена на {days} дней", show_alert=True)
        
        # Обновляем детали магазина
        await show_shop_details(callback, bot, shop_id)
        
    except Exception as e:
        print(f"Error extending subscription: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при продлении подписки.", show_alert=True)


async def show_change_plan_menu(callback: CallbackQuery, bot: Bot, shop_id: int):
    """Показывает меню для смены тарифа (выбор нового плана)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Получаем все активные планы
        plans = await db.fetch_all(
            "SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY price"
        )
        
        if not plans:
            await db.disconnect()
            await callback.answer("❌ Нет доступных планов подписки.", show_alert=True)
            return
        
        # Получаем текущую подписку
        current_subscription = await db.fetch_one(
            """SELECT ss.*, sp.name as plan_name, sp.id as plan_id
               FROM shop_subscriptions ss
               JOIN subscription_plans sp ON ss.plan_id = sp.id
               WHERE ss.shop_id = ? AND ss.is_active = 1
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        await db.disconnect()
        
        current_plan_id = current_subscription.get("plan_id") if current_subscription else None
        
        text = f"""
<b>🔄 Смена тарифа</b>

<b>Магазин:</b> #{shop_id}
"""
        
        if current_subscription:
            text += f"<b>Текущий план:</b> {current_subscription.get('plan_name', 'Не указан')}\n\n"
        
        text += "Выберите новый план подписки:\n"
        
        keyboard_buttons = []
        
        for plan in plans:
            price = Decimal(str(plan.get("price", 0)))
            duration = plan.get("duration_days", 0)
            max_products = plan.get("max_products", 0)
            
            plan_text = f"{plan.get('name', 'Без названия')} - {price:.2f} ₽"
            if plan.get("id") == current_plan_id:
                plan_text = f"✅ {plan_text} (текущий)"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=plan_text,
                    callback_data=f"admin_shop_set_plan_{shop_id}_{plan['id']}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_shop_view_{shop_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing change plan menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке планов.", show_alert=True)


async def change_subscription_plan(callback: CallbackQuery, bot: Bot, shop_id: int, plan_id: int):
    """Меняет тариф подписки на новый план."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from datetime import datetime, timedelta
        
        db = await get_db()
        
        # Проверяем существование плана
        plan = await db.fetch_one(
            "SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1",
            (plan_id,)
        )
        
        if not plan:
            await db.disconnect()
            await callback.answer("❌ План не найден.", show_alert=True)
            return
        
        # Получаем текущую подписку
        current_subscription = await db.fetch_one(
            """SELECT ss.*
               FROM shop_subscriptions ss
               WHERE ss.shop_id = ? AND ss.is_active = 1
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        # Деактивируем старые подписки
        await db.update(
            "shop_subscriptions",
            {"is_active": False},
            "shop_id = ?",
            (shop_id,)
        )
        
        # Создаём новую подписку
        start_date = datetime.now()
        end_date = start_date + timedelta(days=plan["duration_days"])
        
        subscription_id = await db.insert("shop_subscriptions", {
            "shop_id": shop_id,
            "plan_id": plan_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "is_active": True,
            "payment_id": f"admin_manual_{datetime.now().timestamp()}"  # Метка админского изменения
        })
        
        await db.commit()
        await db.disconnect()
        
        await callback.answer(f"✅ Тариф изменён на '{plan.get('name', 'N/A')}'", show_alert=True)
        
        # Обновляем детали магазина
        await show_shop_details(callback, bot, shop_id)
        
    except Exception as e:
        print(f"Error changing subscription plan: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при смене тарифа.", show_alert=True)


# Обработчики callback для управления подпиской
@router.callback_query(F.data.startswith("admin_shop_extend_subscription_"))
async def callback_extend_subscription_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки продления подписки."""
    shop_id = int(callback.data.split("_")[4])
    await show_extend_subscription_menu(callback, bot, shop_id)


@router.callback_query(F.data.startswith("admin_shop_extend_days_"))
async def callback_extend_subscription(callback: CallbackQuery, bot: Bot):
    """Обработчик продления подписки на указанное количество дней."""
    parts = callback.data.split("_")
    shop_id = int(parts[4])
    days = int(parts[5])
    await extend_subscription(callback, bot, shop_id, days)


@router.callback_query(F.data.startswith("admin_shop_change_plan_"))
async def callback_change_plan_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки смены тарифа."""
    shop_id = int(callback.data.split("_")[4])
    await show_change_plan_menu(callback, bot, shop_id)


@router.callback_query(F.data.startswith("admin_shop_set_plan_"))
async def callback_change_plan(callback: CallbackQuery, bot: Bot):
    """Обработчик смены тарифа на новый план."""
    parts = callback.data.split("_")
    shop_id = int(parts[4])
    plan_id = int(parts[5])
    await change_subscription_plan(callback, bot, shop_id, plan_id)


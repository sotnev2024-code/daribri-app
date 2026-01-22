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
import httpx
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
        # Используем API для получения данных
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            
            if response.status_code == 404:
                await callback.answer("❌ Магазин не найден", show_alert=True)
                return
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")
            
            shop = response.json()
        
        # Получаем статистику
        async with httpx.AsyncClient() as client:
            stats_response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}/statistics",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            stats = stats_response.json() if stats_response.status_code == 200 else {}
        
        status_emoji = "✅" if shop.get("is_active") else "❌"
        verified_emoji = "⭐" if shop.get("is_verified") else ""
        
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

<b>Рейтинг:</b> {shop.get('average_rating', 0) or 0:.1f} ⭐ ({shop.get('total_reviews', 0)} отзывов)
"""
        
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
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_shops_list_all_0")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing shop details: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке магазина.", show_alert=True)


async def toggle_shop_status(callback: CallbackQuery, bot: Bot, shop_id: int):
    """Блокирует/разблокирует магазин."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        # Получаем текущий статус
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            
            if response.status_code != 200:
                await callback.answer("❌ Магазин не найден", show_alert=True)
                return
            
            shop = response.json()
            new_status = not shop.get("is_active", False)
        
        # Обновляем статус
        async with httpx.AsyncClient() as client:
            update_response = await client.patch(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)},
                json={"is_active": new_status}
            )
            
            if update_response.status_code != 200:
                raise Exception(f"Update failed: {update_response.status_code}")
        
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
        # Обновляем верификацию
        async with httpx.AsyncClient() as client:
            update_response = await client.patch(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)},
                json={"is_verified": verify}
            )
            
            if update_response.status_code != 200:
                raise Exception(f"Update failed: {update_response.status_code}")
        
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}/statistics",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            
            if response.status_code != 200:
                await callback.answer("❌ Статистика не найдена", show_alert=True)
                return
            
            stats = response.json()
        
        # Получаем информацию о магазине
        async with httpx.AsyncClient() as client:
            shop_response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/shops/{shop_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            shop = shop_response.json() if shop_response.status_code == 200 else {}
        
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


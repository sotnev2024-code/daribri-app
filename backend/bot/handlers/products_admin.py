"""
Обработчики управления товарами для администратора.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
import httpx
import os
from backend.app.config import settings

router = Router()


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


async def show_products_menu(callback: CallbackQuery, bot: Bot):
    """Показывает главное меню управления товарами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Статистика товаров
        total_products = await db.fetch_one("SELECT COUNT(*) as cnt FROM products")
        active_products = await db.fetch_one("SELECT COUNT(*) as cnt FROM products WHERE is_active = 1")
        
        await db.disconnect()
        
        menu_text = f"""
<b>📦 Управление товарами</b>

<b>Статистика:</b>
📊 Всего товаров: {total_products['cnt']}
✅ Активных: {active_products['cnt']}

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все товары", callback_data="admin_products_list_all")],
            [InlineKeyboardButton(text="✅ Активные", callback_data="admin_products_list_active")],
            [InlineKeyboardButton(text="❌ Неактивные", callback_data="admin_products_list_inactive")],
            [InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_products_search")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing products menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке меню товаров.", show_alert=True)


async def show_products_list(callback: CallbackQuery, bot: Bot, filter_type: str = "all", page: int = 0, shop_id: int = None):
    """Показывает список товаров с фильтрами и пагинацией."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        # Используем API для получения данных
        params = {
            "skip": page * 10,
            "limit": 10
        }
        
        if filter_type == "active":
            params["is_active"] = True
        elif filter_type == "inactive":
            params["is_active"] = False
        
        if shop_id:
            params["shop_id"] = shop_id
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/products",
                headers={"X-Telegram-ID": str(callback.from_user.id)},
                params=params
            )
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")
            
            products = response.json()
        
        filter_names = {
            "all": "Все товары",
            "active": "Активные",
            "inactive": "Неактивные"
        }
        
        if not products:
            text = f"<b>📦 {filter_names.get(filter_type, 'Товары')}</b>\n\nТоваров не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_products_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = f"<b>📦 {filter_names.get(filter_type, 'Товары')}</b>\n\n"
        keyboard_buttons = []
        
        for product in products:
            status_emoji = "✅" if product.get("is_active") else "❌"
            price = product.get("price", 0)
            discount_price = product.get("discount_price")
            
            price_text = f"{discount_price:.2f} ₽" if discount_price else f"{price:.2f} ₽"
            if discount_price:
                price_text += f" (было {price:.2f} ₽)"
            
            text += f"{status_emoji} <b>#{product['id']}</b> - {product['name'][:30]}\n"
            text += f"   Магазин: {product.get('shop_name', 'Неизвестно')}\n"
            text += f"   Цена: {price_text}\n"
            text += f"   Остаток: {product.get('quantity', 0)}\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{product['id']} - {product['name'][:25]}",
                    callback_data=f"admin_product_view_{product['id']}"
                )
            ])
        
        # Пагинация
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_products_list_{filter_type}_{page-1}")
            )
        
        if len(products) == 10:  # Если получили полную страницу, есть еще товары
            nav_buttons.append(
                InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_products_list_{filter_type}_{page+1}")
            )
        
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к меню", callback_data="admin_products_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing products list: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке списка товаров.", show_alert=True)


async def show_product_details(callback: CallbackQuery, bot: Bot, product_id: int):
    """Показывает детали товара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/products/{product_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            
            if response.status_code == 404:
                await callback.answer("❌ Товар не найден", show_alert=True)
                return
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code}")
            
            product = response.json()
        
        status_emoji = "✅" if product.get("is_active") else "❌"
        price = product.get("price", 0)
        discount_price = product.get("discount_price")
        
        price_text = f"{discount_price:.2f} ₽" if discount_price else f"{price:.2f} ₽"
        if discount_price:
            price_text += f" (было {price:.2f} ₽)"
        
        text = f"""
<b>{status_emoji} Товар #{product_id}</b>

<b>Название:</b> {product.get('name', 'Не указано')}
<b>Описание:</b> {product.get('description', 'Не указано')[:200] or 'Не указано'}
<b>Цена:</b> {price_text}
<b>Остаток:</b> {product.get('quantity', 0)}
<b>Категория:</b> {product.get('category_name', 'Не указана')}

<b>Магазин:</b> {product.get('shop_name', 'Неизвестно')} (ID: {product.get('shop_id', 'N/A')})

<b>Статус:</b> {'Активен' if product.get('is_active') else 'Неактивен'}
"""
        
        keyboard_buttons = []
        
        # Кнопки управления статусом
        if product.get("is_active"):
            keyboard_buttons.append([
                InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"admin_product_toggle_{product_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Активировать", callback_data=f"admin_product_toggle_{product_id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_product_delete_{product_id}")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_products_list_all_0")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing product details: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке товара.", show_alert=True)


async def toggle_product_status(callback: CallbackQuery, bot: Bot, product_id: int):
    """Активирует/деактивирует товар."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        # Получаем текущий статус
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEBAPP_URL}/api/admin/products/{product_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            
            if response.status_code != 200:
                await callback.answer("❌ Товар не найден", show_alert=True)
                return
            
            product = response.json()
            new_status = not product.get("is_active", False)
        
        # Обновляем статус
        async with httpx.AsyncClient() as client:
            update_response = await client.patch(
                f"{settings.WEBAPP_URL}/api/admin/products/{product_id}/status",
                headers={"X-Telegram-ID": str(callback.from_user.id)},
                params={"is_active": new_status}
            )
            
            if update_response.status_code != 200:
                raise Exception(f"Update failed: {update_response.status_code}")
        
        status_text = "активирован" if new_status else "деактивирован"
        await callback.answer(f"✅ Товар {status_text}", show_alert=True)
        
        # Обновляем детали товара
        await show_product_details(callback, bot, product_id)
        
    except Exception as e:
        print(f"Error toggling product status: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при изменении статуса товара.", show_alert=True)


async def delete_product(callback: CallbackQuery, bot: Bot, product_id: int):
    """Удаляет товар."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.WEBAPP_URL}/api/admin/products/{product_id}",
                headers={"X-Telegram-ID": str(callback.from_user.id)}
            )
            
            if response.status_code == 404:
                await callback.answer("❌ Товар не найден", show_alert=True)
                return
            
            if response.status_code != 200:
                raise Exception(f"Delete failed: {response.status_code}")
        
        await callback.answer("✅ Товар удален", show_alert=True)
        
        # Возвращаемся к списку товаров
        await show_products_list(callback, bot, "all", 0)
        
    except Exception as e:
        print(f"Error deleting product: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при удалении товара.", show_alert=True)


# Обработчики callback
@router.callback_query(F.data == "admin_products_menu")
async def callback_products_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки меню товаров."""
    await show_products_menu(callback, bot)


@router.callback_query(F.data.startswith("admin_products_list_"))
async def callback_products_list(callback: CallbackQuery, bot: Bot):
    """Обработчик списка товаров."""
    parts = callback.data.split("_")
    filter_type = parts[3] if len(parts) > 3 else "all"
    page = int(parts[4]) if len(parts) > 4 else 0
    await show_products_list(callback, bot, filter_type, page)


@router.callback_query(F.data.startswith("admin_product_view_"))
async def callback_product_view(callback: CallbackQuery, bot: Bot):
    """Обработчик просмотра товара."""
    product_id = int(callback.data.split("_")[3])
    await show_product_details(callback, bot, product_id)


@router.callback_query(F.data.startswith("admin_product_toggle_"))
async def callback_product_toggle(callback: CallbackQuery, bot: Bot):
    """Обработчик активации/деактивации товара."""
    product_id = int(callback.data.split("_")[3])
    await toggle_product_status(callback, bot, product_id)


@router.callback_query(F.data.startswith("admin_product_delete_"))
async def callback_product_delete(callback: CallbackQuery, bot: Bot):
    """Обработчик удаления товара."""
    product_id = int(callback.data.split("_")[3])
    await delete_product(callback, bot, product_id)


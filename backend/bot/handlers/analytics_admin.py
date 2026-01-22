"""
Обработчики аналитики и финансов для администратора.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
import os
from backend.app.config import settings

router = Router()


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


async def show_analytics_menu(callback: CallbackQuery, bot: Bot):
    """Показывает главное меню аналитики."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        menu_text = """
<b>📊 Аналитика и финансы</b>

Выберите раздел:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Общая статистика", callback_data="admin_analytics_platform")],
            [InlineKeyboardButton(text="💰 Финансовые отчеты", callback_data="admin_analytics_revenue")],
            [InlineKeyboardButton(text="🏆 Топ магазинов", callback_data="admin_analytics_top_shops")],
            [InlineKeyboardButton(text="📦 Топ товаров", callback_data="admin_analytics_top_products")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing analytics menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке меню аналитики.", show_alert=True)


async def show_platform_statistics(callback: CallbackQuery, bot: Bot):
    """Показывает общую статистику платформы."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from backend.app.services.database import DatabaseService
        
        db = DatabaseService(db_path=settings.DATABASE_PATH)
        await db.connect()
        
        # Активные магазины
        active_shops = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shops WHERE is_active = 1"
        )
        total_shops = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shops"
        )
        active_users = await db.fetch_one(
            """SELECT COUNT(DISTINCT user_id) as cnt 
               FROM orders 
               WHERE created_at >= datetime('now', '-30 days')"""
        )
        total_users = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM users"
        )
        total_products = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products"
        )
        active_products = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE is_active = 1"
        )
        
        await db.disconnect()
        
        stats = {
            "active_shops": active_shops["cnt"] if active_shops else 0,
            "total_shops": total_shops["cnt"] if total_shops else 0,
            "active_users": active_users["cnt"] if active_users else 0,
            "total_users": total_users["cnt"] if total_users else 0,
            "total_products": total_products["cnt"] if total_products else 0,
            "active_products": active_products["cnt"] if active_products else 0
        }
        
        text = f"""
<b>📈 Общая статистика платформы</b>

<b>Магазины:</b>
🏪 Всего магазинов: {stats.get('total_shops', 0)}
✅ Активных: {stats.get('active_shops', 0)}

<b>Пользователи:</b>
👤 Всего пользователей: {stats.get('total_users', 0)}
📊 Активных (за 30 дней): {stats.get('active_users', 0)}

<b>Товары:</b>
📦 Всего товаров: {stats.get('total_products', 0)}
✅ Активных: {stats.get('active_products', 0)}
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing platform statistics: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке статистики.", show_alert=True)
        except:
            pass


async def show_revenue_report(callback: CallbackQuery, bot: Bot, period: str = "month"):
    """Показывает финансовый отчет."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from backend.app.services.database import DatabaseService
        from decimal import Decimal
        
        db = DatabaseService(db_path=settings.DATABASE_PATH)
        await db.connect()
        
        period_map = {
            "day": "-1 day",
            "week": "-7 days",
            "month": "-30 days"
        }
        
        period_sql = period_map.get(period, "-30 days")
        
        # Выручка за период
        revenue = await db.fetch_one(
            f"""SELECT COALESCE(SUM(total_amount), 0) as total 
               FROM orders 
               WHERE created_at >= datetime('now', '{period_sql}')"""
        )
        
        # Количество заказов за период
        orders_count = await db.fetch_one(
            f"""SELECT COUNT(*) as cnt 
               FROM orders 
               WHERE created_at >= datetime('now', '{period_sql}')"""
        )
        
        # Средний чек за период
        avg_order = await db.fetch_one(
            f"""SELECT COALESCE(AVG(total_amount), 0) as avg 
               FROM orders 
               WHERE created_at >= datetime('now', '{period_sql}')"""
        )
        
        await db.disconnect()
        
        report = {
            "period": period,
            "revenue": float(revenue["total"]) if revenue and isinstance(revenue["total"], Decimal) else (revenue["total"] if revenue else 0),
            "orders_count": orders_count["cnt"] if orders_count else 0,
            "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0)
        }
        
        period_names = {
            "day": "За день",
            "week": "За неделю",
            "month": "За месяц"
        }
        
        text = f"""
<b>💰 Финансовый отчет</b>

<b>Период:</b> {period_names.get(period, period)}

<b>Выручка:</b> {report.get('revenue', 0):.2f} ₽
<b>Количество заказов:</b> {report.get('orders_count', 0)}
<b>Средний чек:</b> {report.get('average_order', 0):.2f} ₽
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 День", callback_data="admin_analytics_revenue_day"),
                InlineKeyboardButton(text="📅 Неделя", callback_data="admin_analytics_revenue_week"),
                InlineKeyboardButton(text="📅 Месяц", callback_data="admin_analytics_revenue_month")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing revenue report: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке отчета.", show_alert=True)
        except:
            pass


async def show_top_shops(callback: CallbackQuery, bot: Bot, limit: int = 10):
    """Показывает топ магазинов по выручке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from backend.app.services.database import DatabaseService
        from decimal import Decimal
        
        db = DatabaseService(db_path=settings.DATABASE_PATH)
        await db.connect()
        
        shops = await db.fetch_all(
            """SELECT s.id, s.name, s.is_active, s.is_verified,
                      COALESCE(SUM(o.total_amount), 0) as revenue,
                      COUNT(o.id) as orders_count
               FROM shops s
               LEFT JOIN orders o ON s.id = o.shop_id
               GROUP BY s.id
               ORDER BY revenue DESC
               LIMIT ?""",
            (limit,)
        )
        
        await db.disconnect()
        
        # Преобразуем Decimal в float
        shops_list = []
        for shop in shops:
            shop_dict = dict(shop)
            if shop_dict.get("revenue") is not None:
                if isinstance(shop_dict["revenue"], Decimal):
                    shop_dict["revenue"] = float(shop_dict["revenue"])
            shops_list.append(shop_dict)
        
        shops = shops_list
        
        if not shops:
            text = "<b>🏆 Топ магазинов</b>\n\nМагазинов не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = "<b>🏆 Топ магазинов по выручке</b>\n\n"
        
        for idx, shop in enumerate(shops, 1):
            status_emoji = "✅" if shop.get("is_active") else "❌"
            verified_emoji = "⭐" if shop.get("is_verified") else ""
            
            text += f"{idx}. {status_emoji} {verified_emoji} <b>{shop.get('name', 'Неизвестно')}</b>\n"
            text += f"   Выручка: {shop.get('revenue', 0):.2f} ₽\n"
            text += f"   Заказов: {shop.get('orders_count', 0)}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing top shops: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке топа магазинов.", show_alert=True)
        except:
            pass


async def show_top_products(callback: CallbackQuery, bot: Bot, limit: int = 10):
    """Показывает топ товаров по продажам."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from backend.app.services.database import DatabaseService
        from decimal import Decimal
        
        db = DatabaseService(db_path=settings.DATABASE_PATH)
        await db.connect()
        
        products = await db.fetch_all(
            """SELECT p.id, p.name, p.price, s.name as shop_name,
                      SUM(oi.quantity) as sold_quantity,
                      SUM(oi.price * oi.quantity) as revenue
               FROM products p
               LEFT JOIN order_items oi ON p.id = oi.product_id
               LEFT JOIN shops s ON p.shop_id = s.id
               GROUP BY p.id
               HAVING sold_quantity > 0
               ORDER BY sold_quantity DESC
               LIMIT ?""",
            (limit,)
        )
        
        await db.disconnect()
        
        # Преобразуем Decimal в float
        products_list = []
        for product in products:
            product_dict = dict(product)
            if product_dict.get("price") is not None:
                if isinstance(product_dict["price"], Decimal):
                    product_dict["price"] = float(product_dict["price"])
            if product_dict.get("revenue") is not None:
                if isinstance(product_dict["revenue"], Decimal):
                    product_dict["revenue"] = float(product_dict["revenue"])
            products_list.append(product_dict)
        
        products = products_list
        
        if not products:
            text = "<b>📦 Топ товаров</b>\n\nТоваров не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = "<b>📦 Топ товаров по продажам</b>\n\n"
        
        for idx, product in enumerate(products, 1):
            text += f"{idx}. <b>{product.get('name', 'Неизвестно')}</b>\n"
            text += f"   Магазин: {product.get('shop_name', 'Неизвестно')}\n"
            text += f"   Продано: {product.get('sold_quantity', 0)} шт.\n"
            text += f"   Выручка: {product.get('revenue', 0):.2f} ₽\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing top products: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке топа товаров.", show_alert=True)
        except:
            pass


# Обработчики callback
@router.callback_query(F.data == "admin_analytics_menu")
async def callback_analytics_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки меню аналитики."""
    await show_analytics_menu(callback, bot)


@router.callback_query(F.data == "admin_analytics_platform")
async def callback_analytics_platform(callback: CallbackQuery, bot: Bot):
    """Обработчик общей статистики."""
    await show_platform_statistics(callback, bot)


@router.callback_query(F.data.startswith("admin_analytics_revenue"))
async def callback_analytics_revenue(callback: CallbackQuery, bot: Bot):
    """Обработчик финансовых отчетов."""
    parts = callback.data.split("_")
    period = parts[3] if len(parts) > 3 else "month"
    await show_revenue_report(callback, bot, period)


@router.callback_query(F.data == "admin_analytics_top_shops")
async def callback_analytics_top_shops(callback: CallbackQuery, bot: Bot):
    """Обработчик топа магазинов."""
    await show_top_shops(callback, bot)


@router.callback_query(F.data == "admin_analytics_top_products")
async def callback_analytics_top_products(callback: CallbackQuery, bot: Bot):
    """Обработчик топа товаров."""
    await show_top_products(callback, bot)


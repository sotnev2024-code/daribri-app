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


async def show_revenue_report_menu(callback: CallbackQuery, bot: Bot):
    """Показывает меню выбора типа финансового отчета."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        text = """
<b>💰 Финансовые отчеты</b>

Выберите тип отчета:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_analytics_revenue_all")],
            [InlineKeyboardButton(text="🏪 По магазину", callback_data="admin_analytics_revenue_shops")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing revenue report menu: {e}")
        import traceback
        traceback.print_exc()
        try:
            await callback.answer("❌ Ошибка при загрузке меню.", show_alert=True)
        except:
            pass


async def show_revenue_report(callback: CallbackQuery, bot: Bot, period: str = "month", shop_id: int = None):
    """Показывает финансовый отчет."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from backend.app.services.database import DatabaseService
        from decimal import Decimal
        
        db = DatabaseService(db_path=settings.DATABASE_PATH)
        await db.connect()
        
        # Получаем информацию о магазине, если указан shop_id
        shop_name = None
        if shop_id:
            try:
                shop = await db.fetch_one("SELECT name FROM shops WHERE id = ?", (shop_id,))
                if shop:
                    shop_name = shop.get("name")
            except Exception as shop_error:
                print(f"[ANALYTICS] Error fetching shop name: {shop_error}")
                shop_name = None
        
        period_map = {
            "day": "-1 day",
            "week": "-7 days",
            "month": "-30 days"
        }
        
        period_sql = period_map.get(period, "-30 days")
        
        # Формируем условия для запроса
        conditions = ["status = 'delivered'", f"created_at >= datetime('now', '{period_sql}')"]
        params = []
        
        if shop_id:
            conditions.append("shop_id = ?")
            params.append(shop_id)
        
        where_clause = " AND ".join(conditions)
        
        # Выручка за период (только выполненные заказы)
        revenue = await db.fetch_one(
            f"""SELECT COALESCE(SUM(total_amount), 0) as total 
               FROM orders 
               WHERE {where_clause}""",
            tuple(params)
        )
        
        # Количество заказов за период (только выполненные)
        orders_count = await db.fetch_one(
            f"""SELECT COUNT(*) as cnt 
               FROM orders 
               WHERE {where_clause}""",
            tuple(params)
        )
        
        # Средний чек за период (только выполненные)
        avg_order = await db.fetch_one(
            f"""SELECT COALESCE(AVG(total_amount), 0) as avg 
               FROM orders 
               WHERE {where_clause}""",
            tuple(params)
        )
        
        await db.disconnect()
        
        report = {
            "period": period,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "revenue": float(revenue["total"]) if revenue and isinstance(revenue["total"], Decimal) else (revenue["total"] if revenue else 0),
            "orders_count": orders_count["cnt"] if orders_count else 0,
            "average_order": float(avg_order["avg"]) if avg_order and isinstance(avg_order["avg"], Decimal) else (avg_order["avg"] if avg_order else 0)
        }
        
        period_names = {
            "day": "За день",
            "week": "За неделю",
            "month": "За месяц"
        }
        
        title = "💰 Финансовый отчет"
        if shop_name:
            title = f"💰 Финансовый отчет: {shop_name}"
        
        text = f"""
<b>{title}</b>

<b>Период:</b> {period_names.get(period, period)}
<b>Статус:</b> Только выполненные заказы

<b>Выручка:</b> {report.get('revenue', 0):.2f} ₽
<b>Количество заказов:</b> {report.get('orders_count', 0)}
<b>Средний чек:</b> {report.get('average_order', 0):.2f} ₽
"""
        
        keyboard_buttons = [
            [
                InlineKeyboardButton(text="📅 День", callback_data=f"admin_analytics_revenue_period_day_{shop_id or 'all'}"),
                InlineKeyboardButton(text="📅 Неделя", callback_data=f"admin_analytics_revenue_period_week_{shop_id or 'all'}"),
                InlineKeyboardButton(text="📅 Месяц", callback_data=f"admin_analytics_revenue_period_month_{shop_id or 'all'}")
            ]
        ]
        
        if shop_id:
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад к выбору магазина", callback_data="admin_analytics_revenue_shops")])
        else:
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_revenue_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
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


async def show_shops_for_revenue(callback: CallbackQuery, bot: Bot):
    """Показывает список магазинов для выбора финансового отчета."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        from backend.app.services.database import DatabaseService
        from decimal import Decimal
        
        db = DatabaseService(db_path=settings.DATABASE_PATH)
        await db.connect()
        
        # Получаем все магазины с выручкой от выполненных заказов
        shops = await db.fetch_all(
            """SELECT s.id, s.name, s.is_active, s.is_verified,
                      COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.total_amount ELSE 0 END), 0) as revenue,
                      COUNT(CASE WHEN o.status = 'delivered' THEN o.id END) as orders_count
               FROM shops s
               LEFT JOIN orders o ON s.id = o.shop_id
               GROUP BY s.id, s.name, s.is_active, s.is_verified
               ORDER BY revenue DESC"""
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
            text = "<b>🏪 Выбор магазина</b>\n\nМагазинов не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_revenue_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = "<b>🏪 Выберите магазин для финансового отчета:</b>\n\n"
        keyboard_buttons = []
        
        for shop in shops:
            shop_id = shop.get("id")
            shop_name = shop.get("name", "Без названия")
            revenue = shop.get("revenue", 0)
            orders_count = shop.get("orders_count", 0)
            is_active = shop.get("is_active", 1)
            
            status_emoji = "✅" if is_active else "❌"
            text += f"{status_emoji} <b>{shop_name}</b>\n"
            text += f"   Выручка: {revenue:.2f} ₽ ({orders_count} заказов)\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{shop_name} ({revenue:.0f} ₽)",
                    callback_data=f"admin_analytics_revenue_shop_{shop_id}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_analytics_revenue_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing shops for revenue: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке магазинов.", show_alert=True)


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
                      COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.total_amount ELSE 0 END), 0) as revenue,
                      COUNT(CASE WHEN o.status = 'delivered' THEN o.id END) as orders_count
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


@router.callback_query(F.data == "admin_analytics_revenue")
async def callback_analytics_revenue(callback: CallbackQuery, bot: Bot):
    """Обработчик кнопки финансовых отчетов - показывает меню выбора."""
    await show_revenue_report_menu(callback, bot)


@router.callback_query(F.data == "admin_analytics_revenue_menu")
async def callback_analytics_revenue_menu(callback: CallbackQuery, bot: Bot):
    """Обработчик возврата в меню финансовых отчетов."""
    await show_revenue_report_menu(callback, bot)


@router.callback_query(F.data == "admin_analytics_revenue_all")
async def callback_analytics_revenue_all(callback: CallbackQuery, bot: Bot):
    """Обработчик общей статистики финансовых отчетов."""
    await show_revenue_report(callback, bot, period="month", shop_id=None)


@router.callback_query(F.data == "admin_analytics_revenue_shops")
async def callback_analytics_revenue_shops(callback: CallbackQuery, bot: Bot):
    """Обработчик выбора магазина для финансового отчета."""
    await show_shops_for_revenue(callback, bot)


@router.callback_query(F.data.startswith("admin_analytics_revenue_shop_"))
async def callback_analytics_revenue_shop(callback: CallbackQuery, bot: Bot):
    """Обработчик выбора конкретного магазина для финансового отчета."""
    try:
        parts = callback.data.split("_")
        shop_id = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
        if shop_id:
            await show_revenue_report(callback, bot, period="month", shop_id=shop_id)
        else:
            await callback.answer("❌ Неверный ID магазина.", show_alert=True)
    except Exception as e:
        print(f"[ANALYTICS] Error in callback_analytics_revenue_shop: {e}")
        await callback.answer("❌ Ошибка при выборе магазина.", show_alert=True)


@router.callback_query(F.data.startswith("admin_analytics_revenue_period_"))
async def callback_analytics_revenue_period(callback: CallbackQuery, bot: Bot):
    """Обработчик выбора периода для финансового отчета."""
    try:
        # Формат: admin_analytics_revenue_period_{period}_{shop_id_or_all}
        parts = callback.data.split("_")
        if len(parts) >= 5:
            period = parts[4]  # day, week, month
            shop_param = parts[5] if len(parts) > 5 else "all"  # shop_id или 'all'
            shop_id = int(shop_param) if shop_param.isdigit() else None
            await show_revenue_report(callback, bot, period=period, shop_id=shop_id)
        else:
            await callback.answer("❌ Неверный формат запроса.", show_alert=True)
    except Exception as e:
        print(f"[ANALYTICS] Error in callback_analytics_revenue_period: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при обработке запроса.", show_alert=True)


@router.callback_query(F.data == "admin_analytics_top_shops")
async def callback_analytics_top_shops(callback: CallbackQuery, bot: Bot):
    """Обработчик топа магазинов."""
    await show_top_shops(callback, bot)


@router.callback_query(F.data == "admin_analytics_top_products")
async def callback_analytics_top_products(callback: CallbackQuery, bot: Bot):
    """Обработчик топа товаров."""
    await show_top_products(callback, bot)


"""
Обработчик команды /admin для управления заявками на магазины.
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, date
from decimal import Decimal

router = Router()


class PromoCreateStates(StatesGroup):
    """Состояния для создания промокода."""
    waiting_for_code = State()
    waiting_for_type = State()
    waiting_for_value = State()
    waiting_for_description = State()
    waiting_for_use_once = State()
    waiting_for_first_order_only = State()
    waiting_for_shop_id = State()
    waiting_for_min_amount = State()
    waiting_for_valid_from = State()
    waiting_for_valid_until = State()


class BannerCreateStates(StatesGroup):
    """Состояния для создания баннера."""
    waiting_for_title = State()
    waiting_for_image = State()
    waiting_for_link_type = State()
    waiting_for_link_value = State()
    waiting_for_display_order = State()


class SubscriptionPlanCreateStates(StatesGroup):
    """Состояния для создания плана подписки."""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_duration_days = State()
    waiting_for_max_products = State()


# Список администраторов (можно вынести в config)
ADMIN_IDS = []  # Будет заполняться из .env или config


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    from backend.app.config import settings
    
    # Используем тот же путь к базе данных, что и в FastAPI
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    
    # Проверяем и создаем таблицу promos, если её нет, или добавляем недостающие колонки
    try:
        promos_table = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='promos'")
        if not promos_table:
            print("[MIGRATION] Creating promos table in bot handler...")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    promo_type TEXT NOT NULL CHECK(promo_type IN ('percent', 'fixed', 'free_delivery')),
                    value DECIMAL(10, 2) NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    use_once INTEGER DEFAULT 0,
                    first_order_only INTEGER DEFAULT 0,
                    shop_id INTEGER,
                    min_order_amount DECIMAL(10, 2),
                    valid_from DATE,
                    valid_until DATE,
                    max_uses INTEGER,
                    current_uses INTEGER DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
                )
            """)
            await db.commit()
            print("[MIGRATION] promos table created successfully in bot handler")
        else:
            # Проверяем структуру таблицы и добавляем недостающие колонки
            promos_columns = await db.fetch_all("PRAGMA table_info(promos)")
            promos_column_names = [col["name"] for col in promos_columns]
            
            # Список обязательных колонок с их определениями
            required_columns = {
                "value": "DECIMAL(10, 2) NOT NULL DEFAULT 0",
                "description": "TEXT",
                "is_active": "INTEGER DEFAULT 1",
                "use_once": "INTEGER DEFAULT 0",
                "first_order_only": "INTEGER DEFAULT 0",
                "shop_id": "INTEGER",
                "min_order_amount": "DECIMAL(10, 2)",
                "valid_from": "DATE",
                "valid_until": "DATE",
                "max_uses": "INTEGER",
                "current_uses": "INTEGER DEFAULT 0",
                "usage_count": "INTEGER DEFAULT 0",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            }
            
            # Проверяем и обновляем старые колонки discount_type и discount_value, если они существуют
            if "discount_type" in promos_column_names:
                discount_type_col = next((col for col in promos_columns if col["name"] == "discount_type"), None)
                if discount_type_col and discount_type_col.get("notnull") == 1:
                    try:
                        await db.execute(
                            "UPDATE promos SET discount_type = promo_type WHERE discount_type IS NULL OR discount_type = ''"
                        )
                        await db.commit()
                        print("[MIGRATION] Updated existing promos with discount_type = promo_type in bot handler")
                    except Exception as e:
                        print(f"[MIGRATION] Could not update discount_type in bot handler: {e}")
            
            if "discount_value" in promos_column_names:
                discount_value_col = next((col for col in promos_columns if col["name"] == "discount_value"), None)
                if discount_value_col and discount_value_col.get("notnull") == 1:
                    try:
                        await db.execute(
                            "UPDATE promos SET discount_value = value WHERE discount_value IS NULL"
                        )
                        await db.commit()
                        print("[MIGRATION] Updated existing promos with discount_value = value in bot handler")
                    except Exception as e:
                        print(f"[MIGRATION] Could not update discount_value in bot handler: {e}")
            
            # Добавляем все недостающие колонки
            for column_name, column_definition in required_columns.items():
                if column_name not in promos_column_names:
                    print(f"[MIGRATION] Adding {column_name} column to promos table in bot handler...")
                    try:
                        await db.execute(
                            f"ALTER TABLE promos ADD COLUMN {column_name} {column_definition}"
                        )
                        await db.commit()
                        print(f"[MIGRATION] {column_name} column added successfully in bot handler")
                    except Exception as e:
                        print(f"[MIGRATION] Error adding {column_name} column in bot handler: {e}")
    except Exception as e:
        print(f"[WARNING] Error checking/creating promos table: {e}")
        # Продолжаем работу, возможно таблица уже существует
    
    return db


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    from backend.app.config import settings
    
    # Получаем список администраторов из переменных окружения
    import os
    admin_ids_str = os.getenv("ADMIN_IDS", "") or getattr(settings, "ADMIN_IDS", "")
    
    if admin_ids_str:
        try:
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
            return user_id in admin_ids
        except (ValueError, AttributeError):
            pass
    
    # Если не указаны, разрешаем всем (для разработки)
    # В продакшене лучше вернуть False
    return True  # Временно разрешаем всем для разработки


@router.message(Command("admin"))
async def cmd_admin(message: Message, bot: Bot):
    """Главное меню администратора."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    await show_admin_menu(message, bot)


async def show_admin_menu(message: Message, bot: Bot):
    """Показывает главное меню администратора."""
    try:
        db = await get_db()
        
        # Получаем статистику заявок
        pending_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests WHERE status = 'pending'"
        )
        approved_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests WHERE status = 'approved'"
        )
        rejected_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests WHERE status = 'rejected'"
        )
        
        total_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests"
        )
        
        await db.disconnect()
        
        menu_text = f"""
<b>🔐 Панель администратора</b>

<b>Статистика заявок:</b>
📝 Всего заявок: {total_count['cnt']}
⏳ На рассмотрении: {pending_count['cnt']}
✅ Одобрено: {approved_count['cnt']}
❌ Отклонено: {rejected_count['cnt']}

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏪 Магазины", callback_data="admin_shops_menu")],
            [InlineKeyboardButton(text="📦 Товары", callback_data="admin_products_menu")],
            [InlineKeyboardButton(text="📂 Категории", callback_data="admin_categories_menu")],
            [InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders_menu")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_menu")],
            [InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_analytics_menu")],
            [InlineKeyboardButton(text="📋 Заявки", callback_data="admin_requests_menu")],
            [InlineKeyboardButton(text="💳 Управление подписками", callback_data="admin_subscriptions")],
            [InlineKeyboardButton(text="🎫 Промокоды", callback_data="admin_promos_menu")]
        ])
        
        await message.answer(menu_text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Error showing admin menu: {e}")
        await message.answer("❌ Ошибка при загрузке меню администратора.")


@router.callback_query(F.data.startswith("admin_"))
async def admin_callback_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обрабатывает callback от кнопок администратора."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    action = callback.data
    
    if action == "admin_requests_menu":
        await show_requests_menu(callback, bot)
    elif action == "admin_users_menu":
        from .users_admin import show_users_menu
        await show_users_menu(callback, bot)
    elif action == "admin_promos_menu":
        await show_promos_menu(callback, bot)
    elif action == "admin_all_requests":
        await show_requests_list(callback, bot, status=None)
    elif action == "admin_pending_requests":
        await show_requests_list(callback, bot, status="pending")
    elif action == "admin_approved_requests":
        await show_requests_list(callback, bot, status="approved")
    elif action == "admin_rejected_requests":
        await show_requests_list(callback, bot, status="rejected")
    elif action.startswith("admin_view_request_"):
        request_id = int(action.split("_")[3])
        await show_request_details(callback, bot, request_id)
    elif action.startswith("admin_approve_request_"):
        request_id = int(action.split("_")[3])
        await approve_request(callback, bot, request_id)
    elif action.startswith("admin_reject_request_"):
        request_id = int(action.split("_")[3])
        await reject_request(callback, bot, request_id)
    elif action.startswith("admin_delete_request_"):
        request_id = int(action.split("_")[3])
        await delete_request(callback, bot, request_id)
    elif action.startswith("admin_back_to_menu"):
        await show_admin_menu(callback.message, bot)
        await callback.answer()
    elif action.startswith("admin_back_to_list_"):
        status = action.split("_")[4] if len(action.split("_")) > 4 else None
        if status == "None":
            status = None
        await show_requests_list(callback, bot, status=status)
        await callback.answer()
    elif action == "admin_create_promo":
        await start_create_promo(callback, bot, state)
        await callback.answer()
    elif action == "admin_list_promos":
        await show_promos_list(callback, bot)
        await callback.answer()
    elif action == "admin_promos_statistics":
        await show_promo_statistics(callback, bot)
        await callback.answer()
    elif action == "admin_shops_menu":
        from .shops_admin import show_shops_menu
        await show_shops_menu(callback, bot)
        await callback.answer()
    elif action == "admin_products_menu":
        from .products_admin import show_products_menu
        await show_products_menu(callback, bot)
        await callback.answer()
    elif action == "admin_orders_menu":
        from .orders_admin import show_orders_menu
        await show_orders_menu(callback, bot)
        await callback.answer()
    elif action == "admin_analytics_menu":
        from .analytics_admin import show_analytics_menu
        await show_analytics_menu(callback, bot)
        await callback.answer()
    elif action == "admin_subscriptions":
        from .subscriptions_admin import show_subscription_plans_list
        await show_subscription_plans_list(callback, bot)
        await callback.answer()
    elif action == "admin_create_subscription":
        from .subscriptions_admin import start_create_subscription_plan
        await start_create_subscription_plan(callback, bot, state)
        await callback.answer()
    elif action.startswith("admin_view_subscription_"):
        plan_id = int(action.split("_")[3])
        from .subscriptions_admin import show_subscription_plan_details
        await show_subscription_plan_details(callback, bot, plan_id)
        await callback.answer()
    elif action.startswith("admin_edit_subscription_"):
        plan_id = int(action.split("_")[3])
        from .subscriptions_admin import start_edit_subscription_plan
        await start_edit_subscription_plan(callback, bot, state, plan_id)
        await callback.answer()
    elif action.startswith("admin_delete_subscription_"):
        plan_id = int(action.split("_")[3])
        from .subscriptions_admin import delete_subscription_plan
        await delete_subscription_plan(callback, bot, plan_id)
        await callback.answer()
    elif action.startswith("admin_toggle_subscription_"):
        plan_id = int(action.split("_")[3])
        from .subscriptions_admin import toggle_subscription_plan
        await toggle_subscription_plan(callback, bot, plan_id)
        await callback.answer()
    
    # Импортируем функции из banners.py
    from .banners import (
        show_banners_list, start_create_banner, delete_banner, toggle_banner
    )


async def show_requests_menu(callback: CallbackQuery, bot: Bot):
    """Показывает подменю заявок."""
    try:
        db = await get_db()
        
        # Получаем статистику заявок
        pending_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests WHERE status = 'pending'"
        )
        approved_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests WHERE status = 'approved'"
        )
        rejected_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests WHERE status = 'rejected'"
        )
        total_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_requests"
        )
        
        await db.disconnect()
        
        menu_text = f"""
<b>📋 Управление заявками</b>

<b>Статистика:</b>
📝 Всего заявок: {total_count['cnt']}
⏳ На рассмотрении: {pending_count['cnt']}
✅ Одобрено: {approved_count['cnt']}
❌ Отклонено: {rejected_count['cnt']}

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все заявки", callback_data="admin_all_requests")],
            [InlineKeyboardButton(text="⏳ На рассмотрении", callback_data="admin_pending_requests")],
            [InlineKeyboardButton(text="✅ Одобренные", callback_data="admin_approved_requests")],
            [InlineKeyboardButton(text="❌ Отклоненные", callback_data="admin_rejected_requests")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing requests menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню заявок.", show_alert=True)


async def show_promos_menu(callback: CallbackQuery, bot: Bot):
    """Показывает подменю промокодов."""
    try:
        menu_text = """
<b>🎫 Управление промокодами</b>

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
            [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_promos_statistics")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing promos menu: {e}")
        await callback.answer("❌ Ошибка при загрузке меню промокодов.", show_alert=True)


async def show_requests_list(callback: CallbackQuery, bot: Bot, status: str = None):
    """Показывает список заявок."""
    try:
        db = await get_db()
        
        if status:
            requests = await db.fetch_all(
                "SELECT * FROM shop_requests WHERE status = ? ORDER BY created_at DESC LIMIT 20",
                (status,)
            )
            status_text = {
                "pending": "⏳ На рассмотрении",
                "approved": "✅ Одобренные",
                "rejected": "❌ Отклоненные"
            }.get(status, status)
        else:
            requests = await db.fetch_all(
                "SELECT * FROM shop_requests ORDER BY created_at DESC LIMIT 20",
                ()
            )
            status_text = "Все"
        
        await db.disconnect()
        
        if not requests:
            text = f"<b>📋 Заявки ({status_text})</b>\n\nЗаявок не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        # Формируем список заявок
        text = f"<b>📋 Заявки ({status_text})</b>\n\n"
        keyboard_buttons = []
        
        for req in requests[:10]:  # Показываем первые 10
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌"
            }.get(req["status"], "📝")
            
            text += f"{status_emoji} <b>#{req['id']}</b> - {req['name']}\n"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"#{req['id']} - {req['name'][:30]}",
                    callback_data=f"admin_view_request_{req['id']}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к заявкам", callback_data="admin_requests_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing requests list: {e}")
        await callback.answer("❌ Ошибка при загрузке списка заявок.", show_alert=True)


async def show_request_details(callback: CallbackQuery, bot: Bot, request_id: int):
    """Показывает детали заявки."""
    try:
        db = await get_db()
        
        request = await db.fetch_one(
            "SELECT * FROM shop_requests WHERE id = ?",
            (request_id,)
        )
        
        await db.disconnect()
        
        if not request:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return
        
        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌"
        }.get(request["status"], "📝")
        
        status_text = {
            "pending": "На рассмотрении",
            "approved": "Одобрена",
            "rejected": "Отклонена"
        }.get(request["status"], request["status"])
        
        text = f"""
<b>{status_emoji} Заявка #{request_id} - {status_text}</b>

<b>Информация о магазине:</b>
🏪 Название: {request['name']}
📍 Адрес: {request['address']}
📞 Телефон: {request['phone']}
📝 Описание: {request['description']}

<b>Владелец:</b>
👤 ФИО: {request['owner_name']}
📱 Телефон: {request['owner_phone']}
💬 Telegram: @{request['owner_telegram']}

<b>От пользователя:</b> ID {request['telegram_user_id']}
<b>Дата создания:</b> {request['created_at']}
"""
        
        keyboard_buttons = []
        
        if request["status"] == "pending":
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_approve_request_{request_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_request_{request_id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_delete_request_{request_id}")
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data=f"admin_back_to_list_{request['status']}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Если есть фото, отправляем фото с подписью
        if request.get("photo_file_id"):
            try:
                await callback.message.delete()
                await bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=request["photo_file_id"],
                    caption=text,
                    reply_markup=keyboard
                )
            except Exception as photo_error:
                print(f"Error sending photo: {photo_error}")
                await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard)
        
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing request details: {e}")
        await callback.answer("❌ Ошибка при загрузке заявки.", show_alert=True)


async def approve_request(callback: CallbackQuery, bot: Bot, request_id: int):
    """Одобряет заявку."""
    try:
        db = await get_db()
        
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
                import hashlib
                
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
                import hashlib
                
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
        
        # Обновляем сообщение в группе, если оно есть
        if request.get("group_message_id"):
            try:
                from backend.app.config import settings
                group_id = settings.SHOP_REQUESTS_GROUP_ID
                topic_id = settings.SHOP_REQUESTS_TOPIC_ID
                
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
                
                # Пытаемся обновить сообщение с текстом
                try:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=request["group_message_id"],
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
                                reply_markup=None
                            )
                        except Exception as markup_error:
                            print(f"Error removing reply markup: {markup_error}")
            except Exception as update_error:
                print(f"Error updating group message: {update_error}")
        
        await callback.answer("✅ Заявка одобрена")
        
        # Возвращаемся к деталям заявки
        await show_request_details(callback, bot, request_id)
        
    except Exception as e:
        print(f"Error approving request: {e}")
        await callback.answer("❌ Ошибка при одобрении заявки", show_alert=True)


async def reject_request(callback: CallbackQuery, bot: Bot, request_id: int):
    """Отклоняет заявку."""
    try:
        db = await get_db()
        
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
        
        # Обновляем статус
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
        
        # Обновляем сообщение в группе, если оно есть
        if request.get("group_message_id"):
            try:
                from backend.app.config import settings
                group_id = settings.SHOP_REQUESTS_GROUP_ID
                
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
                
                try:
                    await bot.edit_message_text(
                        chat_id=group_id,
                        message_id=request["group_message_id"],
                        text=updated_text,
                        reply_markup=None
                    )
                except Exception:
                    if request.get("photo_file_id"):
                        await bot.edit_message_caption(
                            chat_id=group_id,
                            message_id=request["group_message_id"],
                            caption=updated_text,
                            reply_markup=None
                        )
            except Exception as update_error:
                print(f"Error updating group message: {update_error}")
        
        await callback.answer("❌ Заявка отклонена")
        
        # Возвращаемся к деталям заявки
        await show_request_details(callback, bot, request_id)
        
    except Exception as e:
        print(f"Error rejecting request: {e}")
        await callback.answer("❌ Ошибка при отклонении заявки", show_alert=True)


async def delete_request(callback: CallbackQuery, bot: Bot, request_id: int):
    """Удаляет заявку."""
    try:
        db = await get_db()
        
        request = await db.fetch_one(
            "SELECT * FROM shop_requests WHERE id = ?",
            (request_id,)
        )
        
        if not request:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return
        
        # Удаляем заявку
        await db.execute(
            "DELETE FROM shop_requests WHERE id = ?",
            (request_id,)
        )
        await db.commit()
        await db.disconnect()
        
        await callback.answer("🗑️ Заявка удалена")
        
        # Возвращаемся к списку заявок
        await show_requests_list(callback, bot, status=request["status"])
        
    except Exception as e:
        print(f"Error deleting request: {e}")
        await callback.answer("❌ Ошибка при удалении заявки", show_alert=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def start_create_promo(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начинает процесс создания промокода."""
    await state.clear()
    
    text = """
<b>🎫 Создание промокода</b>

Вы создаете новый промокод для скидок.

<b>Шаг 1/10: Код промокода</b>

Введите код промокода (буквы и цифры, до 50 символов):
Пример: SUMMER2024, WELCOME10, NEWUSER
"""
    
    await callback.message.edit_text(text)
    await callback.message.answer(
        "Введите код промокода:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PromoCreateStates.waiting_for_code)
    await callback.answer()


@router.message(PromoCreateStates.waiting_for_code, F.text != "❌ Отменить")
async def process_promo_code(message: Message, state: FSMContext):
    """Обрабатывает код промокода."""
    code = message.text.strip().upper()
    
    if len(code) < 2 or len(code) > 50:
        await message.answer("❌ Код должен содержать от 2 до 50 символов. Попробуйте еще раз:")
        return
    
    # Проверяем, не существует ли уже такой промокод
    try:
        db = await get_db()
        existing = await db.fetch_one(
            "SELECT id FROM promos WHERE code = ?",
            (code,)
        )
        await db.disconnect()
        
        if existing:
            await message.answer(f"❌ Промокод {code} уже существует. Введите другой код:")
            return
    except Exception as e:
        print(f"Error checking existing promo: {e}")
    
    await state.update_data(code=code)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Процент (%)", callback_data="promo_type:percent")],
        [InlineKeyboardButton(text="2️⃣ Фиксированная сумма (₽)", callback_data="promo_type:fixed")],
        [InlineKeyboardButton(text="3️⃣ Бесплатная доставка", callback_data="promo_type:free_delivery")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="promo_cancel")]
    ])
    
    await message.answer(
        "<b>Шаг 2/10: Тип промокода</b>\n\n"
        "Выберите тип промокода:",
        reply_markup=keyboard
    )
    await state.set_state(PromoCreateStates.waiting_for_type)


@router.callback_query(F.data.startswith("promo_type:"))
async def process_promo_type_callback(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа промокода через кнопку."""
    # Проверяем, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != PromoCreateStates.waiting_for_type:
        await callback.answer("⚠️ Это действие недоступно в текущем состоянии.", show_alert=True)
        return
    
    promo_type = callback.data.split(":")[1]
    await state.update_data(promo_type=promo_type)
    await callback.answer()
    
    type_texts = {
        "percent": "процентов (например, 10 для 10%)",
        "fixed": "рублей (например, 500 для 500 ₽)",
        "free_delivery": "не требуется (введите 0)"
    }
    
    try:
        await callback.message.edit_text(
            f"<b>Шаг 3/10: Значение скидки</b>\n\n"
            f"Выбран тип: <b>{promo_type}</b>\n\n"
            f"Введите значение скидки в {type_texts[promo_type]}:",
            reply_markup=get_cancel_keyboard()
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        await callback.message.answer(
            f"<b>Шаг 3/10: Значение скидки</b>\n\n"
            f"Выбран тип: <b>{promo_type}</b>\n\n"
            f"Введите значение скидки в {type_texts[promo_type]}:",
            reply_markup=get_cancel_keyboard()
        )
    
    await state.set_state(PromoCreateStates.waiting_for_value)


@router.message(PromoCreateStates.waiting_for_type, F.text != "❌ Отменить")
async def process_promo_type(message: Message, state: FSMContext):
    """Обрабатывает тип промокода (для обратной совместимости)."""
    text = message.text.strip().lower()
    
    type_mapping = {
        "1": "percent",
        "percent": "percent",
        "процент": "percent",
        "2": "fixed",
        "fixed": "fixed",
        "фиксированная": "fixed",
        "3": "free_delivery",
        "free_delivery": "free_delivery",
        "free": "free_delivery",
        "бесплатная доставка": "free_delivery",
        "доставка": "free_delivery"
    }
    
    promo_type = type_mapping.get(text)
    
    if not promo_type:
        await message.answer("❌ Неверный тип. Используйте кнопки выше или введите 1 (percent), 2 (fixed) или 3 (free_delivery):")
        return
    
    # Этот код теперь в callback обработчике
    pass


@router.message(PromoCreateStates.waiting_for_value, F.text != "❌ Отменить")
async def process_promo_value(message: Message, state: FSMContext):
    """Обрабатывает значение промокода."""
    try:
        value = float(message.text.strip().replace(",", "."))
        
        if value < 0:
            await message.answer("❌ Значение не может быть отрицательным. Попробуйте еще раз:")
            return
        
        data = await state.get_data()
        promo_type = data.get("promo_type")
        
        if promo_type == "percent" and value > 100:
            await message.answer("❌ Процент не может быть больше 100. Попробуйте еще раз:")
            return
        
        await state.update_data(value=value)
        
        await message.answer(
            "<b>Шаг 4/10: Описание</b>\n\n"
            "Введите описание промокода (необязательно, можно пропустить введя '-'):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(PromoCreateStates.waiting_for_description)
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте еще раз:")


@router.message(PromoCreateStates.waiting_for_description, F.text != "❌ Отменить")
async def process_promo_description(message: Message, state: FSMContext):
    """Обрабатывает описание промокода."""
    description = message.text.strip()
    if description == "-":
        description = None
    
    await state.update_data(description=description)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="promo_use_once:1")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="promo_use_once:0")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="promo_cancel")]
    ])
    
    await message.answer(
        "<b>Шаг 5/10: Использование один раз</b>\n\n"
        "Можно ли использовать промокод только один раз?",
        reply_markup=keyboard
    )
    await state.set_state(PromoCreateStates.waiting_for_use_once)


@router.callback_query(F.data.startswith("promo_use_once:"))
async def process_promo_use_once_callback(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор 'использовать один раз' через кнопку."""
    # Проверяем, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != PromoCreateStates.waiting_for_use_once:
        await callback.answer("⚠️ Это действие недоступно в текущем состоянии.", show_alert=True)
        return
    
    use_once = callback.data.split(":")[1] == "1"
    await state.update_data(use_once=use_once)
    await callback.answer()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="promo_first_order:1")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="promo_first_order:0")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="promo_cancel")]
    ])
    
    try:
        await callback.message.edit_text(
            "<b>Шаг 6/10: Только для первого заказа</b>\n\n"
            "Действует ли промокод только для первого заказа пользователя?",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        await callback.message.answer(
            "<b>Шаг 6/10: Только для первого заказа</b>\n\n"
            "Действует ли промокод только для первого заказа пользователя?",
            reply_markup=keyboard
        )
    
    await state.set_state(PromoCreateStates.waiting_for_first_order_only)


@router.message(PromoCreateStates.waiting_for_use_once, F.text != "❌ Отменить")
async def process_promo_use_once(message: Message, state: FSMContext):
    """Обрабатывает флаг 'использовать один раз' (для обратной совместимости)."""
    text = message.text.strip().lower()
    use_once = text in ["да", "yes", "y", "1", "true", "✓"]
    
    await state.update_data(use_once=use_once)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="promo_first_order:1")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="promo_first_order:0")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="promo_cancel")]
    ])
    
    await message.answer(
        "<b>Шаг 6/10: Только для первого заказа</b>\n\n"
        "Действует ли промокод только для первого заказа пользователя?",
        reply_markup=keyboard
    )
    await state.set_state(PromoCreateStates.waiting_for_first_order_only)


@router.callback_query(F.data.startswith("promo_first_order:"))
async def process_promo_first_order_callback(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор 'только для первого заказа' через кнопку."""
    # Проверяем, что мы в правильном состоянии
    current_state = await state.get_state()
    if current_state != PromoCreateStates.waiting_for_first_order_only:
        await callback.answer("⚠️ Это действие недоступно в текущем состоянии.", show_alert=True)
        return
    
    first_order_only = callback.data.split(":")[1] == "1"
    await state.update_data(first_order_only=first_order_only)
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "<b>Шаг 7/10: Для определенного магазина</b>\n\n"
            "Действует ли промокод только для определенного магазина?\n"
            "Если нет, введите '-'\n"
            "Если да, введите ID магазина (число):",
            reply_markup=get_cancel_keyboard()
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        await callback.message.answer(
            "<b>Шаг 7/10: Для определенного магазина</b>\n\n"
            "Действует ли промокод только для определенного магазина?\n"
            "Если нет, введите '-'\n"
            "Если да, введите ID магазина (число):",
            reply_markup=get_cancel_keyboard()
        )
    
    await state.set_state(PromoCreateStates.waiting_for_shop_id)


@router.message(PromoCreateStates.waiting_for_first_order_only, F.text != "❌ Отменить")
async def process_promo_first_order(message: Message, state: FSMContext):
    """Обрабатывает флаг 'только для первого заказа' (для обратной совместимости)."""
    text = message.text.strip().lower()
    first_order_only = text in ["да", "yes", "y", "1", "true", "✓"]
    
    await state.update_data(first_order_only=first_order_only)
    
    await message.answer(
        "<b>Шаг 7/10: Для определенного магазина</b>\n\n"
        "Действует ли промокод только для определенного магазина?\n"
        "Если нет, введите '-'\n"
        "Если да, введите ID магазина (число):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PromoCreateStates.waiting_for_shop_id)


@router.message(PromoCreateStates.waiting_for_shop_id, F.text != "❌ Отменить")
async def process_promo_shop_id(message: Message, state: FSMContext):
    """Обрабатывает ID магазина для промокода."""
    text = message.text.strip()
    shop_id = None
    
    if text != "-":
        try:
            shop_id = int(text)
            
            # Проверяем, существует ли магазин
            db = await get_db()
            shop = await db.fetch_one("SELECT id FROM shops WHERE id = ?", (shop_id,))
            await db.disconnect()
            
            if not shop:
                await message.answer(f"❌ Магазин с ID {shop_id} не найден. Введите другой ID или '-' для пропуска:")
                return
        except ValueError:
            await message.answer("❌ Введите число (ID магазина) или '-' для пропуска:")
            return
    
    await state.update_data(shop_id=shop_id)
    
    await message.answer(
        "<b>Шаг 8/10: Минимальная сумма заказа</b>\n\n"
        "Укажите минимальную сумму заказа для применения промокода (в рублях).\n"
        "Если ограничения нет, введите '-' или 0:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PromoCreateStates.waiting_for_min_amount)


@router.message(PromoCreateStates.waiting_for_min_amount, F.text != "❌ Отменить")
async def process_promo_min_amount(message: Message, state: FSMContext):
    """Обрабатывает минимальную сумму заказа."""
    text = message.text.strip()
    min_amount = None
    
    if text != "-" and text != "0":
        try:
            min_amount = float(text.replace(",", "."))
            if min_amount < 0:
                await message.answer("❌ Сумма не может быть отрицательной. Попробуйте еще раз:")
                return
        except ValueError:
            await message.answer("❌ Введите число (минимальная сумма) или '-' для пропуска:")
            return
    
    await state.update_data(min_order_amount=min_amount)
    
    await message.answer(
        "<b>Шаг 9/10: Дата начала действия</b>\n\n"
        "Введите дату начала действия промокода в формате ДД.ММ.ГГГГ\n"
        "Например: 01.12.2024\n"
        "Если начинается сразу, введите '-':",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PromoCreateStates.waiting_for_valid_from)


@router.message(PromoCreateStates.waiting_for_valid_from, F.text != "❌ Отменить")
async def process_promo_valid_from(message: Message, state: FSMContext):
    """Обрабатывает дату начала действия (для обратной совместимости)."""
    text = message.text.strip()
    valid_from = None
    
    if text != "-":
        try:
            valid_from = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ (например, 01.12.2024) или '-' для пропуска:")
            return
    
    await state.update_data(valid_from=valid_from.isoformat() if valid_from else None)
    
    await message.answer(
        "<b>Шаг 10/10: Дата окончания действия</b>\n\n"
        "Введите дату окончания действия промокода в формате ДД.ММ.ГГГГ\n"
        "Например: 31.12.2024\n"
        "Если без ограничения по сроку, введите '-':",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PromoCreateStates.waiting_for_valid_until)


@router.message(PromoCreateStates.waiting_for_valid_until, F.text != "❌ Отменить")
async def process_promo_valid_until(message: Message, state: FSMContext):
    """Обрабатывает дату окончания действия и сохраняет промокод (для обратной совместимости)."""
    text = message.text.strip()
    valid_until = None
    
    if text != "-":
        try:
            valid_until = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ (например, 31.12.2024) или '-' для пропуска:")
            return
    
    # Этот код теперь в callback обработчике
    data = await state.get_data()
    
    # Обрабатываем valid_from из state
    valid_from_date = None
    valid_from_str = data.get("valid_from")
    if valid_from_str:
        try:
            if isinstance(valid_from_str, str):
                valid_from_date = datetime.fromisoformat(valid_from_str).date()
            else:
                valid_from_date = valid_from_str
        except:
            pass
    
    # Проверяем даты
    if valid_from_date and valid_until:
        if valid_from_date > valid_until:
            await message.answer("❌ Дата начала не может быть позже даты окончания. Попробуйте еще раз:")
            return
    
    # Сохраняем промокод
    try:
        db = await get_db()
        
        # Преобразуем value в строку для правильной вставки в DECIMAL колонку
        value_str = str(data["value"])
        min_order_amount_str = str(data.get("min_order_amount")) if data.get("min_order_amount") else None
        
        promo_data = {
            "code": data["code"],
            "promo_type": data["promo_type"],
            "value": value_str,  # Используем строку для DECIMAL колонки
            "description": data.get("description"),
            "is_active": 1,  # SQLite использует INTEGER для boolean
            "use_once": 1 if data.get("use_once", False) else 0,
            "first_order_only": 1 if data.get("first_order_only", False) else 0,
            "shop_id": data.get("shop_id"),
            "min_order_amount": min_order_amount_str,
            "valid_from": valid_from_date.isoformat() if valid_from_date else None,
            "valid_until": valid_until.isoformat() if valid_until else None,
            "usage_count": 0
        }
        
        # Сначала проверяем структуру таблицы, чтобы определить, какие колонки есть
        promos_columns_info = await db.fetch_all("PRAGMA table_info(promos)")
        promos_column_names = [col["name"] for col in promos_columns_info]
        
        # Формируем список колонок для INSERT
        insert_columns = [
            "code", "promo_type", "value", "description", "is_active",
            "use_once", "first_order_only", "shop_id", "min_order_amount",
            "valid_from", "valid_until", "usage_count"
        ]
        
        # Если есть старые колонки discount_type и discount_value, добавляем их в запрос
        if "discount_type" in promos_column_names:
            insert_columns.append("discount_type")
        if "discount_value" in promos_column_names:
            insert_columns.append("discount_value")
        
        # Используем явный SQL запрос с правильными типами данных
        # SQLite автоматически конвертирует строки в DECIMAL для колонок типа DECIMAL
        columns_str = ", ".join(insert_columns)
        placeholders_str = ", ".join(["?" for _ in insert_columns])
        query = f"INSERT INTO promos ({columns_str}) VALUES ({placeholders_str})"
        
        # Формируем параметры
        params_list = [
            promo_data["code"],
            promo_data["promo_type"],
            promo_data["value"],  # Строка, SQLite автоматически конвертирует в DECIMAL
            promo_data.get("description"),
            promo_data["is_active"],
            promo_data["use_once"],
            promo_data["first_order_only"],
            promo_data.get("shop_id"),
            promo_data.get("min_order_amount"),
            promo_data.get("valid_from"),
            promo_data.get("valid_until"),
            promo_data["usage_count"]
        ]
        
        # Если есть discount_type, добавляем значение (используем promo_type как discount_type)
        if "discount_type" in promos_column_names:
            params_list.append(promo_data["promo_type"])  # discount_type = promo_type
        
        # Если есть discount_value, добавляем значение (используем value как discount_value)
        if "discount_value" in promos_column_names:
            params_list.append(promo_data["value"])  # discount_value = value
        
        params = tuple(params_list)
        
        cursor = await db.execute(query, params)
        await db.commit()
        promo_id = cursor.lastrowid
        await db.disconnect()
        
        # Формируем информацию о промокоде
        promo_info = f"""
<b>✅ Промокод успешно создан!</b>

<b>ID:</b> {promo_id}
<b>Код:</b> {data['code']}
<b>Тип:</b> {data['promo_type']}
<b>Значение:</b> {data['value']} {"%" if data['promo_type'] == 'percent' else "₽" if data['promo_type'] == 'fixed' else "(бесплатная доставка)"}
"""
        
        if data.get("description"):
            promo_info += f"<b>Описание:</b> {data['description']}\n"
        
        promo_info += f"\n<b>Условия:</b>\n"
        promo_info += f"• Использовать один раз: {'Да' if data.get('use_once') else 'Нет'}\n"
        promo_info += f"• Только для первого заказа: {'Да' if data.get('first_order_only') else 'Нет'}\n"
        
        if data.get("shop_id"):
            promo_info += f"• Для магазина ID: {data['shop_id']}\n"
        
        if data.get("min_order_amount"):
            promo_info += f"• Минимальная сумма заказа: {data['min_order_amount']} ₽\n"
        
        if valid_from_date:
            promo_info += f"• Действует с: {valid_from_date.strftime('%d.%m.%Y')}\n"
        
        if valid_until:
            promo_info += f"• Действует до: {valid_until.strftime('%d.%m.%Y')}\n"
        
        await message.answer(
            promo_info,
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.clear()
        
    except Exception as e:
        import traceback
        print(f"Error creating promo: {e}")
        traceback.print_exc()
        await message.answer(
            f"❌ Ошибка при создании промокода: {str(e)}\n\nПопробуйте еще раз или обратитесь в поддержку.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


async def show_promos_list(callback: CallbackQuery, bot: Bot):
    """Показывает список промокодов."""
    try:
        db = await get_db()
        
        promos = await db.fetch_all(
            "SELECT * FROM promos ORDER BY created_at DESC LIMIT 20",
            ()
        )
        
        await db.disconnect()
        
        if not promos:
            text = "<b>📋 Промокоды</b>\n\nПромокодов не найдено."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = "<b>📋 Промокоды</b>\n\n"
        
        for promo in promos[:10]:  # Показываем первые 10
            status_emoji = "✅" if promo.get("is_active", True) else "❌"
            promo_type_text = {
                "percent": "процент",
                "fixed": "фикс",
                "free_delivery": "доставка"
            }.get(promo.get("promo_type", ""), promo.get("promo_type", ""))
            
            value = promo.get("value", 0)
            if promo.get("promo_type") == "percent":
                value_text = f"{value}%"
            elif promo.get("promo_type") == "fixed":
                value_text = f"{value} ₽"
            else:
                value_text = "бесплатно"
            
            text += f"{status_emoji} <b>{promo['code']}</b> - {promo_type_text} {value_text}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="admin_back_to_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing promos list: {e}")
        await callback.answer("❌ Ошибка при загрузке списка промокодов.", show_alert=True)


@router.message(F.text == "❌ Отменить")
@router.callback_query(F.data == "promo_cancel")
async def cancel_promo_creation_callback(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание промокода через кнопку."""
    await state.clear()
    await callback.message.edit_text("❌ Создание промокода отменено.")
    await callback.answer()

async def cancel_promo_creation(message: Message, state: FSMContext):
    """Отменяет создание промокода."""
    current_state = await state.get_state()
    # Проверяем, что мы находимся в состоянии создания промокода
    if current_state and "PromoCreateStates" in str(current_state):
        await state.clear()
        await message.answer(
            "❌ Создание промокода отменено.",
            reply_markup=ReplyKeyboardRemove()
        )


async def show_promo_statistics(callback: CallbackQuery, bot: Bot):
    """Показывает статистику использования промокодов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Всего промокодов
        total_promos = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM promos"
        )
        
        # Активных промокодов
        active_promos = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM promos WHERE is_active = 1"
        )
        
        # Общее количество использований
        total_uses = await db.fetch_one(
            "SELECT COALESCE(SUM(usage_count), 0) as total FROM promos"
        )
        
        # Промокоды по типам
        promos_by_type = await db.fetch_all(
            """SELECT promo_type, COUNT(*) as cnt 
               FROM promos 
               GROUP BY promo_type"""
        )
        
        # Топ промокодов по использованию
        top_promos = await db.fetch_all(
            """SELECT code, promo_type, usage_count, current_uses
               FROM promos
               ORDER BY usage_count DESC
               LIMIT 10"""
        )
        
        await db.disconnect()
        
        stats = {
            "total_promos": total_promos["cnt"] if total_promos else 0,
            "active_promos": active_promos["cnt"] if active_promos else 0,
            "total_uses": total_uses["total"] if total_uses else 0,
            "promos_by_type": {row["promo_type"]: row["cnt"] for row in promos_by_type},
            "top_promos": [
                {
                    "code": p["code"],
                    "promo_type": p["promo_type"],
                    "usage_count": p["usage_count"] or 0,
                    "current_uses": p["current_uses"] or 0
                }
                for p in top_promos
            ]
        }
        
        text = f"""
<b>📊 Статистика промокодов</b>

<b>Общая статистика:</b>
🎫 Всего промокодов: {stats.get('total_promos', 0)}
✅ Активных: {stats.get('active_promos', 0)}
📈 Всего использований: {stats.get('total_uses', 0)}

<b>Промокоды по типам:</b>
"""
        
        promos_by_type = stats.get('promos_by_type', {})
        type_names = {
            "percent": "Процентные",
            "fixed": "Фиксированные",
            "free_delivery": "Бесплатная доставка"
        }
        
        for promo_type, count in promos_by_type.items():
            type_name = type_names.get(promo_type, promo_type)
            text += f"• {type_name}: {count}\n"
        
        text += "\n<b>Топ промокодов по использованию:</b>\n"
        
        top_promos = stats.get('top_promos', [])
        for idx, promo in enumerate(top_promos[:5], 1):
            text += f"{idx}. <b>{promo.get('code', 'N/A')}</b> ({promo.get('promo_type', 'N/A')})\n"
            text += f"   Использований: {promo.get('usage_count', 0)}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promos_menu")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing promo statistics: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке статистики промокодов.", show_alert=True)


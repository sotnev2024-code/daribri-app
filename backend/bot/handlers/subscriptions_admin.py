"""
Обработчик управления планами подписки в админ-панели бота.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decimal import Decimal
import json
import httpx
from backend.app.config import settings

router = Router()


class SubscriptionPlanCreateStates(StatesGroup):
    """Состояния для создания плана подписки."""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_duration_days = State()
    waiting_for_max_products = State()


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    from backend.app.config import settings
    
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


def get_cancel_keyboard():
    """Возвращает клавиатуру с кнопкой отмены."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_subscriptions")]
    ])


async def show_subscription_plans_list(callback: CallbackQuery, bot: Bot):
    """Показывает список планов подписки."""
    try:
        db = await get_db()
        
        # Получаем все планы подписки
        plans = await db.fetch_all(
            "SELECT * FROM subscription_plans ORDER BY price ASC, created_at DESC"
        )
        
        await db.disconnect()
        
        if not plans:
            text = "<b>💳 Планы подписки</b>\n\nПланы подписки отсутствуют.\n\nСоздайте новый план подписки:"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать план", callback_data="admin_create_subscription")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
            ])
        else:
            text = "<b>💳 Планы подписки</b>\n\n"
            buttons = []
            
            for plan in plans:
                status = "✅" if plan.get("is_active", 1) else "❌"
                price = Decimal(str(plan.get("price", 0)))
                duration = plan.get("duration_days", 0)
                max_products = plan.get("max_products", 0)
                
                plan_text = f"{status} <b>{plan.get('name', 'Без названия')}</b>\n"
                plan_text += f"💰 Цена: {price:.2f} ₽\n"
                plan_text += f"📅 Длительность: {duration} дней\n"
                plan_text += f"📦 Макс. товаров: {max_products}\n"
                
                if plan.get("description"):
                    desc = plan.get("description", "")[:50]
                    if len(plan.get("description", "")) > 50:
                        desc += "..."
                    plan_text += f"📝 {desc}\n"
                
                plan_text += "\n"
                text += plan_text
                
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{'✅' if plan.get('is_active', 1) else '❌'} {plan.get('name', 'Без названия')}",
                        callback_data=f"admin_view_subscription_{plan['id']}"
                    )
                ])
            
            buttons.append([InlineKeyboardButton(text="➕ Создать план", callback_data="admin_create_subscription")])
            buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        print(f"Error showing subscription plans: {e}")
        import traceback
        traceback.print_exc()
        if callback.message:
            try:
                await callback.message.answer("❌ Ошибка при загрузке планов подписки.")
            except:
                pass
        if hasattr(callback, 'answer'):
            try:
                await callback.answer("❌ Ошибка при загрузке планов подписки.", show_alert=True)
            except:
                pass


async def show_subscription_plan_details(callback: CallbackQuery, bot: Bot, plan_id: int):
    """Показывает детали плана подписки."""
    try:
        db = await get_db()
        
        plan = await db.fetch_one(
            "SELECT * FROM subscription_plans WHERE id = ?",
            (plan_id,)
        )
        
        await db.disconnect()
        
        if not plan:
            await callback.answer("❌ План не найден.", show_alert=True)
            return
        
        status = "✅ Активен" if plan.get("is_active", 1) else "❌ Неактивен"
        price = Decimal(str(plan.get("price", 0)))
        duration = plan.get("duration_days", 0)
        max_products = plan.get("max_products", 0)
        
        text = f"<b>💳 План подписки</b>\n\n"
        text += f"<b>Название:</b> {plan.get('name', 'Без названия')}\n"
        text += f"<b>Статус:</b> {status}\n"
        text += f"<b>Цена:</b> {price:.2f} ₽\n"
        text += f"<b>Длительность:</b> {duration} дней\n"
        text += f"<b>Макс. товаров:</b> {max_products}\n"
        
        if plan.get("description"):
            text += f"<b>Описание:</b>\n{plan.get('description')}\n"
        
        features = plan.get("features")
        if features:
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = {}
            if features:
                text += f"\n<b>Дополнительные функции:</b>\n"
                for key, value in features.items():
                    text += f"• {key}: {value}\n"
        
        created_at = plan.get("created_at", "")
        if created_at:
            text += f"\n📅 Создан: {created_at[:10]}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Активировать" if not plan.get("is_active", 1) else "❌ Деактивировать",
                    callback_data=f"admin_toggle_subscription_{plan_id}"
                ),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_edit_subscription_{plan_id}")
            ],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_delete_subscription_{plan_id}")],
            [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_subscriptions")]
        ])
        
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        print(f"Error showing subscription plan details: {e}")
        import traceback
        traceback.print_exc()
        if callback.message:
            try:
                await callback.message.answer("❌ Ошибка при загрузке плана подписки.")
            except:
                pass
        if hasattr(callback, 'answer'):
            try:
                await callback.answer("❌ Ошибка при загрузке плана подписки.", show_alert=True)
            except:
                pass


async def start_create_subscription_plan(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начинает создание нового плана подписки."""
    await state.clear()
    await state.set_state(SubscriptionPlanCreateStates.waiting_for_name)
    
    text = "<b>💳 Создание плана подписки</b>\n\n"
    text += "Шаг 1/5: Введите название плана подписки:\n"
    text += "Например: Базовый, Премиум, Про"
    
    keyboard = get_cancel_keyboard()
    
    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.answer(text, reply_markup=keyboard)


async def process_plan_name(message: Message, state: FSMContext):
    """Обрабатывает название плана подписки."""
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer(
            "❌ Название должно быть от 2 до 100 символов. Попробуйте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    is_edit = data.get("edit_mode", False)
    current_desc = data.get("current_description", "") if is_edit else None
    
    await state.update_data(name=name)
    await state.set_state(SubscriptionPlanCreateStates.waiting_for_description)
    
    desc_text = "Шаг 2/5: Введите описание плана подписки"
    if is_edit and current_desc:
        desc_text += f"\nТекущее: {current_desc}"
    desc_text += "\n(или отправьте \"-\" чтобы пропустить/оставить без изменений):"
    
    await message.answer(desc_text, reply_markup=get_cancel_keyboard())


async def process_plan_description(message: Message, state: FSMContext):
    """Обрабатывает описание плана подписки."""
    data = await state.get_data()
    is_edit = data.get("edit_mode", False)
    
    if message.text.strip() == "-":
        # Если "-", то при редактировании оставляем старое значение, при создании - None
        description = data.get("current_description") if is_edit else None
    else:
        description = message.text.strip()
    
    await state.update_data(description=description)
    await state.set_state(SubscriptionPlanCreateStates.waiting_for_price)
    
    price_text = "Шаг 3/5: Введите цену плана подписки в рублях:\n"
    if is_edit and data.get("current_price"):
        price_text += f"Текущая: {data.get('current_price')} ₽\n"
    price_text += "Например: 99"
    
    await message.answer(price_text, reply_markup=get_cancel_keyboard())


async def process_plan_price(message: Message, state: FSMContext):
    """Обрабатывает цену плана подписки."""
    try:
        price = Decimal(message.text.strip().replace(",", "."))
        if price < 0:
            raise ValueError("Цена не может быть отрицательной")
        
        # Сохраняем цену в рублях (в базе хранится в рублях)
        await state.update_data(price=float(price))
        await state.set_state(SubscriptionPlanCreateStates.waiting_for_duration_days)
        
        data = await state.get_data()
        is_edit = data.get("edit_mode", False)
        
        duration_text = "Шаг 4/5: Введите длительность подписки в днях:\n"
        if is_edit and data.get("current_duration_days"):
            duration_text += f"Текущая: {data.get('current_duration_days')} дней\n"
        duration_text += "Например: 30 (1 месяц), 90 (3 месяца), 365 (1 год)"
        
        await message.answer(duration_text, reply_markup=get_cancel_keyboard())
    except (ValueError, Exception) as e:
        await message.answer(
            f"❌ Неверный формат цены. Введите число (например: 99 или 9900):\n{str(e)}",
            reply_markup=get_cancel_keyboard()
        )


async def process_plan_duration(message: Message, state: FSMContext):
    """Обрабатывает длительность плана подписки."""
    try:
        duration_days = int(message.text.strip())
        if duration_days < 1:
            raise ValueError("Длительность должна быть больше 0")
        
        await state.update_data(duration_days=duration_days)
        await state.set_state(SubscriptionPlanCreateStates.waiting_for_max_products)
        
        data = await state.get_data()
        is_edit = data.get("edit_mode", False)
        
        max_products_text = "Шаг 5/5: Введите максимальное количество товаров для этого плана:\n"
        if is_edit and data.get("current_max_products"):
            max_products_text += f"Текущее: {data.get('current_max_products')}\n"
        max_products_text += "Например: 50, 100, 200"
        
        await message.answer(max_products_text, reply_markup=get_cancel_keyboard())
    except (ValueError, Exception) as e:
        await message.answer(
            f"❌ Неверный формат. Введите целое число дней (например: 30):\n{str(e)}",
            reply_markup=get_cancel_keyboard()
        )


async def process_plan_max_products(message: Message, state: FSMContext):
    """Обрабатывает максимальное количество товаров и завершает создание плана."""
    from .admin import SubscriptionPlanCreateStates
    
    try:
        max_products = int(message.text.strip())
        if max_products < 1:
            raise ValueError("Количество товаров должно быть больше 0")
        
        data = await state.get_data()
        
        # Создаем план подписки через API или напрямую в БД
        try:
            db = await get_db()
            
            plan_data = {
                "name": data.get("name"),
                "description": data.get("description"),
                "price": data.get("price"),
                "duration_days": data.get("duration_days"),
                "max_products": max_products,
                "features": json.dumps({}),  # Пустые функции по умолчанию
                "is_active": 1
            }
            
            plan_id = await db.insert("subscription_plans", plan_data)
            await db.commit()
            await db.disconnect()
            
            await message.answer(
                "✅ План подписки успешно создан!",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Показываем список планов через кнопку
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 К списку планов", callback_data="admin_subscriptions")]
            ])
            await message.answer("Нажмите кнопку ниже, чтобы вернуться к списку планов:", reply_markup=keyboard)
            
        except Exception as e:
            print(f"Error creating subscription plan: {e}")
            import traceback
            traceback.print_exc()
            await message.answer(
                f"❌ Ошибка при создании плана подписки: {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        
        await state.clear()
        
    except (ValueError, Exception) as e:
        await message.answer(
            f"❌ Неверный формат. Введите целое число (например: 50):\n{str(e)}",
            reply_markup=get_cancel_keyboard()
        )


async def cancel_subscription_creation(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание плана подписки."""
    await state.clear()
    await show_subscription_plans_list(callback, None)
    await callback.answer("❌ Создание плана отменено")


async def delete_subscription_plan(callback: CallbackQuery, bot: Bot, plan_id: int):
    """Удаляет план подписки."""
    try:
        db = await get_db()
        
        # Проверяем, используется ли план
        usage = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM shop_subscriptions WHERE plan_id = ?",
            (plan_id,)
        )
        
        if usage and usage.get("cnt", 0) > 0:
            await callback.answer(
                f"❌ Невозможно удалить план: он используется в {usage['cnt']} подписках.\n"
                "Сначала деактивируйте план.",
                show_alert=True
            )
            await db.disconnect()
            return
        
        await db.execute(
            "DELETE FROM subscription_plans WHERE id = ?",
            (plan_id,)
        )
        await db.commit()
        await db.disconnect()
        
        await callback.answer("✅ План подписки удален", show_alert=True)
        await show_subscription_plans_list(callback, bot)
        
    except Exception as e:
        print(f"Error deleting subscription plan: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при удалении плана подписки.", show_alert=True)


async def toggle_subscription_plan(callback: CallbackQuery, bot: Bot, plan_id: int):
    """Переключает статус активности плана подписки."""
    try:
        db = await get_db()
        
        plan = await db.fetch_one(
            "SELECT is_active FROM subscription_plans WHERE id = ?",
            (plan_id,)
        )
        
        if not plan:
            await callback.answer("❌ План не найден.", show_alert=True)
            await db.disconnect()
            return
        
        new_status = 0 if plan.get("is_active", 1) else 1
        
        await db.update(
            "subscription_plans",
            {"is_active": new_status},
            "id = ?",
            (plan_id,)
        )
        await db.commit()
        await db.disconnect()
        
        status_text = "активирован" if new_status else "деактивирован"
        await callback.answer(f"✅ План подписки {status_text}", show_alert=True)
        await show_subscription_plan_details(callback, bot, plan_id)
        
    except Exception as e:
        print(f"Error toggling subscription plan: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при изменении статуса плана.", show_alert=True)


async def start_edit_subscription_plan(callback: CallbackQuery, bot: Bot, state: FSMContext, plan_id: int):
    """Начинает редактирование плана подписки."""
    try:
        db = await get_db()
        
        plan = await db.fetch_one(
            "SELECT * FROM subscription_plans WHERE id = ?",
            (plan_id,)
        )
        
        await db.disconnect()
        
        if not plan:
            await callback.answer("❌ План не найден.", show_alert=True)
            return
        
        await state.update_data(
            plan_id=plan_id,
            edit_mode=True,
            current_name=plan.get('name'),
            current_description=plan.get('description'),
            current_price=plan.get('price'),
            current_duration_days=plan.get('duration_days'),
            current_max_products=plan.get('max_products')
        )
        await state.set_state(SubscriptionPlanCreateStates.waiting_for_name)
        
        text = "<b>✏️ Редактирование плана подписки</b>\n\n"
        text += "Шаг 1/5: Введите новое название плана:\n"
        text += f"Текущее: {plan.get('name', 'Без названия')}"
        
        keyboard = get_cancel_keyboard()
        
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        print(f"Error starting edit subscription plan: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при начале редактирования.", show_alert=True)


# Регистрация обработчиков
@router.callback_query(F.data.startswith("admin_view_subscription_"))
async def handle_view_subscription(callback: CallbackQuery, bot: Bot):
    """Обрабатывает просмотр деталей плана подписки."""
    plan_id = int(callback.data.split("_")[3])
    await show_subscription_plan_details(callback, bot, plan_id)
    await callback.answer()


@router.message(SubscriptionPlanCreateStates.waiting_for_name)
async def handle_plan_name(message: Message, state: FSMContext):
    """Обрабатывает ввод названия плана."""
    await process_plan_name(message, state)


@router.message(SubscriptionPlanCreateStates.waiting_for_description)
async def handle_plan_description(message: Message, state: FSMContext):
    """Обрабатывает ввод описания плана."""
    await process_plan_description(message, state)


@router.message(SubscriptionPlanCreateStates.waiting_for_price)
async def handle_plan_price(message: Message, state: FSMContext):
    """Обрабатывает ввод цены плана."""
    await process_plan_price(message, state)


@router.message(SubscriptionPlanCreateStates.waiting_for_duration_days)
async def handle_plan_duration(message: Message, state: FSMContext):
    """Обрабатывает ввод длительности плана."""
    await process_plan_duration(message, state)


@router.message(SubscriptionPlanCreateStates.waiting_for_max_products)
async def handle_plan_max_products(message: Message, state: FSMContext):
    """Обрабатывает ввод максимального количества товаров."""
    data = await state.get_data()
    if data.get("edit_mode"):
        # Режим редактирования
        await process_plan_max_products_edit(message, state)
    else:
        # Режим создания
        await process_plan_max_products(message, state)


async def process_plan_max_products_edit(message: Message, state: FSMContext):
    """Обрабатывает максимальное количество товаров и завершает редактирование плана."""
    try:
        max_products = int(message.text.strip())
        if max_products < 1:
            raise ValueError("Количество товаров должно быть больше 0")
        
        data = await state.get_data()
        plan_id = data.get("plan_id")
        
        if not plan_id:
            await message.answer("❌ Ошибка: ID плана не найден", reply_markup=ReplyKeyboardRemove())
            await state.clear()
            return
        
        # Обновляем план подписки
        try:
            db = await get_db()
            
            # Используем новые данные или оставляем старые, если не были изменены
            update_data = {}
            if "name" in data:
                update_data["name"] = data.get("name")
            else:
                update_data["name"] = data.get("current_name")
                
            if "description" in data:
                update_data["description"] = data.get("description")
            else:
                update_data["description"] = data.get("current_description")
                
            if "price" in data:
                update_data["price"] = data.get("price")
            else:
                update_data["price"] = data.get("current_price")
                
            if "duration_days" in data:
                update_data["duration_days"] = data.get("duration_days")
            else:
                update_data["duration_days"] = data.get("current_duration_days")
                
            update_data["max_products"] = max_products
                
            await db.update(
                "subscription_plans",
                update_data,
                "id = ?",
                (plan_id,)
            )
            await db.commit()
            await db.disconnect()
            
            await message.answer(
                "✅ План подписки успешно обновлен!",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Показываем список планов через кнопку
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 К списку планов", callback_data="admin_subscriptions")]
            ])
            await message.answer("Нажмите кнопку ниже, чтобы вернуться к списку планов:", reply_markup=keyboard)
            
        except Exception as e:
            print(f"Error updating subscription plan: {e}")
            import traceback
            traceback.print_exc()
            await message.answer(
                f"❌ Ошибка при обновлении плана подписки: {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        
        await state.clear()
        
    except (ValueError, Exception) as e:
        await message.answer(
            f"❌ Неверный формат. Введите целое число (например: 50):\n{str(e)}",
            reply_markup=get_cancel_keyboard()
        )


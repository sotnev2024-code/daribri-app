"""
Обработчик команды /подписка для покупки подписки на магазин.
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
import uuid

router = Router()


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    from backend.app.config import settings
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


@router.message(Command("подписка"))
@router.message(Command("subscription"))
@router.message(Command("subscribe"))
async def cmd_subscription(message: Message, bot: Bot):
    """Команда для управления подпиской - продление или изменение плана."""
    try:
        db = await get_db()
        
        # Получаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        
        if not user:
            await message.answer(
                "❌ Пользователь не найден. Пожалуйста, сначала используйте команду /start."
            )
            await db.disconnect()
            return
        
        user_id = user["id"]
        
        # Проверяем, есть ли у пользователя магазин
        shop = await db.fetch_one(
            "SELECT id, name FROM shops WHERE owner_id = ?",
            (user_id,)
        )
        
        if not shop:
            await db.disconnect()
            await message.answer(
                "❌ У вас нет магазина.\n\n"
                "Чтобы создать магазин, используйте команду /add_shop и дождитесь одобрения заявки."
            )
            return
        
        shop_id = shop["id"]
        shop_name = shop["name"]
        
        # Проверяем, есть ли уже активная подписка
        active_subscription = await db.fetch_one(
            """SELECT ss.*, sp.name as plan_name, sp.duration_days, sp.price
               FROM shop_subscriptions ss
               JOIN subscription_plans sp ON ss.plan_id = sp.id
               WHERE ss.shop_id = ? AND ss.is_active = 1 AND ss.end_date > datetime('now')
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        await db.disconnect()
        
        # Формируем текст и клавиатуру
        from datetime import datetime
        
        if active_subscription:
            end_date = datetime.fromisoformat(active_subscription["end_date"].replace("Z", "+00:00"))
            end_date_str = end_date.strftime("%d.%m.%Y")
            
            text = f"""
<b>💳 Управление подпиской</b>

<b>Ваш магазин:</b> 🏪 {shop_name}

<b>Текущая подписка:</b>
📦 План: {active_subscription['plan_name']}
📅 Действует до: {end_date_str}

<b>Что вы хотите сделать?</b>
"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Продлить подписку",
                    callback_data=f"subscribe_extend_{active_subscription['plan_id']}"
                )],
                [InlineKeyboardButton(
                    text="📝 Изменить план",
                    callback_data="subscribe_change_plan"
                )]
            ])
        else:
            text = f"""
<b>💳 Управление подпиской</b>

<b>Ваш магазин:</b> 🏪 {shop_name}

❌ У вас нет активной подписки.

<b>Что вы хотите сделать?</b>
"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📝 Выбрать план подписки",
                    callback_data="subscribe_change_plan"
                )]
            ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"Error in cmd_subscription: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.pre_checkout_query(F.invoice_payload.startswith("subscription_direct_") | F.invoice_payload.startswith("subscription_plan_"))
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery, bot: Bot):
    """Обрабатывает запрос перед оплатой подписки."""
    # Все в порядке, подтверждаем платеж
    await bot.answer_pre_checkout_query(pre_checkout.id, ok=True)


@router.message(F.successful_payment.invoice_payload.startswith("subscription_direct_"))
async def successful_payment_handler_direct(message: Message, bot: Bot):
    """Обрабатывает успешную оплату базовой подписки (старый формат - для совместимости)."""
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    try:
        # Извлекаем shop_id из payload
        # Формат: subscription_direct_{shop_id}_{uuid}
        parts = payload.split("_")
        if len(parts) >= 3:
            shop_id = int(parts[2])
            
            db = await get_db()
            
            # Проверяем, что магазин существует и принадлежит пользователю
            shop = await db.fetch_one(
                "SELECT id, name, owner_id FROM shops WHERE id = ?",
                (shop_id,)
            )
            
            if not shop:
                await message.answer("❌ Магазин не найден. Обратитесь в поддержку.")
                await db.disconnect()
                return
            
            # Проверяем владельца магазина
            user = await db.fetch_one(
                "SELECT id FROM users WHERE telegram_id = ?",
                (message.from_user.id,)
            )
            
            if not user or user["id"] != shop["owner_id"]:
                await message.answer("❌ У вас нет прав на этот магазин. Обратитесь в поддержку.")
                await db.disconnect()
                return
            
            # Получаем или создаем план подписки на 1 месяц (30 дней)
            plan = await db.fetch_one(
                "SELECT id FROM subscription_plans WHERE duration_days = 30 AND is_active = 1 LIMIT 1",
                ()
            )
            
            if not plan:
                # Создаем план подписки на 1 месяц (30 дней)
                plan_id = await db.insert("subscription_plans", {
                    "name": "Базовый план",
                    "description": "Подписка на 1 месяц",
                    "price": 99.0,
                    "duration_days": 30,
                    "max_products": 50,
                    "is_active": True,
                    "features": "{}"
                })
            else:
                plan_id = plan["id"]
            
            # Деактивируем старые подписки
            await db.update(
                "shop_subscriptions",
                {"is_active": False},
                "shop_id = ?",
                (shop_id,)
            )
            
            # Создаем подписку
            from datetime import datetime, timedelta
            
            plan_info = await db.fetch_one("SELECT * FROM subscription_plans WHERE id = ?", (plan_id,))
            start_date = datetime.now()
            end_date = start_date + timedelta(days=plan_info["duration_days"])
            
            subscription_id = await db.insert("shop_subscriptions", {
                "shop_id": shop_id,
                "plan_id": plan_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "is_active": True,
                "payment_id": payment.telegram_payment_charge_id or f"pay_{datetime.now().timestamp()}"
            })
            
            await db.commit()
            
            # Активируем товары магазина при активации подписки
            from backend.app.services.subscription_manager import SubscriptionManager
            activated = await SubscriptionManager.activate_shop_products(db, shop_id)
            if activated > 0:
                print(f"[SUBSCRIPTION] Activated {activated} products for shop {shop_id}")
            
            await db.disconnect()
            
            # Отправляем подтверждение
            success_text = f"""
<b>✅ Оплата успешно завершена!</b>

<b>Ваш магазин:</b>
🏪 {shop['name']}

<b>Подписка активирована на {plan_info['duration_days']} дней!</b>
📅 Действует до: {end_date.strftime('%d.%m.%Y')}

Теперь вы можете:
✨ Добавлять товары
📊 Управлять заказами
📈 Отслеживать статистику

Откройте каталог и начните продавать! 🚀
"""
            await message.answer(success_text)
            
    except Exception as e:
        print(f"Error processing successful payment: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Произошла ошибка при обработке платежа. Пожалуйста, свяжитесь с поддержкой.")


@router.message(F.successful_payment.invoice_payload.startswith("subscription_plan_"))
async def successful_payment_handler_plan(message: Message, bot: Bot):
    """Обрабатывает успешную оплату подписки с указанным планом."""
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    try:
        print(f"[SUBSCRIPTION] Processing payment, payload: {payload}")
        # Извлекаем plan_id и shop_id из payload
        # Формат: subscription_plan_{plan_id}_{shop_id}_{uuid}
        # После split("_") получаем: ["subscription", "plan", "{plan_id}", "{shop_id}", "{uuid}", ...]
        
        if not payload.startswith("subscription_plan_"):
            await message.answer("❌ Неверный формат платежа. Обратитесь в поддержку.")
            print(f"[SUBSCRIPTION] Invalid payload prefix: {payload}")
            return
        
        # Убираем префикс "subscription_plan_" и разбиваем оставшуюся часть
        payload_without_prefix = payload.replace("subscription_plan_", "", 1)
        parts = payload_without_prefix.split("_")
        print(f"[SUBSCRIPTION] Payload without prefix: {payload_without_prefix}, parts: {parts}")
        
        if len(parts) < 2:
            await message.answer("❌ Неверный формат платежа. Обратитесь в поддержку.")
            print(f"[SUBSCRIPTION] Invalid payload format: {payload}, parts count: {len(parts)}")
            return
        
        # parts[0] = plan_id, parts[1] = shop_id, parts[2] = uuid (опционально)
        try:
            plan_id = int(parts[0])
            shop_id = int(parts[1])
            print(f"[SUBSCRIPTION] Parsed plan_id={plan_id}, shop_id={shop_id}")
        except (ValueError, IndexError) as parse_error:
            await message.answer("❌ Ошибка обработки платежа. Обратитесь в поддержку.")
            print(f"[SUBSCRIPTION] Error parsing payload: {parse_error}, payload: {payload}, parts: {parts}")
            import traceback
            traceback.print_exc()
            return
        
        db = await get_db()
        
        # Проверяем план
        plan = await db.fetch_one(
            "SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1",
            (plan_id,)
        )
        
        if not plan:
            await message.answer("❌ План подписки не найден. Обратитесь в поддержку.")
            await db.disconnect()
            return
        
        # Проверяем, что магазин существует и принадлежит пользователю
        shop = await db.fetch_one(
            "SELECT id, name, owner_id FROM shops WHERE id = ?",
            (shop_id,)
        )
        
        if not shop:
            await message.answer("❌ Магазин не найден. Обратитесь в поддержку.")
            await db.disconnect()
            return
        
        # Проверяем владельца магазина
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        
        if not user or user["id"] != shop["owner_id"]:
            await message.answer("❌ У вас нет прав на этот магазин. Обратитесь в поддержку.")
            await db.disconnect()
            return
        
        # Проверяем, есть ли активная подписка для продления
        current_subscription = await db.fetch_one(
            """SELECT * FROM shop_subscriptions 
               WHERE shop_id = ? AND is_active = 1 AND end_date > datetime('now')
               ORDER BY end_date DESC LIMIT 1""",
            (shop_id,)
        )
        
        # Деактивируем старые подписки
        await db.update(
            "shop_subscriptions",
            {"is_active": False},
            "shop_id = ?",
            (shop_id,)
        )
        
        # Создаем подписку (новую или продление)
        from datetime import datetime, timedelta
        
        if current_subscription:
            # Продление: начинаем с даты окончания текущей подписки
            current_end_date = datetime.fromisoformat(current_subscription["end_date"].replace("Z", "+00:00"))
            now = datetime.now(current_end_date.tzinfo)
            start_date = current_end_date if current_end_date > now else now
        else:
            # Новая подписка: начинаем с текущей даты
            start_date = datetime.now()
        
        end_date = start_date + timedelta(days=plan["duration_days"])
        
        subscription_id = await db.insert("shop_subscriptions", {
            "shop_id": shop_id,
            "plan_id": plan_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "is_active": True,
            "payment_id": payment.telegram_payment_charge_id or f"pay_{datetime.now().timestamp()}"
        })
        
        await db.commit()
        
        # Активируем товары магазина при активации подписки
        from backend.app.services.subscription_manager import SubscriptionManager
        activated = await SubscriptionManager.activate_shop_products(db, shop_id)
        if activated > 0:
            print(f"[SUBSCRIPTION] Activated {activated} products for shop {shop_id}")
        
        await db.disconnect()
        
        # Отправляем подтверждение
        duration_text = f"{plan['duration_days']} {plan['duration_days'] == 1 and 'день' or (plan['duration_days'] < 5 and 'дня' or 'дней')}"
        success_text = f"""
<b>✅ Оплата успешно завершена!</b>

<b>Ваш магазин:</b>
🏪 {shop['name']}

<b>План:</b> {plan['name']}
<b>Подписка активирована на {duration_text}!</b>
📅 Действует до: {end_date.strftime('%d.%m.%Y')}

<b>Возможности плана:</b>
📦 До {plan['max_products']} товаров
{plan.get('description', '')}

Теперь вы можете:
✨ Добавлять товары
📊 Управлять заказами
📈 Отслеживать статистику

Откройте каталог и начните продавать! 🚀
"""
        await message.answer(success_text)
            
    except Exception as e:
        print(f"Error processing successful payment: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Произошла ошибка при обработке платежа. Пожалуйста, свяжитесь с поддержкой.")


# ===== CALLBACK ОБРАБОТЧИКИ ДЛЯ КНОПОК =====

@router.callback_query(F.data.startswith("subscribe_extend_"))
async def callback_extend_subscription(callback: CallbackQuery, bot: Bot):
    """Обработчик продления подписки."""
    try:
        plan_id = int(callback.data.split("_")[-1])
        print(f"[SUBSCRIBE] Extend subscription callback, plan_id={plan_id}, user_id={callback.from_user.id}")
        
        db = await get_db()
        
        # Получаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (callback.from_user.id,)
        )
        
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            await db.disconnect()
            return
        
        user_id = user["id"]
        
        # Проверяем магазин
        shop = await db.fetch_one(
            "SELECT id, name FROM shops WHERE owner_id = ?",
            (user_id,)
        )
        
        if not shop:
            await callback.answer("❌ У вас нет магазина.", show_alert=True)
            await db.disconnect()
            return
        
        shop_id = shop["id"]
        shop_name = shop["name"]
        
        # Получаем план
        plan = await db.fetch_one(
            "SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1",
            (plan_id,)
        )
        
        if not plan:
            await callback.answer("❌ План подписки не найден.", show_alert=True)
            await db.disconnect()
            return
        
        # Получаем текущую подписку для расчета новой даты окончания
        current_subscription = await db.fetch_one(
            """SELECT * FROM shop_subscriptions 
               WHERE shop_id = ? AND is_active = 1 AND end_date > datetime('now')
               ORDER BY end_date DESC LIMIT 1""",
            (shop_id,)
        )
        
        await db.disconnect()
        
        # Проверяем настройки YooKassa
        from backend.app.config import settings
        import os
        
        yookassa_token = os.getenv("API_KEY_YOOKASSA", "") or getattr(settings, "API_KEY_YOOKASSA", "")
        
        if not yookassa_token:
            await callback.answer("❌ Платежная система не настроена.", show_alert=True)
            return
        
        # Рассчитываем новую дату окончания
        from datetime import datetime, timedelta
        
        if current_subscription:
            # Продление: начинаем с даты окончания текущей подписки
            current_end_date = datetime.fromisoformat(current_subscription["end_date"].replace("Z", "+00:00"))
            now = datetime.now(current_end_date.tzinfo)
            start_date = current_end_date if current_end_date > now else now
            new_end_date = start_date + timedelta(days=plan["duration_days"])
            new_end_date_str = new_end_date.strftime("%d.%m.%Y")
        else:
            new_end_date = datetime.now() + timedelta(days=plan["duration_days"])
            new_end_date_str = new_end_date.strftime("%d.%m.%Y")
        
        # Создаем invoice для оплаты
        invoice_payload = f"subscription_plan_{plan_id}_{shop_id}_{uuid.uuid4().hex[:8]}"
        
        # Цена в копейках
        price_rub = float(plan["price"])
        price_kopecks = int(price_rub * 100)
        
        prices = [LabeledPrice(label=f"Продление: {plan['name']}", amount=price_kopecks)]
        
        # Формируем описание
        duration_text = f"{plan['duration_days']} {plan['duration_days'] == 1 and 'день' or (plan['duration_days'] < 5 and 'дня' or 'дней')}"
        description = f"Продление подписки для магазина \"{shop_name}\"\n\n"
        description += f"План: {plan['name']}\n"
        description += f"Продление на: {duration_text}\n"
        description += f"Новая дата окончания: {new_end_date_str}\n"
        description += f"Макс. товаров: {plan['max_products']}\n"
        if plan.get('description'):
            description += f"\n{plan['description']}"
        
        try:
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title=f"Продление подписки: {plan['name']}",
                description=description,
                payload=invoice_payload,
                provider_token=yookassa_token,
                currency="RUB",
                prices=prices,
                start_parameter=f"subscription_extend_{plan_id}"
            )
            await callback.answer("✅ Счет на оплату отправлен в чат!")
        except Exception as invoice_error:
            print(f"Error sending invoice: {invoice_error}")
            import traceback
            traceback.print_exc()
            await callback.answer("❌ Ошибка при создании платежа. Попробуйте позже.", show_alert=True)
            
    except Exception as e:
        print(f"Error in callback_extend_subscription: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "subscribe_change_plan")
async def callback_change_plan(callback: CallbackQuery, bot: Bot):
    """Обработчик изменения плана - показывает список доступных планов."""
    try:
        print(f"[SUBSCRIBE] Change plan callback, user_id={callback.from_user.id}")
        db = await get_db()
        
        # Получаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (callback.from_user.id,)
        )
        
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            await db.disconnect()
            return
        
        user_id = user["id"]
        
        # Проверяем магазин
        shop = await db.fetch_one(
            "SELECT id, name FROM shops WHERE owner_id = ?",
            (user_id,)
        )
        
        if not shop:
            await callback.answer("❌ У вас нет магазина.", show_alert=True)
            await db.disconnect()
            return
        
        # Получаем список активных планов
        plans = await db.fetch_all(
            "SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY price ASC"
        )
        
        await db.disconnect()
        
        if not plans:
            await callback.answer("❌ Нет доступных планов подписки.", show_alert=True)
            return
        
        # Формируем текст и клавиатуру
        text = "<b>📝 Выберите план подписки</b>\n\n"
        
        keyboard_buttons = []
        for plan in plans:
            duration_text = f"{plan['duration_days']} {plan['duration_days'] == 1 and 'день' or (plan['duration_days'] < 5 and 'дня' or 'дней')}"
            price_text = f"{plan['price']:.0f}" if plan['price'] % 1 == 0 else f"{plan['price']:.2f}"
            
            plan_text = f"<b>{plan['name']}</b> - {price_text} ₽\n"
            plan_text += f"📅 {duration_text} | 📦 До {plan['max_products']} товаров\n"
            if plan.get('description'):
                plan_text += f"{plan['description']}\n"
            plan_text += "\n"
            
            text += plan_text
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{plan['name']} - {price_text} ₽",
                    callback_data=f"subscribe_select_plan_{plan['id']}"
                )
            ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="subscribe_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
        except Exception as edit_error:
            print(f"Error editing message: {edit_error}")
            await callback.message.answer(text, reply_markup=keyboard)
            await callback.answer()
        
    except Exception as e:
        print(f"Error in callback_change_plan: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("subscribe_select_plan_"))
async def callback_select_plan(callback: CallbackQuery, bot: Bot):
    """Обработчик выбора плана - отправляет invoice для оплаты."""
    try:
        plan_id = int(callback.data.split("_")[-1])
        print(f"[SUBSCRIBE] Select plan callback, plan_id={plan_id}, user_id={callback.from_user.id}")
        
        db = await get_db()
        
        # Получаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (callback.from_user.id,)
        )
        
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            await db.disconnect()
            return
        
        user_id = user["id"]
        
        # Проверяем магазин
        shop = await db.fetch_one(
            "SELECT id, name FROM shops WHERE owner_id = ?",
            (user_id,)
        )
        
        if not shop:
            await callback.answer("❌ У вас нет магазина.", show_alert=True)
            await db.disconnect()
            return
        
        shop_id = shop["id"]
        shop_name = shop["name"]
        
        # Получаем план
        plan = await db.fetch_one(
            "SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1",
            (plan_id,)
        )
        
        await db.disconnect()
        
        if not plan:
            await callback.answer("❌ План подписки не найден.", show_alert=True)
            return
        
        # Проверяем настройки YooKassa
        from backend.app.config import settings
        import os
        
        yookassa_token = os.getenv("API_KEY_YOOKASSA", "") or getattr(settings, "API_KEY_YOOKASSA", "")
        
        if not yookassa_token:
            await callback.answer("❌ Платежная система не настроена.", show_alert=True)
            return
        
        # Создаем invoice для оплаты
        invoice_payload = f"subscription_plan_{plan_id}_{shop_id}_{uuid.uuid4().hex[:8]}"
        
        # Цена в копейках
        price_rub = float(plan["price"])
        price_kopecks = int(price_rub * 100)
        
        prices = [LabeledPrice(label=f"Подписка: {plan['name']}", amount=price_kopecks)]
        
        # Формируем описание
        from datetime import datetime, timedelta
        duration_text = f"{plan['duration_days']} {plan['duration_days'] == 1 and 'день' or (plan['duration_days'] < 5 and 'дня' or 'дней')}"
        start_date = datetime.now()
        end_date = start_date + timedelta(days=plan["duration_days"])
        
        description = f"Подписка для магазина \"{shop_name}\"\n\n"
        description += f"План: {plan['name']}\n"
        description += f"Длительность: {duration_text}\n"
        description += f"Дата окончания: {end_date.strftime('%d.%m.%Y')}\n"
        description += f"Макс. товаров: {plan['max_products']}\n"
        if plan.get('description'):
            description += f"\n{plan['description']}"
        
        try:
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title=f"Подписка: {plan['name']}",
                description=description,
                payload=invoice_payload,
                provider_token=yookassa_token,
                currency="RUB",
                prices=prices,
                start_parameter=f"subscription_plan_{plan_id}"
            )
            await callback.answer("✅ Счет на оплату отправлен в чат!")
        except Exception as invoice_error:
            print(f"Error sending invoice: {invoice_error}")
            import traceback
            traceback.print_exc()
            await callback.answer("❌ Ошибка при создании платежа. Попробуйте позже.", show_alert=True)
            
    except Exception as e:
        print(f"Error in callback_select_plan: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "subscribe_back")
async def callback_subscribe_back(callback: CallbackQuery, bot: Bot):
    """Возвращает к меню управления подпиской."""
    try:
        print(f"[SUBSCRIBE] Back callback, user_id={callback.from_user.id}")
        db = await get_db()
        
        # Получаем пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (callback.from_user.id,)
        )
        
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            await db.disconnect()
            return
        
        user_id = user["id"]
        
        # Проверяем, есть ли у пользователя магазин
        shop = await db.fetch_one(
            "SELECT id, name FROM shops WHERE owner_id = ?",
            (user_id,)
        )
        
        if not shop:
            await callback.answer("❌ У вас нет магазина.", show_alert=True)
            await db.disconnect()
            return
        
        shop_id = shop["id"]
        shop_name = shop["name"]
        
        # Проверяем, есть ли уже активная подписка
        active_subscription = await db.fetch_one(
            """SELECT ss.*, sp.name as plan_name, sp.duration_days, sp.price
               FROM shop_subscriptions ss
               JOIN subscription_plans sp ON ss.plan_id = sp.id
               WHERE ss.shop_id = ? AND ss.is_active = 1 AND ss.end_date > datetime('now')
               ORDER BY ss.end_date DESC
               LIMIT 1""",
            (shop_id,)
        )
        
        await db.disconnect()
        
        # Формируем текст и клавиатуру
        from datetime import datetime
        
        if active_subscription:
            end_date = datetime.fromisoformat(active_subscription["end_date"].replace("Z", "+00:00"))
            end_date_str = end_date.strftime("%d.%m.%Y")
            
            text = f"""
<b>💳 Управление подпиской</b>

<b>Ваш магазин:</b> 🏪 {shop_name}

<b>Текущая подписка:</b>
📦 План: {active_subscription['plan_name']}
📅 Действует до: {end_date_str}

<b>Что вы хотите сделать?</b>
"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 Продлить подписку",
                    callback_data=f"subscribe_extend_{active_subscription['plan_id']}"
                )],
                [InlineKeyboardButton(
                    text="📝 Изменить план",
                    callback_data="subscribe_change_plan"
                )]
            ])
        else:
            text = f"""
<b>💳 Управление подпиской</b>

<b>Ваш магазин:</b> 🏪 {shop_name}

❌ У вас нет активной подписки.

<b>Что вы хотите сделать?</b>
"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📝 Выбрать план подписки",
                    callback_data="subscribe_change_plan"
                )]
            ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
        except Exception as edit_error:
            print(f"Error editing message: {edit_error}")
            await callback.message.answer(text, reply_markup=keyboard)
            await callback.answer()
            
    except Exception as e:
        print(f"Error in callback_subscribe_back: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Произошла ошибка.", show_alert=True)

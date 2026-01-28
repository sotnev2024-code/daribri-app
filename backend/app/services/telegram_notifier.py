"""
Сервис для отправки уведомлений в Telegram.
"""

import asyncio
from datetime import datetime
from typing import Optional
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..config import settings


class TelegramNotifier:
    """Сервис для отправки уведомлений в Telegram."""
    
    _bot: Optional[Bot] = None
    
    @classmethod
    def get_bot(cls) -> Optional[Bot]:
        """Возвращает экземпляр бота или None если токен не настроен."""
        if not settings.BOT_TOKEN:
            print("[TELEGRAM] BOT_TOKEN is empty or not configured!")
            return None
        
        if cls._bot is None:
            print(f"[TELEGRAM] Creating bot instance with token: {settings.BOT_TOKEN[:10]}...")
            cls._bot = Bot(
                token=settings.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        
        return cls._bot
    
    @classmethod
    async def send_message(
        cls,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None
    ) -> bool:
        """
        Отправляет сообщение в Telegram.
        
        Args:
            chat_id: ID чата (telegram_id пользователя)
            text: Текст сообщения
            parse_mode: Режим парсинга (HTML, Markdown)
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        bot = cls.get_bot()
        if not bot:
            print(f"[WARNING] BOT_TOKEN not configured, message not sent to {chat_id}")
            return False
        
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode or ParseMode.HTML
            )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram message to {chat_id}: {e}")
            return False
    
    @classmethod
    async def send_order_notification(
        cls,
        shop_owner_telegram_id: int,
        order_number: str,
        customer_name: Optional[str],
        customer_phone: Optional[str],
        delivery_address: Optional[str],
        items: list,
        total_amount: float,
        promo_code: Optional[str] = None,
        promo_discount: float = 0.0,
        delivery_fee: float = 0.0,
        delivery_date: Optional[str] = None,
        delivery_time: Optional[str] = None,
        customer_telegram_id: Optional[int] = None,
        delivery_type: str = "delivery",
        gift_message: Optional[str] = None
    ) -> bool:
        """
        Отправляет уведомление о новом заказе владельцу магазина.
        
        Args:
            shop_owner_telegram_id: Telegram ID владельца магазина
            order_number: Номер заказа
            customer_name: Имя клиента
            customer_phone: Телефон клиента
            delivery_address: Адрес доставки
            items: Список товаров в заказе
            total_amount: Общая сумма заказа
            promo_code: Промокод (если использовался)
            promo_discount: Скидка по промокоду
            delivery_fee: Стоимость доставки
            delivery_date: Дата доставки
            delivery_time: Время доставки
            customer_telegram_id: Telegram ID клиента (для ссылки)
            gift_message: Текст для открытки (если указан)
            
        Returns:
            bool: True если уведомление отправлено
        """
        items_text = "\n".join([
            f"• {item.get('name', 'Товар')} × {item.get('quantity', 1)} — {item.get('total', 0):.2f} ₽"
            for item in items
        ])
        
        # Формируем имя клиента со ссылкой на Telegram профиль
        if customer_telegram_id and customer_name:
            customer_display = f'<a href="tg://user?id={customer_telegram_id}">{customer_name}</a>'
        elif customer_telegram_id:
            customer_display = f'<a href="tg://user?id={customer_telegram_id}">Покупатель</a>'
        else:
            customer_display = customer_name or 'Не указано'
        
        # Определяем тип получения заказа
        is_pickup = delivery_type == 'pickup'
        
        # Формируем информацию о дате и времени
        time_info = ""
        if delivery_date or delivery_time:
            if is_pickup:
                time_info = "\n<b>📅 Получение заказа:</b> "
            else:
                time_info = "\n<b>📅 Доставка:</b> "
            if delivery_date:
                time_info += delivery_date
            if delivery_time:
                time_info += f" в {delivery_time}"
        
        # Формируем информацию о промокоде
        promo_info = ""
        if promo_code:
            promo_info = f"\n<b>🎫 Промокод:</b> {promo_code}"
            if promo_discount > 0:
                promo_info += f" (скидка {promo_discount:.2f} ₽)"
        
        # Текущее время
        order_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Определяем заголовок адреса
        if is_pickup:
            address_label = "Адрес магазина (самовывоз)"
        else:
            address_label = "Адрес доставки"
        
        message = f"""
<b>🛒 Новый заказ!</b>

<b>🕐 Время:</b> {order_time}
<b>Номер заказа:</b> {order_number}
<b>Клиент:</b> {customer_display}
<b>Телефон:</b> {customer_phone or 'Не указан'}
<b>{address_label}:</b> {delivery_address or 'Не указан'}{time_info}

<b>Товары:</b>
{items_text}
"""
        
        # Добавляем текст открытки, если указан
        if gift_message and gift_message.strip():
            message += f"\n\n<b>💌 Текст для открытки:</b>\n<i>{gift_message}</i>"
        
        # Добавляем информацию о стоимости
        if not is_pickup and delivery_fee > 0:
            message += f"\n<b>🚚 Доставка:</b> {delivery_fee:.2f} ₽"
        
        if promo_info:
            message += promo_info
        
        message += f"\n<b>💰 Итого:</b> {total_amount:.2f} ₽"
        
        print(f"[TELEGRAM] Sending order notification to shop owner {shop_owner_telegram_id}")
        print(f"[TELEGRAM] Customer link: {customer_display}")
        result = await cls.send_message(shop_owner_telegram_id, message)
        print(f"[TELEGRAM] Order notification sent: {result}")
        return result
    
    @classmethod
    async def send_order_status_notification(
        cls,
        customer_telegram_id: int,
        order_id: int,
        order_number: str,
        shop_id: int,
        shop_name: str,
        new_status: str,
        total_amount: float
    ) -> bool:
        """
        Отправляет уведомление покупателю об изменении статуса заказа.
        
        Args:
            customer_telegram_id: Telegram ID покупателя
            order_id: ID заказа
            order_number: Номер заказа
            shop_id: ID магазина
            shop_name: Название магазина
            new_status: Новый статус заказа
            total_amount: Сумма заказа
            
        Returns:
            bool: True если уведомление отправлено
        """
        bot = cls.get_bot()
        if not bot:
            print(f"[WARNING] BOT_TOKEN not configured, status notification not sent to {customer_telegram_id}")
            return False
        
        # Статусы на русском с эмодзи
        status_map = {
            "pending": ("⏳ Ожидает обработки", False),
            "processing": ("🔄 В обработке", False),
            "delivered": ("✅ Доставлен", True),
            "cancelled": ("❌ Отменён", True)
        }
        
        status_text, show_review_button = status_map.get(new_status, (new_status, False))
        
        message = f"""
<b>📦 Обновление заказа</b>

<b>Заказ:</b> {order_number}
<b>Магазин:</b> {shop_name}
<b>Сумма:</b> {total_amount:.2f} ₽

<b>Статус:</b> {status_text}
"""
        
        if new_status == "delivered":
            message += "\n<i>Спасибо за покупку! Будем рады вашему отзыву о магазине 💝</i>"
        elif new_status == "cancelled":
            message += "\n<i>Нам жаль, что заказ был отменён. Вы можете оставить отзыв о магазине.</i>"
        
        # Формируем клавиатуру
        keyboard_buttons = []
        
        # Кнопка "Оставить отзыв" для статусов delivered и cancelled
        if show_review_button:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="⭐ Оставить отзыв",
                    callback_data=f"review:{shop_id}:{order_id}"
                )
            ])
        
        # Кнопка "Открыть приложение" убрана по запросу
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        
        print(f"[TELEGRAM] Sending status notification to customer {customer_telegram_id}")
        print(f"[TELEGRAM] Status: {new_status}, Shop: {shop_name}, Order: {order_number}")
        
        try:
            await bot.send_message(
                chat_id=customer_telegram_id,
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            print(f"[TELEGRAM] Status notification sent successfully!")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send order status notification to {customer_telegram_id}: {e}")
            import traceback
            traceback.print_exc()
            return False


    @classmethod
    async def send_order_confirmation_to_customer(
        cls,
        customer_telegram_id: int,
        order_number: str,
        customer_name: Optional[str],
        customer_phone: Optional[str],
        delivery_address: Optional[str],
        delivery_date: Optional[str],
        delivery_time: Optional[str],
        items: list,
        delivery_fee: float,
        total_amount: float = 0.0,
        delivery_type: str = "delivery"
    ) -> bool:
        """
        Отправляет сообщение с подтверждением заказа покупателю.
        
        Args:
            customer_telegram_id: Telegram ID покупателя
            order_number: Номер заказа
            customer_name: Имя покупателя
            customer_phone: Телефон покупателя
            delivery_address: Адрес доставки
            delivery_date: Дата доставки
            delivery_time: Время доставки
            items: Список товаров в заказе
            delivery_fee: Стоимость доставки
            total_amount: Общая сумма заказа
            
        Returns:
            bool: True если сообщение отправлено
        """
        bot = cls.get_bot()
        if not bot:
            print(f"[WARNING] BOT_TOKEN not configured, order confirmation not sent to {customer_telegram_id}")
            return False
        
        # Формируем имя клиента со ссылкой на Telegram профиль
        if customer_name:
            customer_display = f'<a href="tg://user?id={customer_telegram_id}">{customer_name}</a>'
        else:
            customer_display = '<a href="tg://user?id={customer_telegram_id}">Клиент</a>'
        
        # Форматируем состав заказа
        items_text = "\n".join([
            f"• {item.get('name', 'Товар')} × {item.get('quantity', 1)} — {item.get('total', 0):.2f} ₽"
            for item in items
        ])
        
        # Определяем тип получения заказа
        is_pickup = delivery_type == 'pickup'
        
        # Формируем временной слот
        time_slot = ""
        if delivery_date and delivery_time:
            time_slot = f"{delivery_date} в {delivery_time}"
        elif delivery_date:
            time_slot = delivery_date
        elif delivery_time:
            time_slot = delivery_time
        
        # Формируем сообщение в зависимости от типа получения
        if is_pickup:
            # Самовывоз
            time_slot_line = f'\n📅 Получение заказа: {time_slot}' if time_slot else ''
            address_label = 'Адрес магазина'
            delivery_fee_line = ''  # Для самовывоза не показываем стоимость доставки
        else:
            # Доставка
            time_slot_line = f'\n📅 Доставка: {time_slot}' if time_slot else ''
            address_label = 'Адрес доставки'
            delivery_fee_line = f'\n🚚 Доставка: {delivery_fee:.2f} ₽' if delivery_fee > 0 else ''
        
        message = f"""<b>Заказ {order_number} успешно оформлен</b>
Клиент: {customer_display}
Телефон: {customer_phone or 'Не указан'}
{address_label}: {delivery_address or 'Не указан'}{time_slot_line}

Товары:
{items_text}
{delivery_fee_line}
💰 Итого: {total_amount:.2f} ₽

Спасибо за ваш заказ! В ближайшее время с вами свяжется менеджер"""
        
        print(f"[TELEGRAM] Sending order confirmation to customer {customer_telegram_id}")
        print(f"[TELEGRAM] Order: {order_number}, Total: {total_amount:.2f} ₽")
        
        try:
            await bot.send_message(
                chat_id=customer_telegram_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            print(f"[TELEGRAM] Order confirmation sent successfully!")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send order confirmation to {customer_telegram_id}: {e}")
            import traceback
            traceback.print_exc()
            return False


# Глобальный экземпляр
telegram_notifier = TelegramNotifier()




"""
Сервис для проверки и отправки напоминаний о событиях.
"""

import asyncio
from datetime import date, datetime, time
from typing import Optional
import pytz
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from backend.app.services.database import DatabaseService
from backend.app.config import settings


class ReminderService:
    """Сервис для управления напоминаниями."""
    
    _bot: Optional[Bot] = None
    
    @classmethod
    def get_bot(cls) -> Optional[Bot]:
        """Возвращает экземпляр бота или None если токен не настроен."""
        if not settings.BOT_TOKEN:
            print("[REMINDER SERVICE] BOT_TOKEN is empty or not configured!")
            return None
        
        if cls._bot is None:
            print(f"[REMINDER SERVICE] Creating bot instance")
            cls._bot = Bot(
                token=settings.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        
        return cls._bot
    
    @classmethod
    async def check_and_send_reminders(cls):
        """Проверяет напоминания и отправляет уведомления."""
        try:
            # Получаем текущее время в Екатеринбурге
            ekb_tz = pytz.timezone('Asia/Yekaterinburg')
            now_ekb = datetime.now(ekb_tz)
            current_date = now_ekb.date()
            current_time = now_ekb.time()
            
            # Проверяем, что сейчас 10:00 (с небольшой погрешностью - от 10:00 до 10:05)
            reminder_time = time(10, 0)
            reminder_time_end = time(10, 5)
            
            if not (reminder_time <= current_time <= reminder_time_end):
                # Не время для отправки напоминаний
                return
            
            print(f"[REMINDER SERVICE] Checking reminders for {current_date} at {current_time}")
            
            db = DatabaseService(db_path=settings.DATABASE_PATH)
            await db.connect()
            
            # Получаем все напоминания на сегодня, которые еще не отправлены
            reminders = await db.fetch_all(
                """SELECT r.*, u.telegram_id 
                   FROM reminders r
                   JOIN users u ON r.user_id = u.id
                   WHERE r.event_date = ? AND r.is_sent = 0""",
                (current_date.isoformat(),)
            )
            
            print(f"[REMINDER SERVICE] Found {len(reminders)} reminders to send")
            
            bot = cls.get_bot()
            if not bot:
                print("[REMINDER SERVICE] Bot not available, skipping reminder sending")
                await db.disconnect()
                return
            
            sent_count = 0
            for reminder in reminders:
                try:
                    telegram_id = reminder.get("telegram_id")
                    if not telegram_id:
                        print(f"[REMINDER SERVICE] No telegram_id for reminder {reminder.get('id')}")
                        continue
                    
                    event_description = reminder.get("event_description", "Событие")
                    event_date_str = reminder.get("event_date")
                    
                    # Форматируем дату для отображения
                    if event_date_str:
                        try:
                            event_date = date.fromisoformat(event_date_str) if isinstance(event_date_str, str) else event_date_str
                            date_formatted = event_date.strftime("%d.%m.%Y")
                        except:
                            date_formatted = event_date_str
                    else:
                        date_formatted = current_date.strftime("%d.%m.%Y")
                    
                    message = f"""🎁 <b>Напоминание о событии</b>

📅 Дата: <b>{date_formatted}</b>
📝 Событие: <b>{event_description}</b>

Не забудьте подготовить подарок для ваших близких! 💝

<i>Откройте каталог, чтобы выбрать подарок:</i>"""
                    
                    # Создаем кнопку для открытия каталога
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
                    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🛒 Открыть каталог",
                            web_app=WebAppInfo(url=webapp_url)
                        )]
                    ])
                    
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=message,
                        reply_markup=keyboard
                    )
                    
                    # Помечаем напоминание как отправленное
                    await db.execute(
                        "UPDATE reminders SET is_sent = 1, sent_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), reminder.get("id"))
                    )
                    
                    sent_count += 1
                    print(f"[REMINDER SERVICE] Sent reminder {reminder.get('id')} to user {telegram_id}")
                    
                except Exception as e:
                    print(f"[REMINDER SERVICE] Error sending reminder {reminder.get('id')}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if sent_count > 0:
                await db.commit()
                print(f"[REMINDER SERVICE] Successfully sent {sent_count} reminders")
            
            await db.disconnect()
            
        except Exception as e:
            print(f"[REMINDER SERVICE] Error in check_and_send_reminders: {e}")
            import traceback
            traceback.print_exc()
    
    @classmethod
    async def start_periodic_check(cls, interval_minutes: int = 5):
        """Запускает периодическую проверку напоминаний."""
        print(f"[REMINDER SERVICE] Starting periodic reminder check (every {interval_minutes} minutes)")
        
        while True:
            try:
                await cls.check_and_send_reminders()
            except Exception as e:
                print(f"[REMINDER SERVICE] Error in periodic check: {e}")
                import traceback
                traceback.print_exc()
            
            # Ждем перед следующей проверкой
            await asyncio.sleep(interval_minutes * 60)


# Глобальный экземпляр
reminder_service = ReminderService()


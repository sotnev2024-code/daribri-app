"""
Обработчик команды /remind для создания напоминаний о событиях.
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, datetime
import re

from backend.app.services.database import DatabaseService
from backend.app.config import settings

router = Router()


class ReminderStates(StatesGroup):
    """Состояния для создания напоминания."""
    waiting_for_date = State()
    waiting_for_description = State()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def get_db():
    """Получает экземпляр базы данных."""
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    return db


def parse_date(date_str: str) -> date | None:
    """Парсит дату из строки в форматах DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD."""
    date_str = date_str.strip()
    
    # Формат DD.MM.YYYY или DD/MM/YYYY
    patterns = [
        r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # DD.MM.YYYY
        r'(\d{1,2})/(\d{1,2})/(\d{4})',    # DD/MM/YYYY
        r'(\d{4})-(\d{1,2})-(\d{1,2})',    # YYYY-MM-DD
    ]
    
    for pattern in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                if pattern == patterns[2]:  # YYYY-MM-DD
                    year, month, day = map(int, match.groups())
                else:  # DD.MM.YYYY или DD/MM/YYYY
                    day, month, year = map(int, match.groups())
                
                parsed_date = date(year, month, day)
                # Проверяем, что дата не в прошлом
                if parsed_date < date.today():
                    return None
                return parsed_date
            except ValueError:
                continue
    
    return None


@router.message(Command("remind", "напомнить", "напомни"))
async def cmd_remind(message: Message, state: FSMContext):
    """Команда для создания напоминания о событии."""
    print(f"[REMIND] Command received from user {message.from_user.id}")
    try:
        db = await get_db()
        
        # Проверяем, зарегистрирован ли пользователь
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы в системе.\n"
                "Используйте команду /start для регистрации."
            )
            await db.disconnect()
            return
        
        await db.disconnect()
        
        await message.answer(
            "📅 <b>Создание напоминания о событии</b>\n\n"
            "Введите дату события в формате <b>ДД.ММ.ГГГГ</b>\n"
            "Например: <code>15.02.2026</code> или <code>15/02/2026</code>\n\n"
            "<i>Дата должна быть в будущем</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(ReminderStates.waiting_for_date)
        
    except Exception as e:
        print(f"[REMIND] Error in cmd_remind: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(ReminderStates.waiting_for_date, F.text)
async def process_reminder_date(message: Message, state: FSMContext):
    """Обрабатывает дату события."""
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание напоминания отменено.", reply_markup=ReplyKeyboardRemove())
        return
    
    parsed_date = parse_date(message.text)
    
    if not parsed_date:
        await message.answer(
            "❌ Неверный формат даты.\n\n"
            "Введите дату в формате <b>ДД.ММ.ГГГГ</b>\n"
            "Например: <code>15.02.2026</code>\n\n"
            "<i>Дата должна быть в будущем</i>",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(event_date=parsed_date.isoformat())
    
    await message.answer(
        "📝 Теперь опишите событие.\n\n"
        "Например: <i>День рождения мамы</i> или <i>Годовщина свадьбы</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ReminderStates.waiting_for_description)


@router.message(ReminderStates.waiting_for_description, F.text)
async def process_reminder_description(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает описание события и сохраняет напоминание."""
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Создание напоминания отменено.", reply_markup=ReplyKeyboardRemove())
        return
    
    description = message.text.strip()
    
    if len(description) > 500:
        await message.answer(
            "❌ Описание слишком длинное (максимум 500 символов).\n"
            "Пожалуйста, сократите описание.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    try:
        data = await state.get_data()
        event_date_str = data.get("event_date")
        
        if not event_date_str:
            await message.answer("❌ Ошибка: дата не найдена. Начните заново с команды /remind")
            await state.clear()
            return
        
        event_date = date.fromisoformat(event_date_str)
        
        db = await get_db()
        
        # Получаем ID пользователя
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        
        if not user:
            await message.answer("❌ Пользователь не найден.")
            await db.disconnect()
            await state.clear()
            return
        
        # Сохраняем напоминание
        reminder_id = await db.insert("reminders", {
            "user_id": user["id"],
            "event_date": event_date.isoformat(),
            "event_description": description,
            "is_sent": 0
        })
        
        await db.commit()
        await db.disconnect()
        
        # Форматируем дату для отображения
        date_formatted = event_date.strftime("%d.%m.%Y")
        
        await message.answer(
            f"✅ <b>Напоминание создано!</b>\n\n"
            f"📅 Дата: <b>{date_formatted}</b>\n"
            f"📝 Событие: <b>{description}</b>\n\n"
            f"Я напомню вам об этом событии <b>10:00</b> утра по времени Екатеринбурга.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        print(f"[REMIND] Error saving reminder: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            "❌ Произошла ошибка при сохранении напоминания. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


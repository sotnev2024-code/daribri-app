"""
Обработчик запроса номера телефона для оформления заказа.
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class PhoneRequestStates(StatesGroup):
    """Состояния для запроса номера телефона."""
    waiting_for_phone = State()


@router.message(Command("phone"))
async def cmd_phone(message: Message, state: FSMContext, bot: Bot):
    """Команда для запроса номера телефона."""
    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
    await handle_phone_request(message, state, bot, webapp_url)


@router.message(Command("start"), F.text.contains("phone_request"))
async def cmd_start_phone(message: Message, state: FSMContext, bot: Bot):
    """Обработка команды /start с параметром phone_request."""
    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
    await handle_phone_request(message, state, bot, webapp_url)


async def handle_phone_request(message: Message, state: FSMContext, bot: Bot, webapp_url: str):
    """Общая функция для обработки запроса номера телефона."""
    text = """
<b>📱 Отправка номера телефона</b>

Чтобы продолжить оформление заказа, отправьте ваш номер телефона.

Вы можете:
1. Нажать кнопку ниже, чтобы отправить контакт
2. Или написать номер вручную (например: +79991234567)

После отправки номера нажмите кнопку "Вернуться в приложение", чтобы вернуться к оформлению заказа.
"""
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить контакт", request_contact=True)],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(PhoneRequestStates.waiting_for_phone)


@router.message(PhoneRequestStates.waiting_for_phone, F.contact)
async def handle_contact(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает контакт от пользователя."""
    contact = message.contact
    phone = contact.phone_number
    
    # Сохраняем номер телефона для пользователя (можно в БД)
    try:
        from backend.app.services.database import DatabaseService
        db = DatabaseService()
        await db.connect()
        
        # Обновляем номер телефона пользователя в БД
        await db.execute(
            "UPDATE users SET phone = ? WHERE telegram_id = ?",
            (phone, message.from_user.id)
        )
        await db.commit()
        await db.disconnect()
    except Exception as e:
        print(f"Error saving phone to DB: {e}")
    
    await state.clear()
    
    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
    
    # Формируем URL для возврата в приложение с номером телефона
    return_url = f"{webapp_url}?phone={phone.replace('+', '%2B')}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    
    text = f"""
<b>✅ Номер телефона получен!</b>

Ваш номер: <code>{phone}</code>

Теперь вернитесь в приложение, чтобы продолжить оформление заказа.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="↩️ Вернуться в приложение",
            web_app=WebAppInfo(url=return_url)
        )]
    ])
    
    await message.answer(
        text,
        reply_markup=keyboard
    )
    await message.answer(
        "Номер сохранен. Нажмите кнопку выше, чтобы вернуться к оформлению заказа.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(PhoneRequestStates.waiting_for_phone, F.text.regexp(r'^\+?[0-9]{10,15}$'))
async def handle_phone_text(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает номер телефона, введенный текстом."""
    phone = message.text.strip()
    
    # Нормализуем номер телефона
    if not phone.startswith('+'):
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('7'):
            phone = '+' + phone
        else:
            phone = '+7' + phone
    
    # Сохраняем номер телефона для пользователя
    try:
        from backend.app.services.database import DatabaseService
        db = DatabaseService()
        await db.connect()
        
        # Обновляем номер телефона пользователя в БД
        await db.execute(
            "UPDATE users SET phone = ? WHERE telegram_id = ?",
            (phone, message.from_user.id)
        )
        await db.commit()
        await db.disconnect()
    except Exception as e:
        print(f"Error saving phone to DB: {e}")
    
    await state.clear()
    
    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
    
    # Формируем URL для возврата в приложение с номером телефона
    return_url = f"{webapp_url}?phone={phone.replace('+', '%2B')}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    
    text = f"""
<b>✅ Номер телефона получен!</b>

Ваш номер: <code>{phone}</code>

Теперь вернитесь в приложение, чтобы продолжить оформление заказа.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="↩️ Вернуться в приложение",
            web_app=WebAppInfo(url=return_url)
        )]
    ])
    
    await message.answer(
        text,
        reply_markup=keyboard
    )
    await message.answer(
        "Номер сохранен. Нажмите кнопку выше, чтобы вернуться к оформлению заказа.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(PhoneRequestStates.waiting_for_phone, F.text == "❌ Отменить")
async def cancel_phone_request(message: Message, state: FSMContext, bot: Bot):
    """Отменяет запрос номера телефона."""
    await state.clear()
    
    webapp_url = getattr(bot, 'webapp_url', 'http://localhost:8081')
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    
    text = "❌ Отправка номера телефона отменена."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="↩️ Вернуться в приложение",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    
    await message.answer(text, reply_markup=keyboard)
    await message.answer(
        "Вы можете вернуться в приложение и ввести номер вручную.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(PhoneRequestStates.waiting_for_phone)
async def handle_invalid_phone(message: Message):
    """Обрабатывает некорректный ввод номера телефона."""
    await message.answer(
        "❌ Пожалуйста, отправьте номер телефона в правильном формате:\n"
        "• Нажмите кнопку \"📱 Отправить контакт\"\n"
        "• Или введите номер вручную (например: +79991234567)\n\n"
        "Для отмены нажмите кнопку \"❌ Отменить\""
    )


"""
Обработчики корзины.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


@router.message(Command("cart"))
async def cmd_cart(message: Message):
    """Команда /cart."""
    await show_cart_message(message)


@router.callback_query(F.data == "cart")
async def callback_cart(callback: CallbackQuery):
    """Callback для корзины."""
    await show_cart_callback(callback)


async def show_cart_message(message: Message):
    """Показывает корзину (для сообщений)."""
    # В реальном приложении здесь будет запрос к API
    text = """
<b>🛒 Ваша корзина</b>

Корзина пуста.

<i>Добавьте товары из каталога</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Каталог", callback_data="open_catalog")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


async def show_cart_callback(callback: CallbackQuery):
    """Показывает корзину (для callback)."""
    text = """
<b>🛒 Ваша корзина</b>

Корзина пуста.

<i>Добавьте товары из каталога</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Каталог", callback_data="open_catalog")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()







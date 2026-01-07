"""
Обработчики магазина продавца.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


@router.message(Command("shop"))
async def cmd_shop(message: Message):
    """Команда /shop."""
    await show_shop_message(message)


@router.callback_query(F.data == "my_shop")
async def callback_shop(callback: CallbackQuery):
    """Callback для магазина."""
    await show_shop_callback(callback)


@router.callback_query(F.data == "favorites")
async def callback_favorites(callback: CallbackQuery):
    """Callback для избранного."""
    text = """
<b>❤️ Избранное</b>

Список избранного пуст.

<i>Добавляйте понравившиеся товары в избранное!</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Каталог", callback_data="open_catalog")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


async def show_shop_message(message: Message):
    """Показывает информацию о магазине."""
    # В реальном приложении здесь будет проверка магазина пользователя
    text = """
<b>🏪 Мой магазин</b>

У вас пока нет магазина.

<b>Хотите стать продавцом?</b>
Создайте свой магазин и начните продавать!

<b>Преимущества:</b>
✓ Доступ к тысячам покупателей
✓ Удобное управление товарами
✓ Аналитика продаж
✓ Низкая комиссия
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать магазин", callback_data="create_shop")],
        [InlineKeyboardButton(text="💳 Тарифы", callback_data="subscription_plans")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


async def show_shop_callback(callback: CallbackQuery):
    """Показывает информацию о магазине (callback)."""
    text = """
<b>🏪 Мой магазин</b>

У вас пока нет магазина.

<b>Хотите стать продавцом?</b>
Создайте свой магазин и начните продавать!

<b>Преимущества:</b>
✓ Доступ к тысячам покупателей
✓ Удобное управление товарами
✓ Аналитика продаж
✓ Низкая комиссия
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать магазин", callback_data="create_shop")],
        [InlineKeyboardButton(text="💳 Тарифы", callback_data="subscription_plans")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "subscription_plans")
async def show_plans(callback: CallbackQuery):
    """Показывает тарифы."""
    text = """
<b>💳 Тарифные планы</b>

<b>🌱 Стартовый</b> - 990 ₽/мес
• До 20 товаров
• Базовая поддержка

<b>🚀 Бизнес</b> - 2 490 ₽/мес
• До 100 товаров
• Приоритетная поддержка
• Аналитика
• 5 промо-размещений

<b>👑 Премиум</b> - 4 990 ₽/мес
• До 500 товаров
• VIP поддержка
• Расширенная аналитика
• 20 промо-размещений
• Выделенное место в каталоге
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Стартовый", callback_data="subscribe_1")],
        [InlineKeyboardButton(text="🚀 Бизнес", callback_data="subscribe_2")],
        [InlineKeyboardButton(text="👑 Премиум", callback_data="subscribe_3")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_shop")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "create_shop")
async def create_shop(callback: CallbackQuery):
    """Создание магазина."""
    text = """
<b>➕ Создание магазина</b>

Для создания магазина откройте Mini App и перейдите в раздел "Мой магазин".

Там вы сможете:
• Заполнить информацию о магазине
• Добавить фото и описание
• Выбрать тариф
• Добавить товары
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_shop")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()







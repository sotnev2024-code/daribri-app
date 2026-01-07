"""
Обработчики каталога.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


@router.callback_query(F.data == "trending")
async def show_trending(callback: CallbackQuery):
    """Показывает трендовые товары."""
    # В реальном приложении здесь будет запрос к API
    text = """
<b>🔥 Тренды</b>

Популярные товары сейчас:

1. 💐 Букет "Весенняя свежесть" - 3 500 ₽
2. 🌹 Красные розы 51 шт - 8 900 ₽
3. 🪴 Монстера - 2 200 ₽
4. 🍰 Торт "Красный бархат" - 2 800 ₽

<i>Откройте каталог для просмотра всех товаров</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "discounts")
async def show_discounts(callback: CallbackQuery):
    """Показывает товары со скидкой."""
    text = """
<b>🏷 Скидки</b>

Специальные предложения:

1. 💐 Букет "Нежность" - <s>4 000 ₽</s> 2 800 ₽ (-30%)
2. 🌺 Орхидея в горшке - <s>3 500 ₽</s> 2 450 ₽ (-30%)
3. 🧁 Набор капкейков - <s>1 800 ₽</s> 1 260 ₽ (-30%)

<i>Откройте каталог для просмотра всех скидок</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    from .start import get_main_keyboard
    
    webapp_url = getattr(callback.bot, 'webapp_url', 'https://your-domain.com')
    
    text = """
<b>👋 Дарибри</b>

Выберите действие:
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(webapp_url)
    )
    await callback.answer()







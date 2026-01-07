"""
Обработчики заказов.
"""

from typing import Optional, Union
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from backend.app.services.database import DatabaseService
from backend.app.config import settings

router = Router()


class ReviewStates(StatesGroup):
    """Состояния для оставления отзыва."""
    waiting_for_rating = State()
    waiting_for_comment = State()


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    """Команда /orders."""
    await show_orders_message(message)


@router.callback_query(F.data == "orders")
async def callback_orders(callback: CallbackQuery):
    """Callback для заказов."""
    await show_orders_callback(callback)


@router.callback_query(F.data.startswith("review:"))
async def callback_start_review(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс оставления отзыва."""
    # Формат: review:shop_id:order_id
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка данных", show_alert=True)
        return
    
    shop_id = int(parts[1])
    order_id = int(parts[2])
    
    # Проверяем, не оставлял ли пользователь уже отзыв
    db = DatabaseService()
    await db.connect()
    
    try:
        existing_review = await db.fetch_one(
            """SELECT id FROM shop_reviews 
               WHERE user_id = (SELECT id FROM users WHERE telegram_id = ?) 
               AND shop_id = ?""",
            (callback.from_user.id, shop_id)
        )
        
        if existing_review:
            await callback.answer("Вы уже оставляли отзыв об этом магазине", show_alert=True)
            return
        
        # Получаем информацию о магазине
        shop = await db.fetch_one(
            "SELECT name FROM shops WHERE id = ?",
            (shop_id,)
        )
        
        if not shop:
            await callback.answer("Магазин не найден", show_alert=True)
            return
        
        # Сохраняем данные в состояние
        await state.update_data(shop_id=shop_id, order_id=order_id, shop_name=shop["name"])
        await state.set_state(ReviewStates.waiting_for_rating)
        
        # Показываем клавиатуру выбора рейтинга
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐", callback_data="rating:1"),
                InlineKeyboardButton(text="⭐⭐", callback_data="rating:2"),
                InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating:3"),
            ],
            [
                InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating:4"),
                InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating:5"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_review")]
        ])
        
        await callback.message.answer(
            f"<b>⭐ Отзыв о магазине «{shop['name']}»</b>\n\n"
            f"Выберите оценку:",
            reply_markup=keyboard
        )
        await callback.answer()
        
    finally:
        await db.disconnect()


@router.callback_query(F.data.startswith("rating:"), ReviewStates.waiting_for_rating)
async def callback_select_rating(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор рейтинга."""
    rating = int(callback.data.split(":")[1])
    
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.waiting_for_comment)
    
    data = await state.get_data()
    shop_name = data.get("shop_name", "магазине")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_comment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_review")]
    ])
    
    stars = "⭐" * rating
    await callback.message.edit_text(
        f"<b>⭐ Отзыв о магазине «{shop_name}»</b>\n\n"
        f"Ваша оценка: {stars}\n\n"
        f"Напишите комментарий к отзыву или нажмите «Пропустить»:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(ReviewStates.waiting_for_comment)
async def process_review_comment(message: Message, state: FSMContext):
    """Обрабатывает комментарий к отзыву."""
    comment = message.text.strip()
    
    if len(comment) > 1000:
        await message.answer("❌ Комментарий слишком длинный (максимум 1000 символов). Попробуйте ещё раз:")
        return
    
    await save_review(message.from_user.id, state, comment, message)


@router.callback_query(F.data == "skip_comment", ReviewStates.waiting_for_comment)
async def callback_skip_comment(callback: CallbackQuery, state: FSMContext):
    """Пропускает комментарий."""
    await save_review(callback.from_user.id, state, None, callback)
    await callback.answer()


@router.callback_query(F.data == "cancel_review")
async def callback_cancel_review(callback: CallbackQuery, state: FSMContext):
    """Отменяет оставление отзыва."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Оставление отзыва отменено.\n\n"
        "Вы всегда можете оставить отзыв позже в приложении."
    )
    await callback.answer()


async def save_review(telegram_id: int, state: FSMContext, comment: Optional[str], message_or_callback: Union[Message, CallbackQuery]):
    """Сохраняет отзыв в базу данных."""
    data = await state.get_data()
    shop_id = data.get("shop_id")
    order_id = data.get("order_id")
    rating = data.get("rating")
    shop_name = data.get("shop_name", "магазине")
    
    db = DatabaseService()
    await db.connect()
    
    try:
        # Получаем user_id по telegram_id
        user = await db.fetch_one(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        
        if not user:
            text = "❌ Ошибка: пользователь не найден"
            if hasattr(message_or_callback, 'message'):
                # Это CallbackQuery
                await message_or_callback.message.edit_text(text)
            else:
                # Это Message
                await message_or_callback.answer(text)
            await state.clear()
            return
        
        # Проверяем заказ (для верифицированного отзыва)
        is_verified = False
        if order_id:
            order = await db.fetch_one(
                """SELECT id FROM orders 
                   WHERE id = ? AND user_id = ? AND shop_id = ? AND status = 'delivered'""",
                (order_id, user["id"], shop_id)
            )
            if order:
                is_verified = True
        
        # Сохраняем отзыв
        await db.insert("shop_reviews", {
            "shop_id": shop_id,
            "user_id": user["id"],
            "order_id": order_id,
            "rating": rating,
            "comment": comment,
            "is_verified": is_verified
        })
        await db.commit()
        
        stars = "⭐" * rating
        verified_badge = " ✅" if is_verified else ""
        
        text = (
            f"<b>✅ Спасибо за отзыв!</b>\n\n"
            f"<b>Магазин:</b> {shop_name}\n"
            f"<b>Оценка:</b> {stars}{verified_badge}\n"
        )
        if comment:
            text += f"<b>Комментарий:</b> {comment[:100]}{'...' if len(comment) > 100 else ''}\n"
        
        text += "\n<i>Ваш отзыв поможет другим покупателям!</i>"
        
        # Добавляем кнопку открытия приложения
        keyboard = None
        if settings.WEBAPP_URL:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Открыть приложение", url=settings.WEBAPP_URL)]
            ])
        
        # Проверяем тип объекта: CallbackQuery имеет атрибут message, Message - нет
        if hasattr(message_or_callback, 'message'):
            # Это CallbackQuery - редактируем сообщение
            await message_or_callback.message.edit_text(text, reply_markup=keyboard)
        else:
            # Это Message - отправляем новое сообщение
            await message_or_callback.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        print(f"[ERROR] Failed to save review: {e}")
        import traceback
        traceback.print_exc()
        text = "❌ Произошла ошибка при сохранении отзыва. Попробуйте позже."
        if hasattr(message_or_callback, 'message'):
            # Это CallbackQuery
            await message_or_callback.message.edit_text(text)
        else:
            # Это Message
            await message_or_callback.answer(text)
    
    finally:
        await db.disconnect()
        await state.clear()


async def show_orders_message(message: Message):
    """Показывает заказы."""
    text = """
<b>📦 Мои заказы</b>

У вас пока нет заказов.

<i>Оформите первый заказ в каталоге!</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Каталог", callback_data="open_catalog")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


async def show_orders_callback(callback: CallbackQuery):
    """Показывает заказы (callback)."""
    text = """
<b>📦 Мои заказы</b>

У вас пока нет заказов.

<i>Оформите первый заказ в каталоге!</i>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Каталог", callback_data="open_catalog")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()







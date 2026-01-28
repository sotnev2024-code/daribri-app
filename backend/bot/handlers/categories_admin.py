"""
Обработчики управления категориями для администратора.
"""

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import hashlib
from pathlib import Path
from backend.app.config import settings

router = Router()


class CategoryCreateStates(StatesGroup):
    """Состояния для создания категории."""
    waiting_for_type = State()  # Основная или подкатегория
    waiting_for_name = State()
    waiting_for_photo = State()  # Только для основных категорий
    waiting_for_parent_id = State()  # Только для подкатегорий
    waiting_for_description = State()
    waiting_for_sort_order = State()


async def get_db():
    """Получает экземпляр базы данных."""
    from backend.app.services.database import DatabaseService
    
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    await db.connect()
    
    # Проверяем и добавляем поле photo_url, если его нет
    try:
        columns = await db.fetch_all("PRAGMA table_info(categories)")
        column_names = [col["name"] for col in columns]
        
        if "photo_url" not in column_names:
            print("[MIGRATION] Adding photo_url column to categories table...")
            await db.execute("ALTER TABLE categories ADD COLUMN photo_url TEXT")
            await db.commit()
            print("[MIGRATION] photo_url column added successfully")
    except Exception as e:
        print(f"[MIGRATION] Error checking/adding photo_url column: {e}")
    
    return db


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    admin_ids_str = os.getenv("ADMIN_IDS", "") or getattr(settings, "ADMIN_IDS", "")
    
    if admin_ids_str:
        try:
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip().isdigit()]
            return user_id in admin_ids
        except (ValueError, AttributeError):
            pass
    
    return True  # Временно разрешаем всем для разработки


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def show_categories_menu(callback: CallbackQuery, bot: Bot):
    """Показывает главное меню управления категориями."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Статистика категорий
        total_categories = await db.fetch_one("SELECT COUNT(*) as cnt FROM categories")
        main_categories = await db.fetch_one("SELECT COUNT(*) as cnt FROM categories WHERE parent_id IS NULL")
        subcategories = await db.fetch_one("SELECT COUNT(*) as cnt FROM categories WHERE parent_id IS NOT NULL")
        categories_with_products = await db.fetch_one(
            "SELECT COUNT(DISTINCT category_id) as cnt FROM products WHERE category_id IS NOT NULL"
        )
        
        await db.disconnect()
        
        menu_text = f"""
<b>📂 Управление категориями</b>

<b>Статистика:</b>
📊 Всего категорий: {total_categories['cnt']}
📁 Основных: {main_categories['cnt']}
📂 Подкатегорий: {subcategories['cnt']}
📦 С товарами: {categories_with_products['cnt']}

Выберите действие:
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_category_create")],
            [InlineKeyboardButton(text="📋 Список категорий", callback_data="admin_categories_list")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_menu")]
        ])
        
        try:
            await callback.message.edit_text(menu_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(menu_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing categories menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке меню категорий.", show_alert=True)


async def show_categories_list(callback: CallbackQuery, bot: Bot, parent_id: int = None, page: int = 0):
    """Показывает список категорий."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Определяем, какие категории показывать
        if parent_id is None:
            # Показываем основные категории
            categories = await db.fetch_all(
                """SELECT c.*, 
                   (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id) as products_count,
                   (SELECT COUNT(*) FROM categories WHERE parent_id = c.id) as subcategories_count
                   FROM categories c 
                   WHERE c.parent_id IS NULL 
                   ORDER BY c.sort_order, c.name 
                   LIMIT 20 OFFSET ?""",
                (page * 20,)
            )
            title = "📁 Основные категории"
        else:
            # Показываем подкатегории
            categories = await db.fetch_all(
                """SELECT c.*, 
                   (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id) as products_count
                   FROM categories c 
                   WHERE c.parent_id = ? 
                   ORDER BY c.sort_order, c.name 
                   LIMIT 20 OFFSET ?""",
                (parent_id, page * 20)
            )
            parent_cat = await db.fetch_one("SELECT name FROM categories WHERE id = ?", (parent_id,))
            title = f"📂 Подкатегории: {parent_cat['name'] if parent_cat else 'N/A'}"
        
        await db.disconnect()
        
        if not categories:
            text = f"<b>{title}</b>\n\nКатегорий не найдено."
            keyboard_buttons = []
            if parent_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(text="◀️ Назад к основным", callback_data="admin_categories_list")
                ])
            keyboard_buttons.append([
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="admin_categories_menu")
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except Exception:
                await callback.message.answer(text, reply_markup=keyboard)
            await callback.answer()
            return
        
        text = f"<b>{title}</b>\n\n"
        keyboard_buttons = []
        
        for cat in categories[:10]:  # Показываем первые 10
            icon = cat.get("icon") or "📂"
            products_count = cat.get("products_count", 0)
            subcategories_count = cat.get("subcategories_count", 0) if parent_id is None else 0
            
            text += f"{icon} <b>{cat['name']}</b>\n"
            text += f"   📦 Товаров: {products_count}"
            if subcategories_count > 0:
                text += f" | 📂 Подкатегорий: {subcategories_count}"
            text += "\n\n"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{icon} {cat['name'][:30]}",
                    callback_data=f"admin_category_view_{cat['id']}"
                )
            ])
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="◀️ Предыдущие", callback_data=f"admin_categories_list_page_{page-1}")
            )
        if len(categories) == 20:
            nav_buttons.append(
                InlineKeyboardButton(text="Следующие ▶️", callback_data=f"admin_categories_list_page_{page+1}")
            )
        if nav_buttons:
            keyboard_buttons.append(nav_buttons)
        
        # Кнопки возврата
        back_buttons = []
        if parent_id:
            back_buttons.append(
                InlineKeyboardButton(text="◀️ Назад к основным", callback_data="admin_categories_list")
            )
        back_buttons.append(
            InlineKeyboardButton(text="◀️ Назад в меню", callback_data="admin_categories_menu")
        )
        keyboard_buttons.append(back_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing categories list: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке списка категорий.", show_alert=True)


async def show_category_details(callback: CallbackQuery, bot: Bot, category_id: int):
    """Показывает детали категории."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        category = await db.fetch_one(
            """SELECT c.*, 
               (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id) as products_count,
               (SELECT COUNT(*) FROM categories WHERE parent_id = c.id) as subcategories_count
               FROM categories c 
               WHERE c.id = ?""",
            (category_id,)
        )
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            await db.disconnect()
            return
        
        # Получаем родительскую категорию, если есть
        parent_name = None
        if category.get("parent_id"):
            parent = await db.fetch_one(
                "SELECT name FROM categories WHERE id = ?",
                (category["parent_id"],)
            )
            parent_name = parent["name"] if parent else None
        
        # Получаем подкатегории
        subcategories = await db.fetch_all(
            "SELECT id, name, icon FROM categories WHERE parent_id = ? ORDER BY sort_order, name",
            (category_id,)
        )
        
        await db.disconnect()
        
        icon = category.get("icon") or "📂"
        is_main = category.get("parent_id") is None
        
        text = f"""
<b>{icon} {category['name']}</b>

<b>Информация:</b>
{'📁 Основная категория' if is_main else f'📂 Подкатегория (родитель: {parent_name})'}
📦 Товаров: {category.get('products_count', 0)}
{'📂 Подкатегорий: ' + str(category.get('subcategories_count', 0)) if is_main else ''}
🔢 Порядок сортировки: {category.get('sort_order', 0)}
"""
        
        if category.get("description"):
            text += f"\n<b>Описание:</b> {category['description']}\n"
        
        if category.get("photo_url"):
            text += f"\n📷 Фото: загружено\n"
        
        if subcategories:
            text += f"\n<b>Подкатегории:</b>\n"
            for sub in subcategories[:5]:
                sub_icon = sub.get("icon") or "📂"
                text += f"  {sub_icon} {sub['name']}\n"
            if len(subcategories) > 5:
                text += f"  ... и еще {len(subcategories) - 5}\n"
        
        keyboard_buttons = []
        
        # Кнопки действий
        if category.get('products_count', 0) == 0:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin_category_delete_{category_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="⚠️ Удалить (есть товары)", 
                    callback_data=f"admin_category_delete_confirm_{category_id}"
                )
            ])
        
        if subcategories:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="📂 Показать подкатегории", 
                    callback_data=f"admin_categories_list_parent_{category_id}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_categories_list")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Если есть фото, отправляем фото с подписью
        if category.get("photo_url"):
            try:
                # photo_url начинается с /media/, убираем это и ищем в UPLOADS_DIR
                relative_path = category["photo_url"].replace("/media/", "")
                photo_path = settings.UPLOADS_DIR / relative_path
                print(f"[CATEGORY DETAILS] Looking for photo at: {photo_path}")
                if photo_path.exists():
                    await callback.message.delete()
                    await bot.send_photo(
                        chat_id=callback.message.chat.id,
                        photo=FSInputFile(str(photo_path)),
                        caption=text,
                        reply_markup=keyboard
                    )
                else:
                    print(f"[CATEGORY DETAILS] Photo not found at: {photo_path}")
                    await callback.message.edit_text(text, reply_markup=keyboard)
            except Exception as photo_error:
                print(f"Error sending photo: {photo_error}")
                await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard)
        
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing category details: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке категории.", show_alert=True)


async def start_create_category(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начинает процесс создания категории."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Основная категория", callback_data="category_type:main")],
        [InlineKeyboardButton(text="📂 Подкатегория", callback_data="category_type:sub")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="category_cancel")]
    ])
    
    text = """
<b>➕ Создание категории</b>

Выберите тип категории:
• <b>Основная категория</b> - будет запрошено название и фото
• <b>Подкатегория</b> - будет запрошено только название (и выбор родительской категории)
"""
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await state.set_state(CategoryCreateStates.waiting_for_type)
    await callback.answer()


@router.callback_query(F.data.startswith("category_type:"), CategoryCreateStates.waiting_for_type)
async def process_category_type(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обрабатывает выбор типа категории."""
    category_type = callback.data.split(":")[1]
    await state.update_data(category_type=category_type)
    await callback.answer()
    
    if category_type == "main":
        text = """
<b>Шаг 1/4: Название категории</b>

Введите название основной категории:
"""
        try:
            await callback.message.edit_text(text)
        except Exception:
            await callback.message.answer(text)
        await callback.message.answer(
            "Введите название категории:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CategoryCreateStates.waiting_for_name)
    else:  # subcategory
        # Сначала выбираем родительскую категорию
        try:
            db = await get_db()
            main_categories = await db.fetch_all(
                "SELECT id, name, icon FROM categories WHERE parent_id IS NULL ORDER BY sort_order, name"
            )
            await db.disconnect()
            
            if not main_categories:
                await callback.message.edit_text(
                    "❌ Нет основных категорий. Сначала создайте основную категорию.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_categories_menu")]
                    ])
                )
                await state.clear()
                return
            
            keyboard_buttons = []
            for cat in main_categories[:10]:
                icon = cat.get("icon") or "📁"
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"{icon} {cat['name']}",
                        callback_data=f"category_parent_{cat['id']}"
                    )
                ])
            keyboard_buttons.append([
                InlineKeyboardButton(text="❌ Отменить", callback_data="category_cancel")
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            text = """
<b>Шаг 1/4: Родительская категория</b>

Выберите основную категорию для подкатегории:
"""
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except Exception:
                await callback.message.answer(text, reply_markup=keyboard)
            await state.set_state(CategoryCreateStates.waiting_for_parent_id)
        except Exception as e:
            print(f"Error loading parent categories: {e}")
            await callback.message.answer("❌ Ошибка при загрузке категорий.")


@router.callback_query(F.data.startswith("category_parent_"), CategoryCreateStates.waiting_for_parent_id)
async def process_parent_category(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обрабатывает выбор родительской категории."""
    parent_id = int(callback.data.split("_")[2])
    await state.update_data(parent_id=parent_id)
    await callback.answer()
    
    text = """
<b>Шаг 2/3: Название подкатегории</b>

Введите название подкатегории:
"""
    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)
    await callback.message.answer(
        "Введите название подкатегории:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CategoryCreateStates.waiting_for_name)


@router.message(CategoryCreateStates.waiting_for_name, F.text != "❌ Отменить")
async def process_category_name(message: Message, state: FSMContext):
    """Обрабатывает название категории."""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 255:
        await message.answer("❌ Название должно содержать от 2 до 255 символов. Попробуйте еще раз:")
        return
    
    data = await state.get_data()
    category_type = data.get("category_type")
    
    await state.update_data(name=name)
    
    if category_type == "main":
        # Для основной категории запрашиваем фото
        await message.answer(
            "<b>Шаг 2/4: Фото категории</b>\n\n"
            "Отправьте фото для категории (JPG, PNG):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CategoryCreateStates.waiting_for_photo)
    else:
        # Для подкатегории переходим к описанию
        await message.answer(
            "<b>Шаг 3/3: Описание (необязательно)</b>\n\n"
            "Введите описание подкатегории или '-' для пропуска:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CategoryCreateStates.waiting_for_description)


@router.message(CategoryCreateStates.waiting_for_photo, F.photo)
async def process_category_photo(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает фото категории."""
    try:
        # Скачиваем фото
        photo = message.photo[-1]  # Берем самое большое фото
        file = await bot.get_file(photo.file_id)
        
        # Создаем директорию для фото категорий в UPLOADS_DIR
        categories_dir = settings.UPLOADS_DIR / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя файла
        file_hash = hashlib.md5(f"{photo.file_id}_{message.from_user.id}".encode()).hexdigest()[:12]
        extension = Path(file.file_path).suffix or ".jpg"
        filename = f"category_{file_hash}{extension}"
        file_path = categories_dir / filename
        
        # Скачиваем и сохраняем файл
        await bot.download_file(file.file_path, str(file_path))
        print(f"[CATEGORY PHOTO] Saved to: {file_path}")
        
        # Сохраняем путь в state (относительно /media/)
        photo_url = f"/media/categories/{filename}"
        await state.update_data(photo_url=photo_url)
        print(f"[CATEGORY PHOTO] URL: {photo_url}")
        
        await message.answer(
            "<b>Шаг 3/4: Описание (необязательно)</b>\n\n"
            "Введите описание категории или '-' для пропуска:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CategoryCreateStates.waiting_for_description)
        
    except Exception as e:
        print(f"Error processing category photo: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Ошибка при сохранении фото. Попробуйте еще раз или отправьте '-' для пропуска:")


@router.message(CategoryCreateStates.waiting_for_photo, F.document)
async def process_category_photo_document(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает фото как документ (PNG файлы часто отправляются так)."""
    try:
        document = message.document
        mime_type = document.mime_type or ""
        
        # Проверяем, что это изображение
        if not mime_type.startswith("image/"):
            await message.answer("❌ Пожалуйста, отправьте изображение (JPG, PNG, WEBP) или '-' для пропуска:")
            return
        
        file = await bot.get_file(document.file_id)
        
        # Создаем директорию для фото категорий
        categories_dir = settings.UPLOADS_DIR / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя файла
        file_hash = hashlib.md5(f"{document.file_id}_{message.from_user.id}".encode()).hexdigest()[:12]
        original_name = document.file_name or "category.png"
        extension = Path(original_name).suffix or ".png"
        filename = f"category_{file_hash}{extension}"
        file_path = categories_dir / filename
        
        # Скачиваем и сохраняем файл
        await bot.download_file(file.file_path, str(file_path))
        print(f"[CATEGORY PHOTO DOC] Saved to: {file_path}")
        
        # Сохраняем путь в state
        photo_url = f"/media/categories/{filename}"
        await state.update_data(photo_url=photo_url)
        print(f"[CATEGORY PHOTO DOC] URL: {photo_url}")
        
        await message.answer(
            "<b>Шаг 3/4: Описание (необязательно)</b>\n\n"
            "Введите описание категории или '-' для пропуска:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CategoryCreateStates.waiting_for_description)
        
    except Exception as e:
        print(f"Error processing category photo document: {e}")
        import traceback
        traceback.print_exc()
        await message.answer("❌ Ошибка при сохранении фото. Попробуйте еще раз или отправьте '-' для пропуска:")


@router.message(CategoryCreateStates.waiting_for_photo, ~F.photo, ~F.document)
async def process_category_photo_skip(message: Message, state: FSMContext):
    """Обрабатывает пропуск фото."""
    if message.text == "❌ Отменить":
        return
    
    await state.update_data(photo_url=None)
    await message.answer(
        "<b>Шаг 3/4: Описание (необязательно)</b>\n\n"
        "Введите описание категории или '-' для пропуска:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CategoryCreateStates.waiting_for_description)


@router.message(CategoryCreateStates.waiting_for_description, F.text != "❌ Отменить")
async def process_category_description(message: Message, state: FSMContext):
    """Обрабатывает описание категории."""
    description = message.text.strip()
    if description == "-":
        description = None
    
    await state.update_data(description=description)
    
    data = await state.get_data()
    category_type = data.get("category_type")
    
    if category_type == "main":
        # Для основной категории запрашиваем порядок сортировки
        await message.answer(
            "<b>Шаг 4/4: Порядок сортировки</b>\n\n"
            "Введите число для порядка сортировки (меньше = выше в списке, по умолчанию 0):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(CategoryCreateStates.waiting_for_sort_order)
    else:
        # Для подкатегории сохраняем
        await save_category(message, state, bot=None)


@router.message(CategoryCreateStates.waiting_for_sort_order, F.text != "❌ Отменить")
async def process_category_sort_order(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает порядок сортировки и сохраняет категорию."""
    try:
        sort_order = int(message.text.strip()) if message.text.strip() else 0
        await state.update_data(sort_order=sort_order)
        await save_category(message, state, bot)
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте еще раз:")


async def save_category(message: Message, state: FSMContext, bot: Bot = None):
    """Сохраняет категорию в базу данных."""
    try:
        data = await state.get_data()
        db = await get_db()
        
        # Генерируем slug из названия
        name = data["name"]
        slug = name.lower().replace(" ", "-").replace("ё", "е")
        # Убираем все не-латинские и не-кириллические символы
        slug = "".join(c if c.isalnum() or c == "-" else "" for c in slug)
        
        # Проверяем уникальность slug
        existing = await db.fetch_one("SELECT id FROM categories WHERE slug = ?", (slug,))
        if existing:
            counter = 1
            while True:
                new_slug = f"{slug}-{counter}"
                existing = await db.fetch_one("SELECT id FROM categories WHERE slug = ?", (new_slug,))
                if not existing:
                    slug = new_slug
                    break
                counter += 1
        
        category_data = {
            "name": name,
            "slug": slug,
            "description": data.get("description"),
            "sort_order": data.get("sort_order", 0),
            "parent_id": data.get("parent_id")
        }
        
        # Добавляем photo_url только если он есть
        if data.get("photo_url"):
            category_data["photo_url"] = data.get("photo_url")
        
        category_id = await db.insert("categories", category_data)
        await db.commit()
        await db.disconnect()
        
        category_type_text = "основную категорию" if data.get("category_type") == "main" else "подкатегорию"
        
        text = f"""
✅ <b>Категория успешно создана!</b>

<b>ID:</b> {category_id}
<b>Название:</b> {name}
<b>Тип:</b> {category_type_text}
"""
        if data.get("photo_url"):
            text += f"<b>Фото:</b> загружено\n"
        
        if message:
            await message.answer(text, reply_markup=ReplyKeyboardRemove())
        elif bot:
            # Если вызывается из callback, отправляем новое сообщение
            pass
        
        await state.clear()
        
    except Exception as e:
        print(f"Error saving category: {e}")
        import traceback
        traceback.print_exc()
        if message:
            await message.answer(
                f"❌ Ошибка при создании категории: {str(e)}\n\nПопробуйте еще раз.",
                reply_markup=ReplyKeyboardRemove()
            )
        await state.clear()


async def delete_category_confirm(callback: CallbackQuery, bot: Bot, category_id: int):
    """Подтверждает удаление категории с товарами."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Проверяем количество товаров
        products_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE category_id = ?",
            (category_id,)
        )
        products_count = products_count["cnt"] if products_count else 0
        
        # Проверяем подкатегории
        subcategories = await db.fetch_all(
            "SELECT id, name FROM categories WHERE parent_id = ?",
            (category_id,)
        )
        
        category = await db.fetch_one("SELECT name FROM categories WHERE id = ?", (category_id,))
        category_name = category["name"] if category else "N/A"
        
        await db.disconnect()
        
        if products_count == 0 and len(subcategories) == 0:
            # Можно удалить безопасно
            await delete_category(callback, bot, category_id)
            return
        
        # Показываем предупреждение
        text = f"""
⚠️ <b>Внимание!</b>

Категория <b>"{category_name}"</b> содержит:
• 📦 Товаров: {products_count}
"""
        if subcategories:
            text += f"• 📂 Подкатегорий: {len(subcategories)}\n"
        
        text += "\n<b>Варианты действий:</b>\n"
        text += "1. <b>Удалить категорию</b> - товары останутся без категории\n"
        text += "2. <b>Перенести товары</b> - выберите другую категорию\n"
        text += "3. <b>Отменить</b> - вернуться назад"
        
        keyboard_buttons = []
        
        if products_count > 0:
            # Получаем список категорий для переноса
            db = await get_db()
            other_categories = await db.fetch_all(
                "SELECT id, name, icon FROM categories WHERE id != ? ORDER BY name",
                (category_id,)
            )
            await db.disconnect()
            
            if other_categories:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="📦 Перенести товары",
                        callback_data=f"admin_category_move_products_{category_id}"
                    )
                ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🗑️ Удалить все равно",
                callback_data=f"admin_category_delete_force_{category_id}"
            )
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_category_view_{category_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error confirming category deletion: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при проверке категории.", show_alert=True)


async def delete_category(callback: CallbackQuery, bot: Bot, category_id: int, force: bool = False):
    """Удаляет категорию."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        category = await db.fetch_one("SELECT name, photo_url FROM categories WHERE id = ?", (category_id,))
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            await db.disconnect()
            return
        
        # Если есть фото, удаляем файл
        if category.get("photo_url"):
            try:
                # photo_url начинается с /media/, убираем это и ищем в UPLOADS_DIR
                relative_path = category["photo_url"].replace("/media/", "")
                photo_path = settings.UPLOADS_DIR / relative_path
                if photo_path.exists():
                    photo_path.unlink()
                    print(f"[CATEGORY DELETE] Deleted photo: {photo_path}")
            except Exception as e:
                print(f"Error deleting photo: {e}")
        
        # Удаляем категорию (CASCADE удалит подкатегории)
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()
        await db.disconnect()
        
        await callback.answer("✅ Категория удалена")
        
        # Возвращаемся к списку категорий
        await show_categories_list(callback, bot)
        
    except Exception as e:
        print(f"Error deleting category: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при удалении категории.", show_alert=True)


# Обработчики callback'ов
@router.callback_query(F.data == "admin_categories_menu")
async def handle_categories_menu(callback: CallbackQuery, bot: Bot):
    """Обрабатывает переход в меню категорий."""
    await show_categories_menu(callback, bot)


@router.callback_query(F.data == "admin_categories_list")
async def handle_categories_list(callback: CallbackQuery, bot: Bot):
    """Обрабатывает показ списка категорий."""
    await show_categories_list(callback, bot)


@router.callback_query(F.data.startswith("admin_categories_list_page_"))
async def handle_categories_list_page(callback: CallbackQuery, bot: Bot):
    """Обрабатывает пагинацию списка категорий."""
    page = int(callback.data.split("_")[4])
    await show_categories_list(callback, bot, page=page)


@router.callback_query(F.data.startswith("admin_categories_list_parent_"))
async def handle_categories_list_parent(callback: CallbackQuery, bot: Bot):
    """Обрабатывает показ подкатегорий."""
    parent_id = int(callback.data.split("_")[4])
    await show_categories_list(callback, bot, parent_id=parent_id)


@router.callback_query(F.data.startswith("admin_category_view_"))
async def handle_category_view(callback: CallbackQuery, bot: Bot):
    """Обрабатывает просмотр категории."""
    category_id = int(callback.data.split("_")[3])
    await show_category_details(callback, bot, category_id)


async def move_products_to_category(callback: CallbackQuery, bot: Bot, from_category_id: int):
    """Показывает список категорий для переноса товаров."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Получаем информацию о категории
        from_category = await db.fetch_one("SELECT name FROM categories WHERE id = ?", (from_category_id,))
        if not from_category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            await db.disconnect()
            return
        
        # Получаем количество товаров
        products_count = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM products WHERE category_id = ?",
            (from_category_id,)
        )
        products_count = products_count["cnt"] if products_count else 0
        
        # Получаем список других категорий
        other_categories = await db.fetch_all(
            "SELECT id, name, icon FROM categories WHERE id != ? ORDER BY name",
            (from_category_id,)
        )
        await db.disconnect()
        
        if not other_categories:
            await callback.answer("❌ Нет других категорий для переноса", show_alert=True)
            return
        
        text = f"""
<b>📦 Перенос товаров</b>

Категория: <b>{from_category['name']}</b>
Товаров для переноса: {products_count}

Выберите категорию, в которую перенести товары:
"""
        
        keyboard_buttons = []
        for cat in other_categories[:15]:  # Показываем до 15 категорий
            icon = cat.get("icon") or "📂"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{icon} {cat['name']}",
                    callback_data=f"admin_category_move_to_{from_category_id}_{cat['id']}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_category_view_{from_category_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        print(f"Error showing move products menu: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при загрузке категорий.", show_alert=True)


async def execute_move_products(callback: CallbackQuery, bot: Bot, from_category_id: int, to_category_id: int):
    """Переносит товары из одной категории в другую."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    try:
        db = await get_db()
        
        # Проверяем категории
        from_category = await db.fetch_one("SELECT name FROM categories WHERE id = ?", (from_category_id,))
        to_category = await db.fetch_one("SELECT name FROM categories WHERE id = ?", (to_category_id,))
        
        if not from_category or not to_category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            await db.disconnect()
            return
        
        # Переносим товары
        result = await db.execute(
            "UPDATE products SET category_id = ? WHERE category_id = ?",
            (to_category_id, from_category_id)
        )
        await db.commit()
        
        # Получаем количество перенесенных товаров
        moved_count = result.rowcount if hasattr(result, 'rowcount') else 0
        
        await db.disconnect()
        
        await callback.answer(f"✅ Перенесено товаров: {moved_count}")
        
        # Возвращаемся к деталям категории
        await show_category_details(callback, bot, from_category_id)
        
    except Exception as e:
        print(f"Error moving products: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при переносе товаров.", show_alert=True)


@router.callback_query(F.data.startswith("admin_category_delete_"))
async def handle_category_delete(callback: CallbackQuery, bot: Bot):
    """Обрабатывает удаление категории."""
    try:
        parts = callback.data.split("_")
        print(f"[CATEGORIES_ADMIN] Callback data: {callback.data}, parts: {parts}")
        
        # Парсим category_id в зависимости от формата callback_data
        # Форматы: admin_category_delete_{id}, admin_category_delete_confirm_{id}, admin_category_delete_force_{id}
        if "confirm" in callback.data:
            category_id = int(parts[4])  # admin_category_delete_confirm_{id}
            print(f"[CATEGORIES_ADMIN] Confirm delete, category_id: {category_id}")
            await delete_category_confirm(callback, bot, category_id)
        elif "force" in callback.data:
            category_id = int(parts[4])  # admin_category_delete_force_{id}
            print(f"[CATEGORIES_ADMIN] Force delete, category_id: {category_id}")
            await delete_category(callback, bot, category_id, force=True)
        else:
            category_id = int(parts[3])  # admin_category_delete_{id}
            print(f"[CATEGORIES_ADMIN] Delete, category_id: {category_id}")
            await delete_category(callback, bot, category_id)
    except Exception as e:
        print(f"[CATEGORIES_ADMIN] Error in handle_category_delete: {e}")
        import traceback
        traceback.print_exc()
        await callback.answer("❌ Ошибка при обработке удаления категории.", show_alert=True)


@router.callback_query(F.data.startswith("admin_category_move_products_"))
async def handle_move_products(callback: CallbackQuery, bot: Bot):
    """Обрабатывает начало переноса товаров."""
    from_category_id = int(callback.data.split("_")[4])
    await move_products_to_category(callback, bot, from_category_id)


@router.callback_query(F.data.startswith("admin_category_move_to_"))
async def handle_move_to_category(callback: CallbackQuery, bot: Bot):
    """Обрабатывает выбор категории для переноса."""
    parts = callback.data.split("_")
    from_category_id = int(parts[4])
    to_category_id = int(parts[5])
    await execute_move_products(callback, bot, from_category_id, to_category_id)


@router.callback_query(F.data == "admin_category_create")
async def handle_category_create(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Обрабатывает создание категории."""
    await start_create_category(callback, bot, state)


@router.callback_query(F.data == "category_cancel")
async def handle_category_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание категории."""
    await state.clear()
    await callback.message.edit_text("❌ Создание категории отменено.")
    await callback.answer()


@router.message(F.text == "❌ Отменить")
async def handle_cancel_message(message: Message, state: FSMContext):
    """Отменяет текущее действие."""
    current_state = await state.get_state()
    if current_state and "CategoryCreateStates" in str(current_state):
        await state.clear()
        await message.answer(
            "❌ Создание категории отменено.",
            reply_markup=ReplyKeyboardRemove()
        )


#!/usr/bin/env python3
"""
Скрипт для обновления иконок категорий в базе данных.
"""

import sqlite3
import os
from pathlib import Path

# Путь к базе данных
DB_PATH = Path(__file__).parent.parent / "data" / "app.db"

def update_category_icons():
    """Обновляет иконки категорий в базе данных."""
    
    if not DB_PATH.exists():
        print(f"❌ База данных не найдена: {DB_PATH}")
        print("   Создайте базу данных через init_db.py или запустите приложение")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Обновление главных категорий
        updates = [
            ('🌷', 'flowers', 'Цветы'),
            ('🪴', 'houseplants', 'Комнатные растения'),
            ('🧁', 'bakery', 'Кондитерские и пекарни'),
            ('🍓', 'edible-bouquets', 'Съедобные букеты'),
            ('🎁', 'tasty-sets', 'Вкусные наборы'),
            ('☕', 'tea-coffee-sets', 'Наборы чая и кофе'),
            ('⭐', 'misc', 'Разное'),
        ]
        
        print("🔄 Обновление иконок категорий...")
        
        for icon, slug, name in updates:
            cursor.execute(
                "UPDATE categories SET icon = ? WHERE slug = ?",
                (icon, slug)
            )
            if cursor.rowcount > 0:
                print(f"  ✅ {name}: {icon}")
            else:
                print(f"  ⚠️  Категория '{name}' (slug: {slug}) не найдена")
        
        # Обновление подкатегорий
        subcategory_updates = [
            ('🧺', 'fruit-baskets', 'Фруктовые корзины'),
        ]
        
        for icon, slug, name in subcategory_updates:
            cursor.execute(
                "UPDATE categories SET icon = ? WHERE slug = ?",
                (icon, slug)
            )
            if cursor.rowcount > 0:
                print(f"  ✅ {name}: {icon}")
        
        conn.commit()
        print("\n✅ Иконки категорий успешно обновлены!")
        
        # Показываем статистику
        cursor.execute("SELECT COUNT(*) FROM categories WHERE icon IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"📊 Всего категорий с иконками: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("  Обновление иконок категорий")
    print("=" * 50)
    print()
    
    success = update_category_icons()
    
    if success:
        print("\n💡 Для применения изменений перезапустите сервер или обновите страницу")
    else:
        print("\n⚠️  Не удалось обновить иконки. Проверьте ошибки выше.")
    
    print()




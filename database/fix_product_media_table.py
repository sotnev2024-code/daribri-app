#!/usr/bin/env python3
"""
Скрипт для исправления структуры таблицы product_media.
Добавляет недостающие колонки или пересоздает таблицу с правильной структурой.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def fix_product_media_table():
    """Исправляет структуру таблицы product_media."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("ИСПРАВЛЕНИЕ ТАБЛИЦЫ product_media")
    print("=" * 60)
    
    # Проверяем, существует ли таблица
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='product_media'
    """)
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("\n[INFO] Таблица product_media не существует. Создаем...")
        cursor.execute("""
            CREATE TABLE product_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail_url TEXT,
                sort_order INTEGER DEFAULT 0,
                is_primary INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        """)
        print("   ✅ Таблица product_media создана")
    else:
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(product_media)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        print(f"\n[INFO] Таблица product_media существует")
        print(f"   Текущие колонки: {', '.join(columns.keys())}")
        
        # Проверяем и добавляем недостающие колонки
        changes = False
        
        if 'url' not in columns:
            print("\n[1/4] Добавление колонки url...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN url TEXT")
            # Если есть file_path, копируем данные
            if 'file_path' in columns:
                cursor.execute("UPDATE product_media SET url = file_path WHERE url IS NULL")
            changes = True
            print("   ✅ Колонка url добавлена")
        
        if 'media_type' not in columns:
            print("\n[2/4] Добавление колонки media_type...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN media_type TEXT")
            # Если есть file_type, копируем данные
            if 'file_type' in columns:
                cursor.execute("UPDATE product_media SET media_type = file_type WHERE media_type IS NULL")
            else:
                cursor.execute("UPDATE product_media SET media_type = 'photo' WHERE media_type IS NULL")
            changes = True
            print("   ✅ Колонка media_type добавлена")
        
        if 'is_primary' not in columns:
            print("\n[3/4] Добавление колонки is_primary...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN is_primary INTEGER DEFAULT 0")
            # Первый медиа для каждого товара делаем primary
            cursor.execute("""
                UPDATE product_media
                SET is_primary = 1
                WHERE id IN (
                    SELECT MIN(id) 
                    FROM product_media 
                    GROUP BY product_id
                )
            """)
            changes = True
            print("   ✅ Колонка is_primary добавлена")
        
        if 'thumbnail_url' not in columns:
            print("\n[4/4] Добавление колонки thumbnail_url...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN thumbnail_url TEXT")
            changes = True
            print("   ✅ Колонка thumbnail_url добавлена")
        
        if 'sort_order' not in columns:
            print("\n[5/5] Добавление колонки sort_order...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN sort_order INTEGER DEFAULT 0")
            # Если есть display_order, копируем данные
            if 'display_order' in columns:
                cursor.execute("UPDATE product_media SET sort_order = display_order WHERE sort_order IS NULL")
            changes = True
            print("   ✅ Колонка sort_order добавлена")
        
        if not changes:
            print("\n✅ Таблица product_media уже имеет правильную структуру")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ ТАБЛИЦА product_media ИСПРАВЛЕНА")
    print("=" * 60)


if __name__ == "__main__":
    fix_product_media_table()


#!/usr/bin/env python3
"""
Универсальный скрипт для проверки и исправления всех таблиц базы данных.
Исправляет структуру таблиц, добавляя недостающие колонки.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def check_and_fix_table(cursor, table_name, required_columns):
    """
    Проверяет и исправляет структуру таблицы.
    
    Args:
        cursor: Курсор базы данных
        table_name: Имя таблицы
        required_columns: Словарь {column_name: (type, default, nullable)}
    """
    # Проверяем, существует ли таблица
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print(f"\n[INFO] Таблица {table_name} не существует. Пропускаем.")
        return False
    
    # Получаем текущие колонки
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {col[1]: col[2] for col in cursor.fetchall()}
    
    changes = False
    for col_name, (col_type, default, nullable) in required_columns.items():
        if col_name not in existing_columns:
            print(f"\n   [+] Добавление колонки {col_name}...")
            nullable_clause = "" if not nullable else ""
            default_clause = f" DEFAULT {default}" if default else ""
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{default_clause}")
            changes = True
            print(f"      ✅ Колонка {col_name} добавлена")
    
    return changes


def fix_all_tables():
    """Исправляет структуру всех таблиц."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("ПРОВЕРКА И ИСПРАВЛЕНИЕ ВСЕХ ТАБЛИЦ")
    print("=" * 60)
    
    # Исправляем product_media
    print("\n[1] Проверка таблицы product_media...")
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='product_media'
    """)
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("   [INFO] Таблица product_media не существует. Создаем...")
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
        print("      ✅ Таблица product_media создана")
    else:
        # Проверяем структуру
        cursor.execute("PRAGMA table_info(product_media)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        print(f"   Текущие колонки: {', '.join(columns.keys())}")
        
        if 'url' not in columns:
            print("   [+] Добавление колонки url...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN url TEXT")
            if 'file_path' in columns:
                cursor.execute("UPDATE product_media SET url = file_path WHERE url IS NULL")
            print("      ✅ Колонка url добавлена")
        
        if 'media_type' not in columns:
            print("   [+] Добавление колонки media_type...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN media_type TEXT")
            if 'file_type' in columns:
                cursor.execute("UPDATE product_media SET media_type = file_type WHERE media_type IS NULL")
            else:
                cursor.execute("UPDATE product_media SET media_type = 'photo' WHERE media_type IS NULL")
            print("      ✅ Колонка media_type добавлена")
        
        if 'is_primary' not in columns:
            print("   [+] Добавление колонки is_primary...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN is_primary INTEGER DEFAULT 0")
            cursor.execute("""
                UPDATE product_media
                SET is_primary = 1
                WHERE id IN (
                    SELECT MIN(id) 
                    FROM product_media 
                    GROUP BY product_id
                )
            """)
            print("      ✅ Колонка is_primary добавлена")
        
        if 'thumbnail_url' not in columns:
            print("   [+] Добавление колонки thumbnail_url...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN thumbnail_url TEXT")
            print("      ✅ Колонка thumbnail_url добавлена")
        
        if 'sort_order' not in columns:
            print("   [+] Добавление колонки sort_order...")
            cursor.execute("ALTER TABLE product_media ADD COLUMN sort_order INTEGER DEFAULT 0")
            if 'display_order' in columns:
                cursor.execute("UPDATE product_media SET sort_order = display_order WHERE sort_order IS NULL")
            print("      ✅ Колонка sort_order добавлена")
    
    # Проверяем другие таблицы
    print("\n[2] Проверка других таблиц...")
    
    tables_to_check = [
        ('users', [
            ('telegram_id', ('INTEGER', None, False)),
            ('username', ('TEXT', None, True)),
            ('full_name', ('TEXT', None, True)),
            ('phone', ('TEXT', None, True)),
        ]),
        ('shops', [
            ('is_active', ('INTEGER', '1', False)),
            ('photo_url', ('TEXT', None, True)),
        ]),
        ('products', [
            ('is_active', ('INTEGER', '1', False)),
            ('is_trending', ('INTEGER', '0', False)),
        ]),
        ('categories', [
            ('is_active', ('INTEGER', '1', False)),
        ]),
    ]
    
    for table_name, required_columns in tables_to_check:
        changes = check_and_fix_table(cursor, table_name, dict(required_columns))
        if changes:
            print(f"   ✅ Таблица {table_name} исправлена")
        else:
            print(f"   ✓ Таблица {table_name} в порядке")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    fix_all_tables()


#!/usr/bin/env python3
"""
Скрипт для исправления таблицы promos.
Добавляет колонку promo_type если её нет.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def fix_promos_table():
    """Исправляет таблицу promos."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("ИСПРАВЛЕНИЕ ТАБЛИЦЫ promos")
    print("=" * 60)

    # Проверяем существует ли таблица
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='promos'
    """)
    
    if not cursor.fetchone():
        print("\n[INFO] Таблица promos не существует. Создаём...")
        cursor.execute("""
            CREATE TABLE promos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER,
                code TEXT UNIQUE NOT NULL,
                promo_type TEXT NOT NULL CHECK(promo_type IN ('percent', 'fixed', 'free_delivery')),
                discount_type TEXT,
                discount_value DECIMAL(10,2) NOT NULL,
                min_order_amount DECIMAL(10,2),
                max_uses INTEGER,
                uses_count INTEGER DEFAULT 0,
                valid_from TIMESTAMP,
                valid_until TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                first_order_only INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
            )
        """)
        print("   ✅ Таблица promos создана")
    else:
        # Проверяем структуру
        cursor.execute("PRAGMA table_info(promos)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        print(f"\n[INFO] Текущие колонки: {list(columns.keys())}")
        
        # Добавляем promo_type если её нет
        if 'promo_type' not in columns:
            print("\n[1] Добавление колонки promo_type...")
            cursor.execute("ALTER TABLE promos ADD COLUMN promo_type TEXT")
            
            # Копируем данные из discount_type если есть
            if 'discount_type' in columns:
                cursor.execute("UPDATE promos SET promo_type = discount_type WHERE promo_type IS NULL")
            else:
                cursor.execute("UPDATE promos SET promo_type = 'percent' WHERE promo_type IS NULL")
            
            print("   ✅ Колонка promo_type добавлена")
        else:
            print("\n✅ Колонка promo_type уже существует")
        
        # Добавляем discount_type если её нет (для совместимости)
        if 'discount_type' not in columns:
            print("\n[2] Добавление колонки discount_type...")
            cursor.execute("ALTER TABLE promos ADD COLUMN discount_type TEXT")
            
            if 'promo_type' in columns:
                cursor.execute("UPDATE promos SET discount_type = promo_type WHERE discount_type IS NULL")
            
            print("   ✅ Колонка discount_type добавлена")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ ТАБЛИЦА promos ИСПРАВЛЕНА")
    print("=" * 60)


if __name__ == "__main__":
    fix_promos_table()



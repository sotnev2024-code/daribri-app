#!/usr/bin/env python3
"""
Скрипт для добавления колонки delivery_time_slot в таблицу orders.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def fix_delivery_time_column():
    """Добавляет колонку delivery_time_slot."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("ИСПРАВЛЕНИЕ КОЛОНКИ delivery_time_slot")
    print("=" * 60)

    # Проверяем структуру таблицы orders
    cursor.execute("PRAGMA table_info(orders)")
    columns = {col[1]: col[2] for col in cursor.fetchall()}
    
    print(f"\nТекущие колонки: {list(columns.keys())}")

    # Добавляем delivery_time_slot если нет
    if 'delivery_time_slot' not in columns:
        print("\n[1] Добавление колонки delivery_time_slot...")
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_time_slot TEXT")
        
        # Копируем данные из delivery_time если есть
        if 'delivery_time' in columns:
            cursor.execute("UPDATE orders SET delivery_time_slot = delivery_time WHERE delivery_time_slot IS NULL")
            print("   ✅ Данные скопированы из delivery_time")
        
        print("   ✅ Колонка delivery_time_slot добавлена")
    else:
        print("\n✅ Колонка delivery_time_slot уже существует")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ ГОТОВО")
    print("=" * 60)


if __name__ == "__main__":
    fix_delivery_time_column()


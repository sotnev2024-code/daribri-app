#!/usr/bin/env python3
"""
Скрипт для добавления недостающих колонок в таблицу shops.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'miniapp.db')

def fix_shops_table():
    """Добавляет недостающие колонки в таблицу shops."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем текущие колонки
    cursor.execute("PRAGMA table_info(shops)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    print(f"Существующие колонки: {existing_columns}")
    
    # Колонки, которые должны быть
    required_columns = {
        'email': 'TEXT',
        'total_reviews': 'INTEGER DEFAULT 0',
        'redemption_rate': 'REAL DEFAULT 0',
        'is_verified': 'INTEGER DEFAULT 0',
        'average_rating': 'REAL DEFAULT 0',
        'latitude': 'REAL',
        'longitude': 'REAL',
        'telegram': 'TEXT',
        'instagram': 'TEXT',
        'rating': 'REAL DEFAULT 0',
        'reviews_count': 'INTEGER DEFAULT 0',
        'views_count': 'INTEGER DEFAULT 0',
        'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    }
    
    # Добавляем недостающие колонки
    for column, col_type in required_columns.items():
        if column not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE shops ADD COLUMN {column} {col_type}")
                print(f"✅ Добавлена колонка: {column}")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Колонка {column}: {e}")
        else:
            print(f"✓ Колонка {column} уже существует")
    
    conn.commit()
    conn.close()
    print("\n✅ Таблица shops исправлена!")

if __name__ == "__main__":
    fix_shops_table()



#!/usr/bin/env python3
"""
Скрипт для добавления недостающих колонок в базу данных.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def add_column_if_not_exists(cursor, table, column, column_type, default=None):
    """Добавляет колонку если она не существует."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    
    if column not in columns:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}{default_clause}")
        print(f"   ✅ Добавлена колонка {table}.{column}")
        return True
    else:
        print(f"   ✓ Колонка {table}.{column} уже существует")
        return False


def fix_missing_columns():
    """Добавляет все недостающие колонки."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ КОЛОНОК")
    print("=" * 60)
    
    # Проверяем существование таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    changes = False
    
    # Колонки для таблицы products
    print("\n[1] Таблица products:")
    if 'products' in tables:
        changes |= add_column_if_not_exists(cursor, 'products', 'discount_percent', 'INTEGER', 0)
        changes |= add_column_if_not_exists(cursor, 'products', 'is_active', 'INTEGER', 1)
        changes |= add_column_if_not_exists(cursor, 'products', 'is_trending', 'INTEGER', 0)
        changes |= add_column_if_not_exists(cursor, 'products', 'views_count', 'INTEGER', 0)
        changes |= add_column_if_not_exists(cursor, 'products', 'sales_count', 'INTEGER', 0)
    else:
        print("   ❌ Таблица products не найдена!")
    
    # Колонки для таблицы shops
    print("\n[2] Таблица shops:")
    if 'shops' in tables:
        changes |= add_column_if_not_exists(cursor, 'shops', 'average_rating', 'REAL', 0)
        changes |= add_column_if_not_exists(cursor, 'shops', 'rating', 'REAL', 0)
        changes |= add_column_if_not_exists(cursor, 'shops', 'reviews_count', 'INTEGER', 0)
        changes |= add_column_if_not_exists(cursor, 'shops', 'views_count', 'INTEGER', 0)
        changes |= add_column_if_not_exists(cursor, 'shops', 'is_active', 'INTEGER', 1)
        changes |= add_column_if_not_exists(cursor, 'shops', 'photo_url', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shops', 'latitude', 'REAL')
        changes |= add_column_if_not_exists(cursor, 'shops', 'longitude', 'REAL')
    else:
        print("   ❌ Таблица shops не найдена!")
    
    # Колонки для таблицы categories
    print("\n[3] Таблица categories:")
    if 'categories' in tables:
        changes |= add_column_if_not_exists(cursor, 'categories', 'is_active', 'INTEGER', 1)
        changes |= add_column_if_not_exists(cursor, 'categories', 'icon', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'categories', 'slug', 'TEXT')
    else:
        print("   ❌ Таблица categories не найдена!")
    
    # Колонки для таблицы product_media
    print("\n[4] Таблица product_media:")
    if 'product_media' in tables:
        changes |= add_column_if_not_exists(cursor, 'product_media', 'url', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'product_media', 'media_type', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'product_media', 'is_primary', 'INTEGER', 0)
        changes |= add_column_if_not_exists(cursor, 'product_media', 'thumbnail_url', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'product_media', 'sort_order', 'INTEGER', 0)
    else:
        print("   ❌ Таблица product_media не найдена!")
    
    # Колонки для таблицы users
    print("\n[5] Таблица users:")
    if 'users' in tables:
        changes |= add_column_if_not_exists(cursor, 'users', 'phone', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'users', 'is_premium', 'INTEGER', 0)
    else:
        print("   ❌ Таблица users не найдена!")
    
    # Колонки для таблицы shop_requests
    print("\n[6] Таблица shop_requests:")
    if 'shop_requests' in tables:
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'telegram_user_id', 'INTEGER')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'shop_name', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'owner_name', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'phone', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'address', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'city', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'category', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'description', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'status', 'TEXT', "'pending'")
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'admin_comment', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'shop_requests', 'photo_file_id', 'TEXT')
    else:
        print("   ❌ Таблица shop_requests не найдена!")
    
    # Колонки для таблицы orders
    print("\n[7] Таблица orders:")
    if 'orders' in tables:
        changes |= add_column_if_not_exists(cursor, 'orders', 'delivery_address', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'delivery_lat', 'REAL')
        changes |= add_column_if_not_exists(cursor, 'orders', 'delivery_lng', 'REAL')
        changes |= add_column_if_not_exists(cursor, 'orders', 'customer_name', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'customer_phone', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'customer_comment', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'delivery_date', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'delivery_time', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'payment_method', 'TEXT', "'cash'")
        changes |= add_column_if_not_exists(cursor, 'orders', 'promo_code', 'TEXT')
        changes |= add_column_if_not_exists(cursor, 'orders', 'promo_discount', 'REAL')
        changes |= add_column_if_not_exists(cursor, 'orders', 'group_message_id', 'INTEGER')
    else:
        print("   ❌ Таблица orders не найдена!")
    
    # Колонки для таблицы order_items
    print("\n[8] Таблица order_items:")
    if 'order_items' in tables:
        changes |= add_column_if_not_exists(cursor, 'order_items', 'product_name', 'TEXT')
    else:
        print("   ❌ Таблица order_items не найдена!")
    
    # Колонки для таблицы shop_subscriptions
    print("\n[9] Таблица shop_subscriptions:")
    if 'shop_subscriptions' in tables:
        changes |= add_column_if_not_exists(cursor, 'shop_subscriptions', 'payment_id', 'TEXT')
    else:
        print("   ❌ Таблица shop_subscriptions не найдена!")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    if changes:
        print("✅ КОЛОНКИ ДОБАВЛЕНЫ")
    else:
        print("✅ ВСЕ КОЛОНКИ УЖЕ СУЩЕСТВУЮТ")
    print("=" * 60)
    print("\nПерезапустите приложение: systemctl restart daribri")


if __name__ == "__main__":
    fix_missing_columns()


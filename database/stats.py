#!/usr/bin/env python3
"""
Скрипт для просмотра статистики базы данных.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def show_stats():
    """Показывает статистику базы данных."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 60)
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("=" * 60)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Пользователи
    try:
        cursor.execute("SELECT COUNT(*) as count FROM users")
        users_count = cursor.fetchone()["count"]
        print(f"👤 Пользователей: {users_count}")
        
        # Последние 5 пользователей
        cursor.execute("""
            SELECT telegram_id, username, first_name, created_at 
            FROM users ORDER BY created_at DESC LIMIT 5
        """)
        recent_users = cursor.fetchall()
        if recent_users:
            print("   Последние регистрации:")
            for user in recent_users:
                name = user["first_name"] or user["username"] or f"ID:{user['telegram_id']}"
                print(f"   - {name} (@{user['username'] or 'нет'}) - {user['created_at']}")
    except Exception as e:
        print(f"👤 Пользователи: ошибка ({e})")

    print()

    # Магазины
    try:
        cursor.execute("SELECT COUNT(*) as count FROM shops")
        shops_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM shops WHERE is_active = 1")
        active_shops = cursor.fetchone()["count"]
        
        print(f"🏪 Магазинов: {shops_count} (активных: {active_shops})")
        
        # Список магазинов
        cursor.execute("SELECT id, name, is_active FROM shops ORDER BY id")
        shops = cursor.fetchall()
        for shop in shops:
            status = "✅" if shop["is_active"] else "❌"
            print(f"   {status} ID={shop['id']}: {shop['name']}")
    except Exception as e:
        print(f"🏪 Магазины: ошибка ({e})")

    print()

    # Товары
    try:
        cursor.execute("SELECT COUNT(*) as count FROM products")
        products_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
        active_products = cursor.fetchone()["count"]
        
        print(f"📦 Товаров: {products_count} (активных: {active_products})")
    except Exception as e:
        print(f"📦 Товары: ошибка ({e})")

    print()

    # Заказы
    try:
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        orders_count = cursor.fetchone()["count"]
        
        cursor.execute("""
            SELECT status, COUNT(*) as count FROM orders GROUP BY status
        """)
        orders_by_status = cursor.fetchall()
        
        print(f"📋 Заказов: {orders_count}")
        for order in orders_by_status:
            print(f"   - {order['status']}: {order['count']}")
    except Exception as e:
        print(f"📋 Заказы: ошибка ({e})")

    print()

    # Подписки
    try:
        cursor.execute("""
            SELECT COUNT(*) as count FROM shop_subscriptions 
            WHERE is_active = 1 AND end_date > datetime('now')
        """)
        active_subs = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM shop_subscriptions")
        total_subs = cursor.fetchone()["count"]
        
        print(f"💳 Подписок: {total_subs} (активных: {active_subs})")
    except Exception as e:
        print(f"💳 Подписки: ошибка ({e})")

    print()

    # Категории
    try:
        cursor.execute("SELECT COUNT(*) as count FROM categories")
        categories_count = cursor.fetchone()["count"]
        print(f"📁 Категорий: {categories_count}")
    except Exception as e:
        print(f"📁 Категории: ошибка ({e})")

    print()

    # Отзывы
    try:
        cursor.execute("SELECT COUNT(*) as count FROM shop_reviews")
        reviews_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT AVG(rating) as avg FROM shop_reviews")
        avg_rating = cursor.fetchone()["avg"]
        avg_rating = round(avg_rating, 2) if avg_rating else 0
        
        print(f"⭐ Отзывов: {reviews_count} (средняя оценка: {avg_rating})")
    except Exception as e:
        print(f"⭐ Отзывы: ошибка ({e})")

    print()
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    show_stats()


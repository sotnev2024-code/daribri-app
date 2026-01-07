#!/usr/bin/env python3
"""
Скрипт для проверки данных в базе данных.
Помогает диагностировать проблемы с загрузкой данных на сайте.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / "miniapp.db"

def check_database():
    """Проверяет наличие данных в базе."""
    if not DATABASE_PATH.exists():
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("ПРОВЕРКА ДАННЫХ В БАЗЕ")
    print("=" * 60)
    
    # Проверка таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n📊 Найдено таблиц: {len(tables)}")
    print(f"   Таблицы: {', '.join(tables)}")
    
    # Проверка категорий
    cursor.execute("SELECT COUNT(*) FROM categories")
    categories_count = cursor.fetchone()[0]
    print(f"\n📁 Категории: {categories_count}")
    if categories_count > 0:
        cursor.execute("SELECT id, name, is_active FROM categories LIMIT 5")
        for row in cursor.fetchall():
            status = "✅" if row[2] else "❌"
            print(f"   {status} ID={row[0]}: {row[1]}")
    
    # Проверка магазинов
    cursor.execute("SELECT COUNT(*) FROM shops")
    shops_count = cursor.fetchone()[0]
    print(f"\n🏪 Магазины: {shops_count}")
    if shops_count > 0:
        cursor.execute("SELECT id, name, is_active FROM shops LIMIT 5")
        for row in cursor.fetchall():
            status = "✅" if row[2] else "❌"
            print(f"   {status} ID={row[0]}: {row[1]}")
    
    # Проверка подписок
    cursor.execute("SELECT COUNT(*) FROM shop_subscriptions")
    subscriptions_count = cursor.fetchone()[0]
    print(f"\n💳 Подписки (всего): {subscriptions_count}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM shop_subscriptions 
        WHERE is_active = 1 AND end_date > datetime('now')
    """)
    active_subscriptions_count = cursor.fetchone()[0]
    print(f"   ✅ Активных подписок: {active_subscriptions_count}")
    
    if active_subscriptions_count > 0:
        cursor.execute("""
            SELECT ss.id, s.name, ss.start_date, ss.end_date, ss.is_active
            FROM shop_subscriptions ss
            JOIN shops s ON ss.shop_id = s.id
            WHERE ss.is_active = 1 AND ss.end_date > datetime('now')
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"   ✅ ID={row[0]}: {row[1]} (до {row[3]})")
    
    # Проверка товаров
    cursor.execute("SELECT COUNT(*) FROM products")
    products_count = cursor.fetchone()[0]
    print(f"\n📦 Товары (всего): {products_count}")
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
    active_products_count = cursor.fetchone()[0]
    print(f"   ✅ Активных товаров: {active_products_count}")
    
    # Проверка товаров с активными подписками
    cursor.execute("""
        SELECT COUNT(*) FROM products p
        JOIN shops s ON p.shop_id = s.id
        WHERE p.is_active = 1 
        AND s.is_active = 1
        AND EXISTS (
            SELECT 1 FROM shop_subscriptions ss 
            WHERE ss.shop_id = s.id 
            AND ss.is_active = 1 
            AND ss.end_date > datetime('now')
        )
    """)
    visible_products_count = cursor.fetchone()[0]
    print(f"   👁️  Видимых товаров (с активной подпиской): {visible_products_count}")
    
    if visible_products_count == 0 and active_products_count > 0:
        print("\n⚠️  ПРОБЛЕМА: Есть активные товары, но нет активных подписок!")
        print("   Товары не будут отображаться на сайте.")
        print("   Решение: Создайте активную подписку для магазинов.")
    
    # Проверка пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    print(f"\n👤 Пользователи: {users_count}")
    
    # Итоговая диагностика
    print("\n" + "=" * 60)
    print("ДИАГНОСТИКА")
    print("=" * 60)
    
    issues = []
    
    if categories_count == 0:
        issues.append("❌ Нет категорий - сайт не будет работать")
    
    if shops_count == 0:
        issues.append("⚠️  Нет магазинов")
    
    if active_subscriptions_count == 0:
        issues.append("❌ Нет активных подписок - товары не будут отображаться")
    
    if visible_products_count == 0:
        issues.append("❌ Нет видимых товаров - каталог будет пустым")
    
    if not issues:
        print("✅ Все проверки пройдены! Данные в порядке.")
    else:
        print("⚠️  Обнаружены проблемы:")
        for issue in issues:
            print(f"   {issue}")
    
    conn.close()

if __name__ == "__main__":
    check_database()


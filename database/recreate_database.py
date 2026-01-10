#!/usr/bin/env python3
"""
Скрипт для ПОЛНОГО пересоздания базы данных с правильной структурой.
ВНИМАНИЕ: Этот скрипт удалит все данные!
"""

import sqlite3
import os
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"
BACKUP_PATH = Path(__file__).parent / "miniapp.db.backup"


def recreate_database():
    """Полностью пересоздаёт базу данных."""
    
    print("=" * 60)
    print("ПОЛНОЕ ПЕРЕСОЗДАНИЕ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    # Создаём бэкап
    if DATABASE_PATH.exists():
        import shutil
        shutil.copy(DATABASE_PATH, BACKUP_PATH)
        print(f"\n[BACKUP] Создан бэкап: {BACKUP_PATH}")
        
        # Удаляем старую базу
        os.remove(DATABASE_PATH)
        print(f"[DELETE] Удалена старая база данных")
    
    # Создаём новую базу
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем внешние ключи
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("\n[CREATING] Создание таблиц...")
    
    # 1. users
    print("   [1/15] users...")
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT DEFAULT 'ru',
            is_premium INTEGER DEFAULT 0,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. subscription_plans
    print("   [2/15] subscription_plans...")
    cursor.execute("""
        CREATE TABLE subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            duration_days INTEGER NOT NULL,
            max_products INTEGER DEFAULT 50,
            features TEXT DEFAULT '{}',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. categories
    print("   [3/15] categories...")
    cursor.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            name TEXT NOT NULL,
            slug TEXT UNIQUE,
            icon TEXT,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)
    
    # 4. shops
    print("   [4/15] shops...")
    cursor.execute("""
        CREATE TABLE shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            address TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            phone TEXT,
            telegram TEXT,
            instagram TEXT,
            photo_url TEXT,
            is_active INTEGER DEFAULT 1,
            rating REAL DEFAULT 0,
            average_rating REAL DEFAULT 0,
            reviews_count INTEGER DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # 5. shop_subscriptions
    print("   [5/15] shop_subscriptions...")
    cursor.execute("""
        CREATE TABLE shop_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
        )
    """)
    
    # 6. shop_requests (ВАЖНО - правильная структура!)
    print("   [6/15] shop_requests...")
    cursor.execute("""
        CREATE TABLE shop_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            photo_file_id TEXT,
            photo_url TEXT,
            description TEXT,
            address TEXT,
            phone TEXT,
            owner_name TEXT,
            owner_phone TEXT,
            owner_telegram TEXT,
            status TEXT DEFAULT 'pending',
            group_message_id INTEGER,
            shop_id INTEGER,
            admin_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 7. products
    print("   [7/15] products...")
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            discount_price DECIMAL(10, 2),
            discount_percent INTEGER DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            is_trending INTEGER DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            sales_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    
    # 8. product_media
    print("   [8/15] product_media...")
    cursor.execute("""
        CREATE TABLE product_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            media_type TEXT NOT NULL DEFAULT 'photo',
            url TEXT NOT NULL,
            thumbnail_url TEXT,
            sort_order INTEGER DEFAULT 0,
            is_primary INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)
    
    # 9. cart_items
    print("   [9/15] cart_items...")
    cursor.execute("""
        CREATE TABLE cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_id, product_id)
        )
    """)
    
    # 10. favorites
    print("   [10/15] favorites...")
    cursor.execute("""
        CREATE TABLE favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_id, product_id)
        )
    """)
    
    # 11. orders
    print("   [11/15] orders...")
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shop_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            total_amount DECIMAL(10, 2) NOT NULL,
            delivery_address TEXT,
            delivery_lat REAL,
            delivery_lng REAL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_comment TEXT,
            delivery_date TEXT,
            delivery_time TEXT,
            payment_method TEXT DEFAULT 'cash',
            promo_code TEXT,
            promo_discount REAL,
            group_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        )
    """)
    
    # 12. order_items
    print("   [12/15] order_items...")
    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            product_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    """)
    
    # 13. shop_reviews
    print("   [13/15] shop_reviews...")
    cursor.execute("""
        CREATE TABLE shop_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            order_id INTEGER,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
        )
    """)
    
    # 14. promos
    print("   [14/15] promos...")
    cursor.execute("""
        CREATE TABLE promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT NOT NULL,
            discount_value DECIMAL(10, 2) NOT NULL,
            min_order_amount DECIMAL(10, 2),
            max_uses INTEGER,
            uses_count INTEGER DEFAULT 0,
            valid_from TIMESTAMP,
            valid_until TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        )
    """)
    
    # 15. banners
    print("   [15/15] banners...")
    cursor.execute("""
        CREATE TABLE banners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            image_url TEXT NOT NULL,
            link_type TEXT,
            link_id INTEGER,
            link_url TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    # Проверяем результат
    print("\n" + "=" * 60)
    print("ПРОВЕРКА РЕЗУЛЬТАТА")
    print("=" * 60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n✅ Создано таблиц: {len(tables)}")
    for table in tables:
        if table != 'sqlite_sequence':
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"   • {table} ({len(columns)} колонок)")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ БАЗА ДАННЫХ ПЕРЕСОЗДАНА УСПЕШНО")
    print("=" * 60)
    print("\nВАЖНО: Исправьте права на файл:")
    print("  chown www-data:www-data /var/www/daribri/database/miniapp.db")
    print("\nЗатем перезапустите сервис:")
    print("  systemctl restart daribri")


if __name__ == "__main__":
    confirm = input("\n⚠️  ВНИМАНИЕ: Все данные будут удалены! Продолжить? (yes/no): ")
    if confirm.lower() == 'yes':
        recreate_database()
    else:
        print("Отменено.")



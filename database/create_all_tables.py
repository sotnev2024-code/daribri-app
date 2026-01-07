#!/usr/bin/env python3
"""
Скрипт для создания всех необходимых таблиц в базе данных.
Используется, когда база данных не полностью инициализирована.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def create_all_tables():
    """Создает все необходимые таблицы в базе данных."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("=" * 60)
    print("СОЗДАНИЕ ВСЕХ ТАБЛИЦ В БАЗЕ ДАННЫХ")
    print("=" * 60)
    
    # Таблица users
    print("\n[1/11] Создание таблицы users...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            is_premium INTEGER DEFAULT 0,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Таблица users создана")
    
    # Таблица shops
    print("\n[2/11] Создание таблицы shops...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            address TEXT,
            city TEXT,
            phone TEXT,
            email TEXT,
            photo_url TEXT,
            latitude REAL,
            longitude REAL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ Таблица shops создана")
    
    # Таблица products (уже должна быть создана через миграции, но на всякий случай)
    print("\n[3/11] Создание таблицы products...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10, 2) NOT NULL,
            discount_price DECIMAL(10, 2),
            quantity INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            is_trending INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)
    print("   ✅ Таблица products создана")
    
    # Таблица product_media
    print("\n[4/11] Создание таблицы product_media...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ Таблица product_media создана")
    
    # Таблица cart_items
    print("\n[5/11] Создание таблицы cart_items...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_id, product_id)
        )
    """)
    print("   ✅ Таблица cart_items создана")
    
    # Таблица favorites
    print("\n[6/11] Создание таблицы favorites...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(user_id, product_id)
        )
    """)
    print("   ✅ Таблица favorites создана")
    
    # Таблица orders
    print("\n[7/11] Создание таблицы orders...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            shop_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            total_amount DECIMAL(10, 2) NOT NULL,
            promo_code TEXT,
            promo_discount_amount DECIMAL(10, 2) DEFAULT 0,
            delivery_fee DECIMAL(10, 2) DEFAULT 0,
            delivery_address TEXT,
            delivery_phone TEXT,
            delivery_name TEXT,
            delivery_date TEXT,
            delivery_time TEXT,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ Таблица orders создана")
    
    # Таблица order_items
    print("\n[8/11] Создание таблицы order_items...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    """)
    print("   ✅ Таблица order_items создана")
    
    # Таблица shop_reviews
    print("\n[9/11] Создание таблицы shop_reviews...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            order_id INTEGER,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
            UNIQUE(shop_id, user_id, order_id)
        )
    """)
    print("   ✅ Таблица shop_reviews создана")
    
    # Таблица shop_subscriptions
    print("\n[10/11] Создание таблицы shop_subscriptions...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES subscription_plans(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ Таблица shop_subscriptions создана")
    
    # Таблица shop_requests
    print("\n[11/11] Создание таблицы shop_requests...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            address TEXT,
            city TEXT,
            phone TEXT,
            email TEXT,
            photo_url TEXT,
            status TEXT DEFAULT 'pending',
            group_message_id INTEGER,
            shop_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE SET NULL
        )
    """)
    print("   ✅ Таблица shop_requests создана")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТАБЛИЦЫ УСПЕШНО СОЗДАНЫ")
    print("=" * 60)
    print("\nТеперь запустите: python database/check_data.py")


if __name__ == "__main__":
    create_all_tables()


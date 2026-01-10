#!/usr/bin/env python3
"""
Полный скрипт для исправления базы данных.
Создает все необходимые таблицы с правильной структурой.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def fix_database():
    """Полностью исправляет базу данных."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("=" * 60)
    print("ПОЛНОЕ ИСПРАВЛЕНИЕ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    # Получаем список существующих таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    print(f"\n[INFO] Существующие таблицы: {', '.join(existing_tables) if existing_tables else 'нет'}")
    
    # 1. Таблица users
    print("\n[1/12] Проверка таблицы users...")
    if 'users' not in existing_tables:
        print("   Создаем таблицу users...")
        cursor.execute("""
            CREATE TABLE users (
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
    else:
        print("   ✓ Таблица users существует")
    
    # 2. Таблица subscription_plans
    print("\n[2/12] Проверка таблицы subscription_plans...")
    if 'subscription_plans' not in existing_tables:
        print("   Создаем таблицу subscription_plans...")
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
        print("   ✅ Таблица subscription_plans создана")
    else:
        print("   ✓ Таблица subscription_plans существует")
    
    # 3. Таблица categories
    print("\n[3/12] Проверка таблицы categories...")
    if 'categories' not in existing_tables:
        print("   Создаем таблицу categories...")
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
        print("   ✅ Таблица categories создана")
    else:
        # Проверяем колонку is_active
        cursor.execute("PRAGMA table_info(categories)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1")
            print("   + Добавлена колонка is_active")
        print("   ✓ Таблица categories существует")
    
    # 4. Таблица shops
    print("\n[4/12] Проверка таблицы shops...")
    if 'shops' not in existing_tables:
        print("   Создаем таблицу shops...")
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
                reviews_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        print("   ✅ Таблица shops создана")
    else:
        # Проверяем необходимые колонки
        cursor.execute("PRAGMA table_info(shops)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE shops ADD COLUMN is_active INTEGER DEFAULT 1")
            print("   + Добавлена колонка is_active")
        if 'photo_url' not in columns:
            cursor.execute("ALTER TABLE shops ADD COLUMN photo_url TEXT")
            print("   + Добавлена колонка photo_url")
        print("   ✓ Таблица shops существует")
    
    # 5. Таблица shop_subscriptions
    print("\n[5/12] Проверка таблицы shop_subscriptions...")
    if 'shop_subscriptions' not in existing_tables:
        print("   Создаем таблицу shop_subscriptions...")
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
        print("   ✅ Таблица shop_subscriptions создана")
    else:
        print("   ✓ Таблица shop_subscriptions существует")
    
    # 6. Таблица products
    print("\n[6/12] Проверка таблицы products...")
    if 'products' not in existing_tables:
        print("   Создаем таблицу products...")
        cursor.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                discount_price DECIMAL(10, 2),
                discount_percent INTEGER,
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
        print("   ✅ Таблица products создана")
    else:
        # Проверяем необходимые колонки
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN is_active INTEGER DEFAULT 1")
            print("   + Добавлена колонка is_active")
        if 'is_trending' not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN is_trending INTEGER DEFAULT 0")
            print("   + Добавлена колонка is_trending")
        print("   ✓ Таблица products существует")
    
    # 7. Таблица product_media
    print("\n[7/12] Проверка таблицы product_media...")
    if 'product_media' not in existing_tables:
        print("   Создаем таблицу product_media...")
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
        # Проверяем и исправляем структуру
        cursor.execute("PRAGMA table_info(product_media)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        if 'url' not in columns:
            cursor.execute("ALTER TABLE product_media ADD COLUMN url TEXT")
            if 'file_path' in columns:
                cursor.execute("UPDATE product_media SET url = file_path WHERE url IS NULL")
            print("   + Добавлена колонка url")
        
        if 'media_type' not in columns:
            cursor.execute("ALTER TABLE product_media ADD COLUMN media_type TEXT")
            if 'file_type' in columns:
                cursor.execute("UPDATE product_media SET media_type = file_type WHERE media_type IS NULL")
            else:
                cursor.execute("UPDATE product_media SET media_type = 'photo' WHERE media_type IS NULL")
            print("   + Добавлена колонка media_type")
        
        if 'is_primary' not in columns:
            cursor.execute("ALTER TABLE product_media ADD COLUMN is_primary INTEGER DEFAULT 0")
            cursor.execute("""
                UPDATE product_media SET is_primary = 1
                WHERE id IN (SELECT MIN(id) FROM product_media GROUP BY product_id)
            """)
            print("   + Добавлена колонка is_primary")
        
        if 'thumbnail_url' not in columns:
            cursor.execute("ALTER TABLE product_media ADD COLUMN thumbnail_url TEXT")
            print("   + Добавлена колонка thumbnail_url")
        
        if 'sort_order' not in columns:
            cursor.execute("ALTER TABLE product_media ADD COLUMN sort_order INTEGER DEFAULT 0")
            if 'display_order' in columns:
                cursor.execute("UPDATE product_media SET sort_order = display_order WHERE sort_order IS NULL")
            print("   + Добавлена колонка sort_order")
        
        print("   ✓ Таблица product_media существует")
    
    # 8. Таблица cart_items
    print("\n[8/12] Проверка таблицы cart_items...")
    if 'cart_items' not in existing_tables:
        print("   Создаем таблицу cart_items...")
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
        print("   ✅ Таблица cart_items создана")
    else:
        print("   ✓ Таблица cart_items существует")
    
    # 9. Таблица favorites
    print("\n[9/12] Проверка таблицы favorites...")
    if 'favorites' not in existing_tables:
        print("   Создаем таблицу favorites...")
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
        print("   ✅ Таблица favorites создана")
    else:
        print("   ✓ Таблица favorites существует")
    
    # 10. Таблица orders
    print("\n[10/12] Проверка таблицы orders...")
    if 'orders' not in existing_tables:
        print("   Создаем таблицу orders...")
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
            )
        """)
        print("   ✅ Таблица orders создана")
    else:
        print("   ✓ Таблица orders существует")
    
    # 11. Таблица order_items
    print("\n[11/12] Проверка таблицы order_items...")
    if 'order_items' not in existing_tables:
        print("   Создаем таблицу order_items...")
        cursor.execute("""
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                product_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            )
        """)
        print("   ✅ Таблица order_items создана")
    else:
        print("   ✓ Таблица order_items существует")
    
    # 12. Таблица shop_reviews
    print("\n[12/12] Проверка таблицы shop_reviews...")
    if 'shop_reviews' not in existing_tables:
        print("   Создаем таблицу shop_reviews...")
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
        print("   ✅ Таблица shop_reviews создана")
    else:
        print("   ✓ Таблица shop_reviews существует")
    
    # Дополнительные таблицы
    print("\n[+] Проверка дополнительных таблиц...")
    
    # shop_requests
    if 'shop_requests' not in existing_tables:
        print("   Создаем таблицу shop_requests...")
        cursor.execute("""
            CREATE TABLE shop_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                shop_name TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT,
                city TEXT,
                category TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                admin_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ Таблица shop_requests создана")
    
    # promos
    if 'promos' not in existing_tables:
        print("   Создаем таблицу promos...")
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
        print("   ✅ Таблица promos создана")
    
    # banners
    if 'banners' not in existing_tables:
        print("   Создаем таблицу banners...")
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
        print("   ✅ Таблица banners создана")
    
    conn.commit()
    
    # Проверяем финальный результат
    print("\n" + "=" * 60)
    print("ПРОВЕРКА РЕЗУЛЬТАТА")
    print("=" * 60)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    final_tables = [row[0] for row in cursor.fetchall()]
    print(f"\n✅ Таблицы в базе данных ({len(final_tables)}):")
    for table in final_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   • {table}: {count} записей")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ ИСПРАВЛЕНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print("\nПерезапустите приложение: systemctl restart daribri")


if __name__ == "__main__":
    fix_database()



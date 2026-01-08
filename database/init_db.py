"""
Скрипт инициализации базы данных SQLite для Telegram Mini App.
Создаёт схему и наполняет начальными данными.
"""

import sqlite3
import os
from pathlib import Path


# Путь к базе данных
DATABASE_DIR = Path(__file__).parent
DATABASE_PATH = DATABASE_DIR / "miniapp.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
# SEED_DATA_PATH больше не используется - тестовые данные не загружаются автоматически


def execute_sql_file(cursor: sqlite3.Cursor, file_path: Path) -> None:
    """Выполняет SQL файл."""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)


def create_basic_schema(cursor: sqlite3.Cursor) -> None:
    """Создаёт базовую схему базы данных (минимальный набор таблиц для seed_data)."""
    # Таблица subscription_plans
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscription_plans (
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
    
    # Таблица categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            name TEXT NOT NULL,
            slug TEXT UNIQUE,
            icon TEXT,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)


def init_database(reset: bool = False) -> None:
    """
    Инициализирует базу данных.
    
    Args:
        reset: Если True, удаляет существующую базу и создаёт новую.
    """
    if reset and DATABASE_PATH.exists():
        os.remove(DATABASE_PATH)
        print(f"[OK] Удалена существующая база данных: {DATABASE_PATH}")
    
    # Создаём подключение (автоматически создаёт файл)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Проверяем, существует ли схема
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='categories'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Применяем схему, если файл существует и не пустой
            schema_applied = False
            if SCHEMA_PATH.exists() and SCHEMA_PATH.stat().st_size > 0:
                print("[...] Создание схемы базы данных...")
                try:
                    execute_sql_file(cursor, SCHEMA_PATH)
                    print("[OK] Схема создана успешно")
                    schema_applied = True
                except Exception as e:
                    print(f"[WARNING] Ошибка при выполнении schema.sql: {e}")
            
            # Проверяем, что таблица categories действительно создана
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='categories'
            """)
            table_exists_after = cursor.fetchone() is not None
            
            if not table_exists_after:
                if not schema_applied:
                    print("[WARNING] Файл schema.sql не найден или пуст")
                else:
                    print("[WARNING] Таблица categories не найдена после создания схемы")
                print("[INFO] Создание базовой схемы...")
                create_basic_schema(cursor)
                print("[OK] Базовая схема создана")
        
        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        
        # Не загружаем тестовые данные автоматически
        # Пользователь должен добавить данные вручную через API или бота
        if count == 0:
            print("[INFO] База данных пуста. Данные нужно добавить вручную через API или бота.")
        else:
            print(f"[INFO] Данные уже существуют ({count} категорий)")
        
        conn.commit()
        print(f"\n[OK] База данных готова: {DATABASE_PATH}")
        
        # Выводим статистику
        print_statistics(cursor)
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Ошибка: {e}")
        raise
    finally:
        conn.close()


def print_statistics(cursor: sqlite3.Cursor) -> None:
    """Выводит статистику базы данных."""
    print("\n=== Статистика базы данных ===")
    print("-" * 40)
    
    tables = [
        ("subscription_plans", "Планов подписки"),
        ("categories", "Категорий"),
    ]
    
    for table, label in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {label}: {count}")
    
    # Категории с подкатегориями
    cursor.execute("""
        SELECT c.name, COUNT(sub.id) as subcategories
        FROM categories c
        LEFT JOIN categories sub ON sub.parent_id = c.id
        WHERE c.parent_id IS NULL
        GROUP BY c.id
        ORDER BY c.sort_order
    """)
    
    print("\n=== Структура категорий ===")
    print("-" * 40)
    for row in cursor.fetchall():
        name, sub_count = row
        if sub_count > 0:
            print(f"  * {name} ({sub_count} подкатегорий)")
        else:
            print(f"  * {name}")


def get_connection() -> sqlite3.Connection:
    """Возвращает подключение к базе данных."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Инициализация базы данных")
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Удалить существующую базу и создать новую"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("  Telegram Mini App - Инициализация БД")
    print("=" * 50)
    print()
    
    init_database(reset=args.reset)


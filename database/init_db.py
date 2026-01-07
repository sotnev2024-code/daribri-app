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
SEED_DATA_PATH = DATABASE_DIR / "seed_data.sql"


def execute_sql_file(cursor: sqlite3.Cursor, file_path: Path) -> None:
    """Выполняет SQL файл."""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    cursor.executescript(sql_script)


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
        # Применяем схему
        print("[...] Создание схемы базы данных...")
        execute_sql_file(cursor, SCHEMA_PATH)
        print("[OK] Схема создана успешно")
        
        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Наполняем начальными данными
            print("[...] Наполнение начальными данными...")
            execute_sql_file(cursor, SEED_DATA_PATH)
            print("[OK] Начальные данные добавлены")
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


"""
Скрипт для очистки всех данных из базы данных.
Удаляет все данные из таблиц, но сохраняет структуру базы.
"""

import sqlite3
from pathlib import Path


# Путь к базе данных
DATABASE_DIR = Path(__file__).parent
DATABASE_PATH = DATABASE_DIR / "miniapp.db"


def clear_database() -> None:
    """
    Очищает все данные из базы данных, сохраняя структуру.
    """
    if not DATABASE_PATH.exists():
        print(f"[ERROR] База данных не найдена: {DATABASE_PATH}")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Получаем список всех таблиц
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("[INFO] В базе данных нет таблиц для очистки")
            return
        
        print(f"[...] Найдено таблиц: {len(tables)}")
        print(f"[...] Начинаю очистку данных...")
        
        # Отключаем внешние ключи временно для более быстрой очистки
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        # Очищаем каждую таблицу
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table}")
                count = cursor.rowcount
                print(f"  [OK] {table}: удалено {count} записей")
            except Exception as e:
                print(f"  [ERROR] {table}: {e}")
        
        # Сбрасываем автоинкременты (обнуляем счетчики)
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
            except:
                pass  # Если таблица не использует автоинкремент, это нормально
        
        # Включаем обратно внешние ключи
        cursor.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        print(f"\n[OK] База данных очищена: {DATABASE_PATH}")
        
        # Выводим статистику после очистки
        print("\n=== Статистика после очистки ===")
        print("-" * 40)
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} записей")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Ошибка при очистке: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("  Telegram Mini App - Очистка базы данных")
    print("=" * 50)
    print()
    print("⚠️  ВНИМАНИЕ: Все данные будут удалены!")
    print()
    
    # Запрашиваем подтверждение
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        confirm = "yes"
    else:
        confirm = input("Продолжить? (yes/no): ").strip().lower()
    
    if confirm in ["yes", "y", "да", "д"]:
        print()
        clear_database()
    else:
        print("\n[INFO] Очистка отменена")



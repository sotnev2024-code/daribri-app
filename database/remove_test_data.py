#!/usr/bin/env python3
"""
Скрипт для удаления тестовых данных из базы данных.
Удаляет категории и планы подписок, созданные из seed_data.sql.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def remove_test_data():
    """Удаляет тестовые данные из базы данных."""
    if not DATABASE_PATH.exists():
        print(f"❌ База данных не найдена: {DATABASE_PATH}")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("УДАЛЕНИЕ ТЕСТОВЫХ ДАННЫХ")
    print("=" * 60)
    
    # Проверяем наличие таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    if 'categories' not in tables:
        print("\n[INFO] Таблица categories не найдена")
    else:
        # Удаляем все категории
        cursor.execute("SELECT COUNT(*) FROM categories")
        count_before = cursor.fetchone()[0]
        
        if count_before > 0:
            print(f"\n[1] Удаление категорий ({count_before} записей)...")
            # Сначала удаляем подкатегории (с parent_id)
            cursor.execute("DELETE FROM categories WHERE parent_id IS NOT NULL")
            # Затем удаляем основные категории
            cursor.execute("DELETE FROM categories WHERE parent_id IS NULL")
            print("   ✅ Категории удалены")
        else:
            print("\n[1] Категории уже пусты")
    
    if 'subscription_plans' not in tables:
        print("\n[INFO] Таблица subscription_plans не найдена")
    else:
        # Удаляем все планы подписок
        cursor.execute("SELECT COUNT(*) FROM subscription_plans")
        count_before = cursor.fetchone()[0]
        
        if count_before > 0:
            print(f"\n[2] Удаление планов подписок ({count_before} записей)...")
            # Проверяем, есть ли активные подписки
            if 'shop_subscriptions' in tables:
                cursor.execute("SELECT COUNT(*) FROM shop_subscriptions")
                active_subs = cursor.fetchone()[0]
                if active_subs > 0:
                    print(f"   ⚠️  ВНИМАНИЕ: Есть {active_subs} активных подписок!")
                    print("   Планы подписок не будут удалены, чтобы не нарушить работу системы.")
                else:
                    cursor.execute("DELETE FROM subscription_plans")
                    print("   ✅ Планы подписок удалены")
            else:
                cursor.execute("DELETE FROM subscription_plans")
                print("   ✅ Планы подписок удалены")
        else:
            print("\n[2] Планы подписок уже пусты")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ УДАЛЕНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print("\nПримечание: Планы подписок могут быть не удалены, если есть активные подписки.")
    print("Это сделано для защиты данных.")


if __name__ == "__main__":
    remove_test_data()



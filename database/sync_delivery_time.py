#!/usr/bin/env python3
"""
Скрипт для синхронизации колонки delivery_time/delivery_time_slot.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'miniapp.db')

def sync_delivery_time():
    """Синхронизирует колонки времени доставки."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 50)
    print("СИНХРОНИЗАЦИЯ КОЛОНКИ ВРЕМЕНИ ДОСТАВКИ")
    print("=" * 50)
    
    # Получаем текущие колонки
    cursor.execute("PRAGMA table_info(orders)")
    columns = {row[1] for row in cursor.fetchall()}
    
    print(f"\nСуществующие колонки в orders: {columns}")
    
    has_delivery_time = 'delivery_time' in columns
    has_delivery_time_slot = 'delivery_time_slot' in columns
    
    print(f"delivery_time: {'✅ есть' if has_delivery_time else '❌ нет'}")
    print(f"delivery_time_slot: {'✅ есть' if has_delivery_time_slot else '❌ нет'}")
    
    # Добавляем обе колонки если их нет
    if not has_delivery_time:
        print("\n[1] Добавление колонки delivery_time...")
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_time TEXT")
        print("   ✅ Колонка delivery_time добавлена")
    
    if not has_delivery_time_slot:
        print("\n[2] Добавление колонки delivery_time_slot...")
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_time_slot TEXT")
        print("   ✅ Колонка delivery_time_slot добавлена")
    
    # Синхронизируем данные между колонками
    print("\n[3] Синхронизация данных...")
    
    # Копируем из delivery_time в delivery_time_slot
    cursor.execute("""
        UPDATE orders 
        SET delivery_time_slot = delivery_time 
        WHERE delivery_time_slot IS NULL AND delivery_time IS NOT NULL
    """)
    rows1 = cursor.rowcount
    
    # Копируем из delivery_time_slot в delivery_time
    cursor.execute("""
        UPDATE orders 
        SET delivery_time = delivery_time_slot 
        WHERE delivery_time IS NULL AND delivery_time_slot IS NOT NULL
    """)
    rows2 = cursor.rowcount
    
    if rows1 > 0 or rows2 > 0:
        print(f"   ✅ Синхронизировано записей: {rows1 + rows2}")
    else:
        print("   ✅ Данные уже синхронизированы")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
    print("=" * 50)

if __name__ == "__main__":
    sync_delivery_time()



"""
Скрипт для установки бесконечной подписки пользователю.
Устанавливает end_date на дату далеко в будущем (2099-12-31).
"""

import sqlite3
from pathlib import Path
from datetime import datetime


# Путь к базе данных
DATABASE_DIR = Path(__file__).parent
DATABASE_PATH = DATABASE_DIR / "miniapp.db"

# Дата для бесконечной подписки (31 декабря 2099 года)
INFINITE_DATE = "2099-12-31 23:59:59"


def set_infinite_subscription(telegram_id: int = None, shop_id: int = None) -> None:
    """
    Устанавливает бесконечную подписку для пользователя или магазина.
    
    Args:
        telegram_id: Telegram ID пользователя (если указан, будет найден его магазин)
        shop_id: ID магазина напрямую
    """
    if not DATABASE_PATH.exists():
        print(f"[ERROR] База данных не найдена: {DATABASE_PATH}")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Включаем поддержку внешних ключей
    cursor.execute("PRAGMA foreign_keys = ON")
    
    try:
        # Определяем shop_id
        if telegram_id:
            # Находим магазин по telegram_id пользователя
            cursor.execute("""
                SELECT s.id 
                FROM shops s
                JOIN users u ON s.owner_id = u.id
                WHERE u.telegram_id = ?
                LIMIT 1
            """, (telegram_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"[ERROR] Магазин не найден для пользователя с telegram_id={telegram_id}")
                return
            
            shop_id = result[0]
            print(f"[INFO] Найден магазин ID={shop_id} для пользователя telegram_id={telegram_id}")
        
        if not shop_id:
            print("[ERROR] Необходимо указать либо telegram_id, либо shop_id")
            return
        
        # Проверяем, существует ли магазин
        cursor.execute("SELECT id, name FROM shops WHERE id = ?", (shop_id,))
        shop = cursor.fetchone()
        
        if not shop:
            print(f"[ERROR] Магазин с ID={shop_id} не найден")
            return
        
        shop_name = shop[1]
        print(f"[INFO] Магазин: {shop_name} (ID: {shop_id})")
        
        # Деактивируем все старые подписки
        cursor.execute("""
            UPDATE shop_subscriptions 
            SET is_active = 0 
            WHERE shop_id = ?
        """, (shop_id,))
        deactivated_count = cursor.rowcount
        print(f"[INFO] Деактивировано старых подписок: {deactivated_count}")
        
        # Проверяем, есть ли активный план подписки
        cursor.execute("""
            SELECT id FROM subscription_plans 
            WHERE is_active = 1 
            ORDER BY price ASC 
            LIMIT 1
        """)
        plan = cursor.fetchone()
        
        if not plan:
            print("[ERROR] Нет активных планов подписки в базе")
            return
        
        plan_id = plan[0]
        print(f"[INFO] Используется план подписки ID={plan_id}")
        
        # Создаём или обновляем подписку с бесконечной датой
        # Сначала проверяем, есть ли уже подписка для этого магазина
        cursor.execute("""
            SELECT id FROM shop_subscriptions 
            WHERE shop_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (shop_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Обновляем существующую подписку
            subscription_id = existing[0]
            cursor.execute("""
                UPDATE shop_subscriptions 
                SET end_date = ?,
                    is_active = 1,
                    start_date = datetime('now')
                WHERE id = ?
            """, (INFINITE_DATE, subscription_id))
            print(f"[INFO] Обновлена подписка ID={subscription_id}")
        else:
            # Создаём новую подписку
            cursor.execute("""
                INSERT INTO shop_subscriptions 
                (shop_id, plan_id, start_date, end_date, is_active, payment_id)
                VALUES (?, ?, datetime('now'), ?, 1, 'infinite_admin')
            """, (shop_id, plan_id, INFINITE_DATE))
            subscription_id = cursor.lastrowid
            print(f"[INFO] Создана новая подписка ID={subscription_id}")
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute("""
            SELECT ss.*, sp.name as plan_name
            FROM shop_subscriptions ss
            JOIN subscription_plans sp ON ss.plan_id = sp.id
            WHERE ss.id = ?
        """, (subscription_id,))
        
        subscription = cursor.fetchone()
        if subscription:
            print(f"\n[OK] Подписка установлена успешно!")
            print(f"  ID подписки: {subscription[0]}")
            print(f"  План: {subscription[8]}")  # plan_name
            print(f"  Дата начала: {subscription[3]}")
            print(f"  Дата окончания: {subscription[4]} (бесконечная)")
            print(f"  Активна: {'Да' if subscription[5] else 'Нет'}")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


def list_shops() -> None:
    """Выводит список всех магазинов с их владельцами."""
    if not DATABASE_PATH.exists():
        print(f"[ERROR] База данных не найдена: {DATABASE_PATH}")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT s.id, s.name, u.telegram_id, u.username, u.first_name
            FROM shops s
            JOIN users u ON s.owner_id = u.id
            ORDER BY s.id
        """)
        
        shops = cursor.fetchall()
        
        if not shops:
            print("[INFO] Магазинов не найдено")
            return
        
        print("\n=== Список магазинов ===")
        print("-" * 60)
        print(f"{'ID':<5} {'Название':<25} {'Telegram ID':<15} {'Владелец':<20}")
        print("-" * 60)
        
        for shop in shops:
            shop_id, name, tg_id, username, first_name = shop
            owner = username or first_name or f"ID:{tg_id}"
            print(f"{shop_id:<5} {name[:24]:<25} {tg_id:<15} {owner[:19]:<20}")
        
        print("-" * 60)
        print(f"Всего: {len(shops)} магазинов")
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("  Установка бесконечной подписки")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_shops()
    elif len(sys.argv) > 1:
        # Парсим аргументы
        if sys.argv[1].startswith("--telegram-id="):
            telegram_id = int(sys.argv[1].split("=")[1])
            set_infinite_subscription(telegram_id=telegram_id)
        elif sys.argv[1].startswith("--shop-id="):
            shop_id = int(sys.argv[1].split("=")[1])
            set_infinite_subscription(shop_id=shop_id)
        else:
            print("Использование:")
            print("  python database/set_infinite_subscription.py --telegram-id=123456789")
            print("  python database/set_infinite_subscription.py --shop-id=1")
            print("  python database/set_infinite_subscription.py --list")
    else:
        print("Использование:")
        print("  python database/set_infinite_subscription.py --telegram-id=123456789")
        print("  python database/set_infinite_subscription.py --shop-id=1")
        print("  python database/set_infinite_subscription.py --list")
        print()
        print("Примеры:")
        print("  # Установить бесконечную подписку по Telegram ID")
        print("  python database/set_infinite_subscription.py --telegram-id=123456789")
        print()
        print("  # Установить бесконечную подписку по ID магазина")
        print("  python database/set_infinite_subscription.py --shop-id=1")
        print()
        print("  # Показать список всех магазинов")
        print("  python database/set_infinite_subscription.py --list")



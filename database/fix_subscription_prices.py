#!/usr/bin/env python3
"""
Скрипт для проверки и исправления цен планов подписок.
Telegram требует минимум 60 RUB для платежей.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "miniapp.db"


def fix_subscription_prices():
    """Проверяет и исправляет цены планов подписок."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 60)
    print("ПРОВЕРКА ЦЕН ПЛАНОВ ПОДПИСОК")
    print("=" * 60)

    # Получаем текущие планы
    cursor.execute("SELECT * FROM subscription_plans ORDER BY id")
    plans = cursor.fetchall()

    if not plans:
        print("\n❌ Планы подписок не найдены!")
        print("\nСоздаём планы подписок...")
        
        # Создаём планы подписок с корректными ценами (минимум 60 RUB)
        plans_data = [
            ("Пробный", "Бесплатный пробный период на 7 дней", 0, 7, 10, 1),
            ("Базовый", "Базовый план на 1 месяц", 299, 30, 30, 1),
            ("Стандарт", "Стандартный план на 1 месяц", 599, 30, 100, 1),
            ("Премиум", "Премиум план на 1 месяц", 999, 30, 500, 1),
            ("Бизнес", "Бизнес план на 1 год", 4999, 365, 9999, 1),
        ]
        
        cursor.executemany("""
            INSERT INTO subscription_plans (name, description, price, duration_days, max_products, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, plans_data)
        
        conn.commit()
        print("✅ Планы подписок созданы!")
        
        # Повторно получаем планы
        cursor.execute("SELECT * FROM subscription_plans ORDER BY id")
        plans = cursor.fetchall()

    print("\n📋 Текущие планы подписок:")
    print("-" * 60)
    
    min_telegram_price = 60  # Минимальная цена для Telegram в RUB
    plans_to_fix = []
    
    for plan in plans:
        price = float(plan["price"])
        status = "✅" if price == 0 or price >= min_telegram_price else "⚠️"
        
        print(f"{status} ID={plan['id']}: {plan['name']}")
        print(f"   Цена: {price} RUB")
        print(f"   Длительность: {plan['duration_days']} дней")
        print(f"   Макс. товаров: {plan['max_products']}")
        print()
        
        if 0 < price < min_telegram_price:
            plans_to_fix.append(plan)
    
    if plans_to_fix:
        print("\n⚠️ Найдены планы с ценой меньше минимальной (60 RUB):")
        for plan in plans_to_fix:
            print(f"   - {plan['name']}: {plan['price']} RUB")
        
        print("\nИсправляем цены...")
        for plan in plans_to_fix:
            new_price = max(float(plan["price"]), min_telegram_price)
            cursor.execute(
                "UPDATE subscription_plans SET price = ? WHERE id = ?",
                (new_price, plan["id"])
            )
            print(f"   ✅ {plan['name']}: {plan['price']} → {new_price} RUB")
        
        conn.commit()
        print("\n✅ Цены исправлены!")
    else:
        print("\n✅ Все цены корректны!")

    conn.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    fix_subscription_prices()


"""
Скрипт для добавления тестовых промокодов в базу данных.
Использование: python database/add_test_promos.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

# Добавляем корень проекта в путь для импорта
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.database import DatabaseService
from backend.app.config import settings


async def add_test_promos():
    """Добавляет тестовые промокоды в базу данных."""
    db = DatabaseService(db_path=settings.DATABASE_PATH)
    
    try:
        await db.connect()
        print(f"[INFO] Подключение к базе данных: {settings.DATABASE_PATH}")
        
        # Проверяем, существует ли таблица promos
        promos_table = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='promos'")
        if not promos_table:
            print("[ERROR] Таблица promos не существует. Запустите приложение для создания таблицы.")
            return
        
        # Проверяем, есть ли уже промокоды
        existing = await db.fetch_all("SELECT code FROM promos")
        if existing:
            print(f"[INFO] В базе уже есть {len(existing)} промокодов")
            response = input("Удалить существующие промокоды? (y/N): ")
            if response.lower() == 'y':
                await db.execute("DELETE FROM promos")
                await db.commit()
                print("[INFO] Существующие промокоды удалены")
            else:
                print("[INFO] Пропускаем существующие промокоды")
        
        # Сегодняшняя дата
        today = date.today()
        
        # Список тестовых промокодов
        test_promos = [
            # ========== Процентные скидки ==========
            {
                "code": "SALE10",
                "promo_type": "percent",
                "value": "10.00",
                "description": "Скидка 10% на весь заказ",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            {
                "code": "DISCOUNT15",
                "promo_type": "percent",
                "value": "15.00",
                "description": "Скидка 15% на заказ от 2000₽",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": "2000.00",
                "valid_from": None,
                "valid_until": (today + timedelta(days=30)).isoformat(),
                "usage_count": 0
            },
            {
                "code": "MEGA20",
                "promo_type": "percent",
                "value": "20.00",
                "description": "Мегаскидка 20% только для первого заказа",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 1,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            {
                "code": "ONETIME25",
                "promo_type": "percent",
                "value": "25.00",
                "description": "Одноразовая скидка 25%",
                "is_active": 1,
                "use_once": 1,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            
            # ========== Фиксированные суммы ==========
            {
                "code": "BONUS100",
                "promo_type": "fixed",
                "value": "100.00",
                "description": "Скидка 100₽ на заказ",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            {
                "code": "SAVE500",
                "promo_type": "fixed",
                "value": "500.00",
                "description": "Экономия 500₽ на заказ от 3000₽",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": "3000.00",
                "valid_from": None,
                "valid_until": (today + timedelta(days=60)).isoformat(),
                "usage_count": 0
            },
            {
                "code": "FIRST1000",
                "promo_type": "fixed",
                "value": "1000.00",
                "description": "Подарок 1000₽ для новых клиентов",
                "is_active": 1,
                "use_once": 1,
                "first_order_only": 1,
                "shop_id": None,
                "min_order_amount": "5000.00",
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            {
                "code": "BIG2000",
                "promo_type": "fixed",
                "value": "2000.00",
                "description": "Большая скидка 2000₽",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": "10000.00",
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            
            # ========== Бесплатная доставка ==========
            {
                "code": "FREEDEL",
                "promo_type": "free_delivery",
                "value": "0.00",
                "description": "Бесплатная доставка",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            {
                "code": "DELIVERY500",
                "promo_type": "free_delivery",
                "value": "0.00",
                "description": "Бесплатная доставка при заказе от 500₽",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": "500.00",
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            {
                "code": "FIRSTDEL",
                "promo_type": "free_delivery",
                "value": "0.00",
                "description": "Бесплатная доставка для первого заказа",
                "is_active": 1,
                "use_once": 1,
                "first_order_only": 1,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
            
            # ========== Промокоды с датами действия ==========
            {
                "code": "NEWYEAR30",
                "promo_type": "percent",
                "value": "30.00",
                "description": "Новогодняя скидка 30% (действует до конца месяца)",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": today.isoformat(),
                "valid_until": (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1) if today.month < 12 else date(today.year + 1, 1, 31).isoformat(),
                "usage_count": 0
            },
            {
                "code": "FUTURE50",
                "promo_type": "percent",
                "value": "50.00",
                "description": "Скидка 50% (начнет действовать через неделю)",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": (today + timedelta(days=7)).isoformat(),
                "valid_until": (today + timedelta(days=37)).isoformat(),
                "usage_count": 0
            },
            {
                "code": "EXPIRED5",
                "promo_type": "percent",
                "value": "5.00",
                "description": "Истекший промокод (для тестирования)",
                "is_active": 1,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": (today - timedelta(days=30)).isoformat(),
                "valid_until": (today - timedelta(days=1)).isoformat(),
                "usage_count": 0
            },
            
            # ========== Неактивные промокоды ==========
            {
                "code": "INACTIVE10",
                "promo_type": "percent",
                "value": "10.00",
                "description": "Неактивный промокод (для тестирования)",
                "is_active": 0,
                "use_once": 0,
                "first_order_only": 0,
                "shop_id": None,
                "min_order_amount": None,
                "valid_from": None,
                "valid_until": None,
                "usage_count": 0
            },
        ]
        
        # Получаем список магазинов для промокодов с shop_id
        shops = await db.fetch_all("SELECT id FROM shops WHERE is_active = 1 LIMIT 3")
        shop_ids = [shop["id"] for shop in shops] if shops else []
        
        # Добавляем промокоды для конкретных магазинов, если есть магазины
        if shop_ids:
            test_promos.extend([
                {
                    "code": "SHOP1_10",
                    "promo_type": "percent",
                    "value": "10.00",
                    "description": f"Скидка 10% для магазина #{shop_ids[0]}",
                    "is_active": 1,
                    "use_once": 0,
                    "first_order_only": 0,
                    "shop_id": shop_ids[0],
                    "min_order_amount": None,
                    "valid_from": None,
                    "valid_until": None,
                    "usage_count": 0
                },
                {
                    "code": "SHOP_FIXED",
                    "promo_type": "fixed",
                    "value": "300.00",
                    "description": f"Скидка 300₽ для магазина #{shop_ids[0] if shop_ids else None}",
                    "is_active": 1,
                    "use_once": 0,
                    "first_order_only": 0,
                    "shop_id": shop_ids[0] if shop_ids else None,
                    "min_order_amount": "1000.00",
                    "valid_from": None,
                    "valid_until": None,
                    "usage_count": 0
                },
            ])
        
        # Добавляем промокоды в базу данных
        added_count = 0
        skipped_count = 0
        
        for promo_data in test_promos:
            try:
                # Проверяем, не существует ли уже такой промокод
                existing = await db.fetch_one(
                    "SELECT id FROM promos WHERE code = ?",
                    (promo_data["code"],)
                )
                
                if existing:
                    print(f"[SKIP] Промокод {promo_data['code']} уже существует")
                    skipped_count += 1
                    continue
                
                # Формируем список колонок и значений для INSERT
                # Проверяем структуру таблицы
                promos_columns_info = await db.fetch_all("PRAGMA table_info(promos)")
                promos_column_names = [col["name"] for col in promos_columns_info]
                
                # Формируем данные для INSERT, исключая None значения (если колонка может быть NULL)
                insert_data = {}
                for key, value in promo_data.items():
                    if value is not None or key in ["description", "shop_id", "valid_from", "valid_until", "min_order_amount"]:
                        insert_data[key] = value
                
                # Если есть старые колонки discount_type и discount_value, добавляем их
                if "discount_type" in promos_column_names:
                    insert_data["discount_type"] = promo_data["promo_type"]
                if "discount_value" in promos_column_names:
                    insert_data["discount_value"] = promo_data["value"]
                
                # Вставляем промокод
                promo_id = await db.insert("promos", insert_data)
                print(f"[OK] Добавлен промокод: {promo_data['code']} (ID: {promo_id}) - {promo_data['description']}")
                added_count += 1
                
            except Exception as e:
                print(f"[ERROR] Ошибка при добавлении промокода {promo_data['code']}: {e}")
                continue
        
        print(f"\n[SUCCESS] Добавлено промокодов: {added_count}, пропущено: {skipped_count}")
        print(f"\n[INFO] Список добавленных промокодов:")
        
        # Выводим список всех активных промокодов
        all_promos = await db.fetch_all(
            "SELECT code, promo_type, value, description, is_active, valid_until FROM promos ORDER BY code"
        )
        
        print("\n" + "="*80)
        print(f"{'Код':<15} {'Тип':<15} {'Значение':<12} {'Описание':<30} {'Статус':<10} {'Действует до':<15}")
        print("="*80)
        
        for promo in all_promos:
            promo_type_text = {
                "percent": "Процент",
                "fixed": "Фикс. сумма",
                "free_delivery": "Беспл. доставка"
            }.get(promo["promo_type"], promo["promo_type"])
            
            value_text = f"{promo['value']}%" if promo["promo_type"] == "percent" else f"{promo['value']}₽" if promo["promo_type"] == "fixed" else "-"
            status_text = "✅ Активен" if promo["is_active"] else "❌ Неактивен"
            valid_until_text = promo["valid_until"] if promo["valid_until"] else "Без срока"
            
            description = (promo["description"] or "")[:28] + ".." if promo["description"] and len(promo["description"]) > 30 else (promo["description"] or "")
            
            print(f"{promo['code']:<15} {promo_type_text:<15} {value_text:<12} {description:<30} {status_text:<10} {valid_until_text:<15}")
        
        print("="*80)
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()
        print("\n[INFO] Соединение с базой данных закрыто")


if __name__ == "__main__":
    print("="*80)
    print("Добавление тестовых промокодов в базу данных")
    print("="*80)
    asyncio.run(add_test_promos())


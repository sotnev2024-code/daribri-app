"""
API Routes для заказов.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
import uuid
from datetime import datetime

from ..models.order import Order, OrderCreate, OrderItem, OrderWithItems
from ..models.user import User
from ..services.database import DatabaseService, get_db
from ..services.telegram_notifier import telegram_notifier
from .users import get_current_user

router = APIRouter()


def generate_order_number() -> str:
    """Генерирует номер заказа."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique = uuid.uuid4().hex[:6].upper()
    return f"ORD-{timestamp}-{unique}"


@router.get("/shop/{shop_id}", response_model=List[OrderWithItems])
async def get_shop_orders(
    shop_id: int,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает заказы магазина (только для владельца магазина)."""
    # Проверяем, что пользователь является владельцем магазина
    shop = await db.fetch_one(
        "SELECT id FROM shops WHERE id = ? AND owner_id = ?",
        (shop_id, current_user.id)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found or access denied")
    
    if status:
        orders = await db.fetch_all(
            """SELECT o.*, s.name as shop_name
               FROM orders o
               JOIN shops s ON o.shop_id = s.id
               WHERE o.shop_id = ? AND o.status = ?
               ORDER BY o.created_at DESC
               LIMIT ? OFFSET ?""",
            (shop_id, status, limit, skip)
        )
    else:
        orders = await db.fetch_all(
            """SELECT o.*, s.name as shop_name
               FROM orders o
               JOIN shops s ON o.shop_id = s.id
               WHERE o.shop_id = ?
               ORDER BY o.created_at DESC
               LIMIT ? OFFSET ?""",
            (shop_id, limit, skip)
        )
    
    result = []
    for order in orders:
        items = await db.fetch_all(
            """SELECT oi.*, 
                      COALESCE(oi.product_name, p.name) as product_name,
                      (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as product_image_url
               FROM order_items oi
               LEFT JOIN products p ON oi.product_id = p.id
               WHERE oi.order_id = ?""",
            (order["id"],)
        )
        result.append(OrderWithItems(
            **order,
            items=[OrderItem(**item) for item in items]
        ))
    
    return result


@router.get("/", response_model=List[OrderWithItems])
async def get_orders(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает заказы пользователя."""
    if status:
        orders = await db.fetch_all(
            """SELECT o.*, s.name as shop_name
               FROM orders o
               JOIN shops s ON o.shop_id = s.id
               WHERE o.user_id = ? AND o.status = ?
               ORDER BY o.created_at DESC
               LIMIT ? OFFSET ?""",
            (current_user.id, status, limit, skip)
        )
    else:
        orders = await db.fetch_all(
            """SELECT o.*, s.name as shop_name
               FROM orders o
               JOIN shops s ON o.shop_id = s.id
               WHERE o.user_id = ?
               ORDER BY o.created_at DESC
               LIMIT ? OFFSET ?""",
            (current_user.id, limit, skip)
        )
    
    result = []
    for order in orders:
        items = await db.fetch_all(
            """SELECT oi.*, 
                      p.name as product_name,
                      (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as product_image_url
               FROM order_items oi
               JOIN products p ON oi.product_id = p.id
               WHERE oi.order_id = ?""",
            (order["id"],)
        )
        result.append(OrderWithItems(
            **order,
            items=[OrderItem(**item) for item in items]
        ))
    
    return result


@router.get("/{order_id}", response_model=OrderWithItems)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает заказ по ID."""
    order = await db.fetch_one(
        """SELECT o.*, s.name as shop_name
           FROM orders o
           JOIN shops s ON o.shop_id = s.id
           WHERE o.id = ? AND o.user_id = ?""",
        (order_id, current_user.id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    items = await db.fetch_all(
        """SELECT oi.*, 
                  COALESCE(oi.product_name, p.name) as product_name,
                  (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as product_image_url
           FROM order_items oi
           LEFT JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = ?""",
        (order_id,)
    )
    
    return OrderWithItems(
        **order,
        items=[OrderItem(**item) for item in items]
    )


@router.post("/", response_model=Order)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Создаёт новый заказ."""
    # Проверяем магазин и получаем информацию о владельце
    shop = await db.fetch_one(
        """SELECT s.id, s.name, s.owner_id, u.telegram_id 
           FROM shops s
           JOIN users u ON s.owner_id = u.id
           WHERE s.id = ? AND s.is_active = 1""",
        (order_data.shop_id,)
    )
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    
    # Проверяем товары и считаем сумму
    subtotal_amount = Decimal("0")
    discount_amount = Decimal("0")
    order_items_info = []  # Для уведомления
    
    for item in order_data.items:
        product = await db.fetch_one(
            "SELECT * FROM products WHERE id = ? AND shop_id = ? AND is_active = 1",
            (item.product_id, order_data.shop_id)
        )
        if not product:
            raise HTTPException(
                status_code=400, 
                detail=f"Товар {item.product_id} не найден в магазине"
            )
        if not product["is_active"]:
            raise HTTPException(
                status_code=400,
                detail=f"Товар '{product['name']}' недоступен для заказа"
            )
        if product["quantity"] < item.quantity:
            available = product["quantity"] or 0
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно товара '{product['name']}' на складе. Доступно: {available}, требуется: {item.quantity}"
            )
        
        price = Decimal(str(product["price"]))
        discount_price = Decimal(str(product["discount_price"])) if product["discount_price"] else None
        
        if discount_price:
            item_total = float(discount_price * item.quantity)
            subtotal_amount += discount_price * item.quantity
            discount_amount += (price - discount_price) * item.quantity
        else:
            item_total = float(price * item.quantity)
            subtotal_amount += price * item.quantity
        
        # Сохраняем информацию о товаре для уведомления
        order_items_info.append({
            "name": product["name"],
            "quantity": item.quantity,
            "total": item_total
        })
    
    # Проверяем и применяем промокод, если указан
    promo_discount_amount = Decimal("0")
    delivery_fee = Decimal("500")  # Стандартная стоимость доставки
    
    if order_data.promo_code:
        from ..models.promo import PromoValidate
        from ..routes.promo import validate_promo
        
        # Проверяем, является ли это первым заказом
        user_orders = await db.fetch_one(
            "SELECT COUNT(*) as count FROM orders WHERE user_id = ?",
            (current_user.id,)
        )
        is_first_order = (user_orders and user_orders["count"] == 0) if user_orders else False
        
        # Валидируем промокод
        promo_validate = PromoValidate(
            code=order_data.promo_code,
            shop_id=order_data.shop_id,
            total_amount=subtotal_amount,
            is_first_order=is_first_order
        )
        
        # Получаем промокод напрямую через БД для валидации
        promo = await db.fetch_one(
            "SELECT * FROM promos WHERE code = ? AND is_active = 1",
            (order_data.promo_code.upper().strip(),)
        )
        
        if promo:
            from datetime import date
            from ..models.promo import PromoType
            
            today = date.today()
            promo_valid = True
            promo_type = PromoType(promo["promo_type"])
            promo_value = Decimal(str(promo["value"]))
            
            # Проверка дат
            if promo["valid_from"]:
                valid_from = date.fromisoformat(promo["valid_from"]) if isinstance(promo["valid_from"], str) else promo["valid_from"]
                if valid_from > today:
                    promo_valid = False
            if promo["valid_until"]:
                valid_until = date.fromisoformat(promo["valid_until"]) if isinstance(promo["valid_until"], str) else promo["valid_until"]
                if valid_until < today:
                    promo_valid = False
            
            # Проверка условий
            if promo_valid and promo["min_order_amount"]:
                if subtotal_amount < Decimal(str(promo["min_order_amount"])):
                    promo_valid = False
            
            if promo_valid and promo["shop_id"]:
                if promo["shop_id"] != order_data.shop_id:
                    promo_valid = False
            
            if promo_valid and promo["first_order_only"]:
                if not is_first_order:
                    promo_valid = False
            
            if promo_valid and promo["use_once"]:
                used = await db.fetch_one(
                    "SELECT COUNT(*) as count FROM orders WHERE user_id = ? AND promo_code = ?",
                    (current_user.id, order_data.promo_code.upper().strip())
                )
                if used and used["count"] > 0:
                    promo_valid = False
            
            # Вычисляем скидку
            if promo_valid:
                if promo_type == PromoType.PERCENT:
                    promo_discount_amount = (subtotal_amount * promo_value) / 100
                elif promo_type == PromoType.FIXED:
                    promo_discount_amount = min(promo_value, subtotal_amount)
                elif promo_type == PromoType.FREE_DELIVERY:
                    delivery_fee = Decimal("0")
                    promo_discount_amount = Decimal("0")
                
                # Увеличиваем счетчик использований промокода
                await db.execute(
                    "UPDATE promos SET usage_count = usage_count + 1 WHERE id = ?",
                    (promo["id"],)
                )
    
    # Итоговая сумма с учетом промокода и доставки
    total_amount = subtotal_amount - promo_discount_amount + delivery_fee
    
    # Создаём заказ
    order_dict = order_data.model_dump(exclude={"items"})
    order_dict["user_id"] = current_user.id
    order_dict["order_number"] = generate_order_number()
    order_dict["total_amount"] = float(total_amount)
    order_dict["discount_amount"] = float(discount_amount)
    order_dict["promo_discount_amount"] = float(promo_discount_amount)
    order_dict["delivery_fee"] = float(delivery_fee)
    
    order_id = await db.insert("orders", order_dict)
    
    # Добавляем товары в заказ и обновляем остатки
    for item in order_data.items:
        # Получаем полную информацию о товаре для сохранения названия
        product = await db.fetch_one(
            "SELECT name, price, discount_price FROM products WHERE id = ?",
            (item.product_id,)
        )
        
        # Сохраняем название товара в заказе (на случай, если товар будет удален)
        await db.insert("order_items", {
            "order_id": order_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": product["price"],
            "discount_price": product["discount_price"],
            "product_name": product["name"]  # Сохраняем название товара
        })
        
        # Уменьшаем остаток и увеличиваем счётчик продаж
        await db.execute(
            """UPDATE products 
               SET quantity = quantity - ?, sales_count = sales_count + ?
               WHERE id = ?""",
            (item.quantity, item.quantity, item.product_id)
        )
    
    await db.commit()
    
    # Удаляем товары из корзины
    product_ids = [item.product_id for item in order_data.items]
    placeholders = ",".join(["?" for _ in product_ids])
    await db.execute(
        f"DELETE FROM cart_items WHERE user_id = ? AND product_id IN ({placeholders})",
        (current_user.id,) + tuple(product_ids)
    )
    await db.commit()
    
    order = await db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
    
    # Форматируем дату и время доставки для уведомлений
    delivery_date_str = None
    delivery_time_str = None
    
    if order_data.delivery_date:
        from datetime import datetime
        try:
            if isinstance(order_data.delivery_date, str):
                delivery_date_obj = datetime.fromisoformat(order_data.delivery_date)
            else:
                delivery_date_obj = order_data.delivery_date
            delivery_date_str = delivery_date_obj.strftime("%d.%m.%Y")
        except:
            delivery_date_str = str(order_data.delivery_date)
    
    delivery_time_str = order_data.delivery_time
    
    # Отправляем уведомление владельцу магазина в Telegram
    if shop.get("telegram_id"):
        try:
            await telegram_notifier.send_order_notification(
                shop_owner_telegram_id=shop["telegram_id"],
                order_number=order_dict["order_number"],
                customer_name=order_data.recipient_name,
                customer_phone=order_data.recipient_phone,
                delivery_address=order_data.delivery_address,
                items=order_items_info,
                total_amount=float(total_amount),
                promo_code=order_data.promo_code if order_data.promo_code else None,
                promo_discount=float(promo_discount_amount),
                delivery_fee=float(delivery_fee),
                delivery_date=delivery_date_str,
                delivery_time=delivery_time_str,
                customer_telegram_id=current_user.telegram_id
            )
        except Exception as e:
            # Не прерываем выполнение, если уведомление не отправилось
            import traceback
            print(f"[ERROR] Failed to send order notification to shop owner: {e}")
            traceback.print_exc()
    
    # Отправляем сообщение с подтверждением заказа покупателю
    if current_user.telegram_id:
        try:
            # Получаем email пользователя из базы данных
            user_data = await db.fetch_one(
                "SELECT email FROM users WHERE id = ?",
                (current_user.id,)
            )
            customer_email = user_data.get("email") if user_data else None
            
            # Вычисляем сервисный сбор (если есть)
            # Сервисный сбор = общая сумма - (сумма товаров - промокод + доставка)
            calculated_total = float(subtotal_amount - promo_discount_amount + delivery_fee)
            service_fee = max(0, float(total_amount) - calculated_total)
            
            # Форматируем дату для временного слота
            delivery_date_for_slot = None
            if order_data.delivery_date:
                try:
                    if isinstance(order_data.delivery_date, str):
                        try:
                            date_obj = datetime.strptime(order_data.delivery_date, "%Y-%m-%d")
                        except:
                            date_obj = datetime.strptime(order_data.delivery_date, "%d.%m.%Y")
                        delivery_date_for_slot = date_obj.strftime("%Y-%m-%d")
                    else:
                        delivery_date_for_slot = order_data.delivery_date.strftime("%Y-%m-%d")
                except:
                    delivery_date_for_slot = str(order_data.delivery_date)
            
            await telegram_notifier.send_order_confirmation_to_customer(
                customer_telegram_id=current_user.telegram_id,
                order_number=order_dict["order_number"],
                customer_name=order_data.recipient_name,
                customer_phone=order_data.recipient_phone,
                customer_email=customer_email,
                delivery_address=order_data.delivery_address,
                delivery_date=delivery_date_for_slot,
                delivery_time=delivery_time_str,
                items=order_items_info,
                subtotal=float(subtotal_amount),
                delivery_fee=float(delivery_fee),
                service_fee=service_fee,
                promo_discount=float(promo_discount_amount),
                total_amount=float(total_amount)
            )
        except Exception as e:
            # Не прерываем выполнение, если уведомление не отправилось
            import traceback
            print(f"[ERROR] Failed to send order confirmation to customer: {e}")
            traceback.print_exc()
    
    return Order(**order)


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str = Query(..., description="New order status"),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет статус заказа (только для владельца магазина)."""
    # Проверяем, что заказ существует и пользователь - владелец магазина
    order = await db.fetch_one(
        """SELECT o.*, s.name as shop_name FROM orders o
           JOIN shops s ON o.shop_id = s.id
           WHERE o.id = ? AND s.owner_id = ?""",
        (order_id, current_user.id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or access denied")
    
    # Валидация статуса
    valid_statuses = ["pending", "processing", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    old_status = order["status"]
    
    await db.update("orders", {"status": status}, "id = ?", (order_id,))
    await db.commit()
    
    updated_order = await db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
    
    # Отправляем уведомление покупателю о смене статуса
    if old_status != status:
        print(f"[ORDER STATUS] Status changed from '{old_status}' to '{status}' for order {order_id}")
        
        # Получаем telegram_id покупателя
        buyer = await db.fetch_one(
            "SELECT telegram_id FROM users WHERE id = ?",
            (order["user_id"],)
        )
        
        print(f"[ORDER STATUS] Buyer user_id: {order['user_id']}, telegram_id: {buyer.get('telegram_id') if buyer else 'NOT FOUND'}")
        
        if buyer and buyer.get("telegram_id"):
            try:
                print(f"[ORDER STATUS] Sending notification to telegram_id: {buyer['telegram_id']}")
                result = await telegram_notifier.send_order_status_notification(
                    customer_telegram_id=buyer["telegram_id"],
                    order_id=order_id,
                    order_number=order["order_number"],
                    shop_id=order["shop_id"],
                    shop_name=order["shop_name"],
                    new_status=status,
                    total_amount=float(order["total_amount"])
                )
                print(f"[ORDER STATUS] Notification sent: {result}")
            except Exception as e:
                # Не прерываем выполнение, если уведомление не отправилось
                import traceback
                print(f"[ERROR] Failed to send status notification: {e}")
                traceback.print_exc()
        else:
            print(f"[ORDER STATUS] No telegram_id found for buyer, skipping notification")
    
    return Order(**updated_order)


@router.patch("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Отменяет заказ."""
    order = await db.fetch_one(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?",
        (order_id, current_user.id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Cannot cancel order in this status")
    
    # Возвращаем товары на склад
    items = await db.fetch_all(
        "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
        (order_id,)
    )
    for item in items:
        await db.execute(
            "UPDATE products SET quantity = quantity + ?, sales_count = sales_count - ? WHERE id = ?",
            (item["quantity"], item["quantity"], item["product_id"])
        )
    
    await db.update("orders", {"status": "cancelled"}, "id = ?", (order_id,))
    
    return {"message": "Order cancelled"}





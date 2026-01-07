"""
API Routes для корзины.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from decimal import Decimal

from ..models.cart import CartItem, CartItemCreate, CartItemUpdate, CartItemWithProduct
from ..models.user import User
from ..services.database import DatabaseService, get_db
from .users import get_current_user

router = APIRouter()


@router.get("/", response_model=List[CartItemWithProduct])
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает корзину пользователя."""
    items = await db.fetch_all(
        """SELECT ci.*,
                  p.name as product_name,
                  p.price as product_price,
                  p.discount_price as product_discount_price,
                  p.quantity as available_quantity,
                  p.is_active as product_active,
                  p.shop_id,
                  s.name as shop_name,
                  (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as product_image_url
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           JOIN shops s ON p.shop_id = s.id
           WHERE ci.user_id = ?
           ORDER BY ci.created_at DESC""",
        (current_user.id,)
    )
    
    return [
        CartItemWithProduct(
            **item,
            is_available=item["product_active"] and item["available_quantity"] >= item["quantity"]
        )
        for item in items
    ]


@router.get("/summary")
async def get_cart_summary(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает сводку по корзине."""
    items = await db.fetch_all(
        """SELECT ci.quantity,
                  COALESCE(p.discount_price, p.price) as final_price,
                  p.price as original_price,
                  p.shop_id
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           WHERE ci.user_id = ? AND p.is_active = 1""",
        (current_user.id,)
    )
    
    total_items = sum(item["quantity"] for item in items)
    total_amount = sum(Decimal(str(item["final_price"])) * item["quantity"] for item in items)
    total_original = sum(Decimal(str(item["original_price"])) * item["quantity"] for item in items)
    discount = total_original - total_amount
    shops_count = len(set(item["shop_id"] for item in items))
    
    return {
        "total_items": total_items,
        "total_amount": float(total_amount),
        "discount": float(discount),
        "shops_count": shops_count
    }


@router.post("/", response_model=CartItem)
async def add_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Добавляет товар в корзину."""
    # Проверяем товар
    product = await db.fetch_one(
        "SELECT id, quantity FROM products WHERE id = ? AND is_active = 1",
        (item_data.product_id,)
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["quantity"] < item_data.quantity:
        raise HTTPException(status_code=400, detail="Not enough items in stock")
    
    # Проверяем, есть ли уже в корзине
    existing = await db.fetch_one(
        "SELECT id, quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
        (current_user.id, item_data.product_id)
    )
    
    if existing:
        # Обновляем количество
        new_quantity = existing["quantity"] + item_data.quantity
        if new_quantity > product["quantity"]:
            raise HTTPException(status_code=400, detail="Not enough items in stock")
        
        await db.update(
            "cart_items",
            {"quantity": new_quantity},
            "id = ?",
            (existing["id"],)
        )
        item = await db.fetch_one("SELECT * FROM cart_items WHERE id = ?", (existing["id"],))
    else:
        # Создаём новую запись
        item_id = await db.insert("cart_items", {
            "user_id": current_user.id,
            "product_id": item_data.product_id,
            "quantity": item_data.quantity
        })
        item = await db.fetch_one("SELECT * FROM cart_items WHERE id = ?", (item_id,))
    
    return CartItem(**item)


@router.patch("/{item_id}", response_model=CartItem)
async def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет количество товара в корзине."""
    
    # Отладочная информация
    print(f"[DEBUG] update_cart_item called: item_id={item_id}")
    print(f"[DEBUG] item_update (raw): {item_update}")
    print(f"[DEBUG] item_update.model_dump(): {item_update.model_dump()}")
    print(f"[DEBUG] item_update.quantity: {item_update.quantity}, type: {type(item_update.quantity)}")
    print(f"[DEBUG] item_update.quantity repr: {repr(item_update.quantity)}")
    
    # Убеждаемся, что quantity - это целое число
    if not isinstance(item_update.quantity, int):
        print(f"[DEBUG] WARNING: quantity is not int! value={item_update.quantity}, type={type(item_update.quantity)}")
        print(f"[DEBUG] quantity dict: {item_update.quantity if isinstance(item_update.quantity, dict) else 'not a dict'}")
        # Пытаемся преобразовать
        try:
            # Если это словарь, попробуем извлечь значение
            if isinstance(item_update.quantity, dict) and 'quantity' in item_update.quantity:
                print(f"[DEBUG] Extracting quantity from dict: {item_update.quantity['quantity']}")
                item_update.quantity = int(item_update.quantity['quantity'])
            else:
                item_update.quantity = int(item_update.quantity)
        except (ValueError, TypeError, KeyError) as e:
            print(f"[DEBUG] ERROR converting quantity to int: {e}")
            raise HTTPException(
                status_code=422, 
                detail=f"Quantity must be an integer, got {type(item_update.quantity)}: {item_update.quantity}"
            )
    item = await db.fetch_one(
        """SELECT ci.*, p.quantity as available, p.is_active, p.name as product_name
           FROM cart_items ci
           JOIN products p ON ci.product_id = p.id
           WHERE ci.id = ? AND ci.user_id = ?""",
        (item_id, current_user.id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    if not item["is_active"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Товар '{item['product_name']}' недоступен"
        )
    
    if item_update.quantity > item["available"]:
        available = item["available"] or 0
        raise HTTPException(
            status_code=400, 
            detail=f"Недостаточно товара '{item['product_name']}' на складе. Доступно: {available}, требуется: {item_update.quantity}"
        )
    
    await db.update("cart_items", {"quantity": item_update.quantity}, "id = ?", (item_id,))
    await db.commit()
    
    updated = await db.fetch_one("SELECT * FROM cart_items WHERE id = ?", (item_id,))
    return CartItem(**updated)


@router.delete("/{item_id}")
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Удаляет товар из корзины."""
    item = await db.fetch_one(
        "SELECT id FROM cart_items WHERE id = ? AND user_id = ?",
        (item_id, current_user.id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    await db.delete("cart_items", "id = ?", (item_id,))
    return {"message": "Item removed from cart"}


@router.delete("/")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Очищает корзину."""
    await db.delete("cart_items", "user_id = ?", (current_user.id,))
    return {"message": "Cart cleared"}







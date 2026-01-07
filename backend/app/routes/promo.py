"""
API Routes для промокодов.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from decimal import Decimal
from datetime import date, datetime

from ..models.promo import (
    Promo, PromoCreate, PromoValidate, PromoValidationResult, PromoType
)
from ..models.user import User
from ..services.database import DatabaseService, get_db
from .users import get_current_user

router = APIRouter()


@router.post("/validate", response_model=PromoValidationResult)
async def validate_promo(
    promo_data: PromoValidate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Проверяет валидность промокода и возвращает размер скидки."""
    
    # Ищем промокод
    promo = await db.fetch_one(
        "SELECT * FROM promos WHERE code = ? AND is_active = 1",
        (promo_data.code.upper().strip(),)
    )
    
    if not promo:
        return PromoValidationResult(
            valid=False,
            message="Промокод не найден"
        )
    
    today = date.today()
    
    # Проверяем даты действия
    if promo["valid_from"] and date.fromisoformat(promo["valid_from"]) > today:
        return PromoValidationResult(
            valid=False,
            message="Промокод еще не начал действовать"
        )
    
    if promo["valid_until"] and date.fromisoformat(promo["valid_until"]) < today:
        return PromoValidationResult(
            valid=False,
            message="Промокод истек"
        )
    
    # Проверяем минимальную сумму заказа
    if promo["min_order_amount"]:
        min_amount = Decimal(str(promo["min_order_amount"]))
        if promo_data.total_amount < min_amount:
            return PromoValidationResult(
                valid=False,
                message=f"Минимальная сумма заказа для промокода: {min_amount} ₽"
            )
    
    # Проверяем, что промокод для определенного магазина
    if promo["shop_id"] and promo["shop_id"] != promo_data.shop_id:
        return PromoValidationResult(
            valid=False,
            message="Промокод недействителен для этого магазина"
        )
    
    # Проверяем, что только для первого заказа
    if promo["first_order_only"]:
        if not promo_data.is_first_order:
            return PromoValidationResult(
                valid=False,
                message="Промокод действует только для первого заказа"
            )
    
    # Проверяем, что промокод можно использовать только один раз
    if promo["use_once"]:
        # Проверяем, использовал ли пользователь уже этот промокод
        used = await db.fetch_one(
            "SELECT COUNT(*) as count FROM orders WHERE user_id = ? AND promo_code = ?",
            (current_user.id, promo_data.code.upper().strip())
        )
        if used and used["count"] > 0:
            return PromoValidationResult(
                valid=False,
                message="Промокод уже был использован"
            )
    
    # Вычисляем размер скидки
    discount_amount = Decimal("0")
    promo_type = PromoType(promo["promo_type"])
    value = Decimal(str(promo["value"]))
    
    if promo_type == PromoType.PERCENT:
        discount_amount = (promo_data.total_amount * value) / 100
    elif promo_type == PromoType.FIXED:
        discount_amount = min(value, promo_data.total_amount)  # Не больше суммы заказа
    elif promo_type == PromoType.FREE_DELIVERY:
        # Для бесплатной доставки скидка считается отдельно
        discount_amount = Decimal("0")
    
    return PromoValidationResult(
        valid=True,
        promo=Promo(**promo),
        discount_amount=discount_amount,
        discount_type=promo_type.value,
        message="Промокод применен"
    )


@router.post("/", response_model=Promo)
async def create_promo(
    promo_data: PromoCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Создает новый промокод (только для админов или владельцев магазинов)."""
    # TODO: Добавить проверку прав доступа
    
    promo_dict = promo_data.model_dump()
    promo_dict["code"] = promo_dict["code"].upper().strip()
    
    # Проверяем, не существует ли уже такой промокод
    existing = await db.fetch_one(
        "SELECT id FROM promos WHERE code = ?",
        (promo_dict["code"],)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Промокод с таким кодом уже существует")
    
    promo_id = await db.insert("promos", promo_dict)
    promo = await db.fetch_one("SELECT * FROM promos WHERE id = ?", (promo_id,))
    
    return Promo(**promo)


@router.get("/", response_model=List[Promo])
async def get_promos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    shop_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает список промокодов."""
    # TODO: Добавить проверку прав доступа
    
    if shop_id:
        promos = await db.fetch_all(
            "SELECT * FROM promos WHERE shop_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (shop_id, limit, skip)
        )
    else:
        promos = await db.fetch_all(
            "SELECT * FROM promos ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, skip)
        )
    
    return [Promo(**promo) for promo in promos]


@router.get("/{promo_id}", response_model=Promo)
async def get_promo(
    promo_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Получает промокод по ID."""
    promo = await db.fetch_one("SELECT * FROM promos WHERE id = ?", (promo_id,))
    if not promo:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    return Promo(**promo)



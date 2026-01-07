"""
API Routes для пользователей.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

from ..models.user import User, UserCreate, UserUpdate
from ..services.database import DatabaseService, get_db

router = APIRouter()


async def get_current_user(
    x_telegram_id: int = Header(..., alias="X-Telegram-ID"),
    db: DatabaseService = Depends(get_db)
) -> User:
    """Получает текущего пользователя по Telegram ID из заголовка.
    Если пользователь не найден, создаёт его автоматически (для dev режима).
    """
    user = await db.fetch_one(
        "SELECT * FROM users WHERE telegram_id = ?",
        (x_telegram_id,)
    )
    
    if not user:
        # Автоматически создаём пользователя (для dev режима)
        # В продакшене пользователь должен создаваться через /api/users/ при авторизации
        user_id = await db.insert("users", {
            "telegram_id": x_telegram_id,
            "username": f"user_{x_telegram_id}",
            "first_name": "Тестовый",
            "last_name": "Пользователь",
            "language_code": "ru",
            "is_premium": False
        })
        user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")
    
    return User(**user)


async def get_current_user_optional(
    x_telegram_id: Optional[int] = Header(None, alias="X-Telegram-ID"),
    db: DatabaseService = Depends(get_db)
) -> Optional[User]:
    """Получает текущего пользователя по Telegram ID из заголовка, если он предоставлен.
    Возвращает None, если заголовок не предоставлен (для публичных endpoints).
    """
    if x_telegram_id is None:
        return None
    
    user = await db.fetch_one(
        "SELECT * FROM users WHERE telegram_id = ?",
        (x_telegram_id,)
    )
    
    if not user:
        return None
    
    return User(**user)


@router.post("/", response_model=User)
async def create_or_update_user(
    user_data: UserCreate,
    db: DatabaseService = Depends(get_db)
):
    """Создаёт или обновляет пользователя (при авторизации в Mini App)."""
    existing = await db.fetch_one(
        "SELECT * FROM users WHERE telegram_id = ?",
        (user_data.telegram_id,)
    )
    
    if existing:
        # Обновляем данные
        await db.update(
            "users",
            {
                "username": user_data.username,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "language_code": user_data.language_code,
                "is_premium": user_data.is_premium,
            },
            "telegram_id = ?",
            (user_data.telegram_id,)
        )
        user = await db.fetch_one(
            "SELECT * FROM users WHERE telegram_id = ?",
            (user_data.telegram_id,)
        )
    else:
        # Создаём нового
        user_id = await db.insert("users", user_data.model_dump())
        user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    
    return User(**user)


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получает данные текущего пользователя."""
    return current_user


@router.patch("/me", response_model=User)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет данные текущего пользователя."""
    update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
    
    if update_data:
        await db.update("users", update_data, "id = ?", (current_user.id,))
    
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (current_user.id,))
    return User(**user)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    db: DatabaseService = Depends(get_db)
):
    """Получает пользователя по ID."""
    user = await db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)




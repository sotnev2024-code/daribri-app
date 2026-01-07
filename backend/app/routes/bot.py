"""
Роуты для работы с ботом.
"""

from fastapi import APIRouter, Depends
from ..models.user import User
from ..services.database import get_db, DatabaseService
from ..routes.users import get_current_user
from ..config import settings
import httpx

router = APIRouter()


@router.get("/username")
async def get_bot_username(
    current_user: User = Depends(get_current_user)
):
    """Получает username бота."""
    if not settings.BOT_TOKEN:
        return {"username": None, "error": "BOT_TOKEN not configured"}
    
    try:
        # Получаем информацию о боте через Telegram Bot API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getMe"
            )
            data = response.json()
            
            if data.get("ok") and data.get("result"):
                return {
                    "username": data["result"].get("username"),
                    "bot_username": data["result"].get("username"),
                    "first_name": data["result"].get("first_name")
                }
            else:
                return {"username": None, "error": "Failed to get bot info"}
    except Exception as e:
        return {"username": None, "error": str(e)}


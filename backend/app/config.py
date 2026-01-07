"""
Конфигурация приложения.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


# Определяем корень проекта (где лежит .env)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Приложение
    APP_NAME: str = "Дарибри"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Telegram Bot
    BOT_TOKEN: str = ""
    WEBAPP_URL: str = ""  # URL фронтенда Mini App
    
    # Сервер
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # База данных
    DATABASE_PATH: Path = PROJECT_ROOT / "database" / "miniapp.db"
    
    # Загрузка медиа
    UPLOADS_DIR: Path = PROJECT_ROOT / "uploads"
    PRODUCTS_MEDIA_DIR: Path = UPLOADS_DIR / "products"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: list = ["video/mp4", "video/webm"]
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Безопасность
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Yandex Maps API
    YANDEX_API_KEY: str = ""  # API ключ для Yandex Geocoder API (получить на https://developer.tech.yandex.ru/)
    
    # Telegram Bot
    SHOP_REQUESTS_GROUP_ID: int = -1003694178126  # ID группы для заявок на магазины
    SHOP_REQUESTS_TOPIC_ID: int = 2  # ID подтемы в группе
    ADMIN_IDS: str = ""  # Список ID администраторов через запятую (например: "123456789,987654321")
    
    # YooKassa Payments
    API_KEY_YOOKASSA: str = ""  # API ключ от YooKassa для Telegram
    
    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()

# Логируем загрузку конфигурации
print(f"[CONFIG] Loading from: {ENV_FILE}")
print(f"[CONFIG] ENV file exists: {ENV_FILE.exists()}")
print(f"[CONFIG] BOT_TOKEN configured: {'Yes' if settings.BOT_TOKEN else 'No'}")
print(f"[CONFIG] WEBAPP_URL: {settings.WEBAPP_URL or 'Not set'}")





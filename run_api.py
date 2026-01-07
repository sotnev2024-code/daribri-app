"""
Запуск API сервера и Telegram бота.
"""

import asyncio
import threading
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем backend в путь
import sys
sys.path.insert(0, str(Path(__file__).parent / "backend"))


def run_api_server():
    """Запускает FastAPI сервер."""
    import os
    from backend.app.config import settings
    
    host = os.getenv("HOST", settings.HOST)
    port = int(os.getenv("PORT", settings.PORT))
    
    # В потоке нельзя использовать reload=True из-за проблем с сигналами на Windows
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=False,  # Отключаем reload для работы в потоке
    )


def run_telegram_bot():
    """Запускает Telegram бота."""
    from backend.bot.main import run_bot
    
    bot_token = os.getenv("BOT_TOKEN")
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")
    
    if not bot_token:
        print("[ERROR] BOT_TOKEN not set in .env file!")
        print("[ERROR] Please add BOT_TOKEN=your_bot_token to .env file")
        print("[WARNING] Bot will not start.")
        return
    
    if bot_token == "your_bot_token_here" or len(bot_token.strip()) == 0:
        print("[ERROR] BOT_TOKEN is not configured properly!")
        print("[ERROR] Please set a valid BOT_TOKEN in .env file")
        print("[ERROR] You can get your bot token from @BotFather in Telegram")
        print("[WARNING] Bot will not start.")
        return
    
    print(f"[INFO] Bot token found (length: {len(bot_token)})")
    run_bot(bot_token, webapp_url)


if __name__ == "__main__":
    import os
    from backend.app.config import settings
    
    host = os.getenv("HOST", settings.HOST)
    port = int(os.getenv("PORT", settings.PORT))
    
    print("=" * 50)
    print("  Telegram Mini App - API Server + Bot")
    print("=" * 50)
    print()
    print(f"[INFO] Starting API server on http://{host}:{port}")
    print(f"[INFO] Docs: http://{host}:{port}/docs")
    print()
    
    # Запускаем API сервер в отдельном потоке
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Даём API серверу немного времени на запуск
    import time
    time.sleep(2)
    
    print("[INFO] API server started in background thread")
    print("[INFO] Starting Telegram bot...")
    print()
    
    # Запускаем бота в главном потоке
    try:
        run_telegram_bot()
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
    finally:
        print("[INFO] Stopped")

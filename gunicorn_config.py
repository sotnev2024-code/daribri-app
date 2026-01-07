"""
Конфигурация Gunicorn для production.
Используется только для API сервера, бот запускается отдельно.
"""

import multiprocessing
import os
from pathlib import Path

# Количество воркеров
workers = multiprocessing.cpu_count() * 2 + 1

# Класс воркера (для async приложений)
worker_class = "uvicorn.workers.UvicornWorker"

# Биндинг
bind = "127.0.0.1:8000"

# Логи
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

accesslog = str(log_dir / "access.log")
errorlog = str(log_dir / "error.log")
loglevel = "info"

# Таймауты
timeout = 120
keepalive = 5

# Перезагрузка воркеров
max_requests = 1000
max_requests_jitter = 50

# Уровень детализации
capture_output = True
enable_stdio_inheritance = True




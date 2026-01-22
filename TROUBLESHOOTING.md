# Диагностика проблем с сервером

## Как посмотреть логи сервера

### 1. Логи systemd сервиса (основной способ)

```bash
# Посмотреть последние логи (50 строк)
sudo journalctl -u daribri -n 50

# Посмотреть логи в реальном времени (следить за новыми записями)
sudo journalctl -u daribri -f

# Посмотреть логи за последний час
sudo journalctl -u daribri --since "1 hour ago"

# Посмотреть логи за сегодня
sudo journalctl -u daribri --since today

# Посмотреть логи с определенного времени
sudo journalctl -u daribri --since "2024-01-16 10:00:00"
```

### 2. Проверить статус сервиса

```bash
# Статус сервиса
sudo systemctl status daribri

# Если сервис не запущен, попробуйте запустить
sudo systemctl start daribri

# Если есть ошибки, перезагрузите конфигурацию systemd
sudo systemctl daemon-reload
sudo systemctl restart daribri
```

### 3. Проверить логи Python напрямую

Если приложение запускается не через systemd:

```bash
# Перейти в директорию проекта
cd /var/www/daribri

# Запустить вручную и посмотреть ошибки
/var/www/daribri/venv/bin/python /var/www/daribri/run_api.py
```

## Частые проблемы после обновления

### Проблема 1: Отсутствуют зависимости

После добавления `openpyxl` нужно установить зависимости:

```bash
cd /var/www/daribri
source venv/bin/activate
pip install -r requirements.txt
```

Или если venv не активирован:

```bash
/var/www/daribri/venv/bin/pip install -r requirements.txt
```

### Проблема 2: Ошибки импорта

Проверьте, что все файлы скопированы:

```bash
cd /var/www/daribri

# Проверить наличие новых файлов
ls -la backend/bot/handlers/shops_admin.py
ls -la backend/bot/handlers/products_admin.py
ls -la backend/bot/handlers/orders_admin.py
ls -la backend/bot/handlers/analytics_admin.py
ls -la backend/app/routes/admin.py
```

### Проблема 3: Ошибки синтаксиса Python

Проверьте синтаксис файлов:

```bash
cd /var/www/daribri

# Проверить синтаксис основных файлов
/var/www/daribri/venv/bin/python -m py_compile backend/app/routes/admin.py
/var/www/daribri/venv/bin/python -m py_compile backend/bot/handlers/shops_admin.py
/var/www/daribri/venv/bin/python -m py_compile backend/bot/handlers/products_admin.py
/var/www/daribri/venv/bin/python -m py_compile backend/bot/handlers/orders_admin.py
/var/www/daribri/venv/bin/python -m py_compile backend/bot/handlers/analytics_admin.py
```

### Проблема 4: Неправильные пути или права доступа

```bash
# Проверить права доступа
sudo chown -R www-data:www-data /var/www/daribri
sudo chmod +x /var/www/daribri/run_api.py

# Проверить, что файлы существуют
ls -la /var/www/daribri/run_api.py
ls -la /var/www/daribri/backend/app/main.py
```

## Полная процедура обновления на сервере

```bash
# 1. Остановить сервис
sudo systemctl stop daribri

# 2. Перейти в директорию проекта
cd /var/www/daribri

# 3. Обновить код из GitHub
git pull origin main

# 4. Установить/обновить зависимости
/var/www/daribri/venv/bin/pip install -r requirements.txt

# 5. Проверить синтаксис (опционально)
/var/www/daribri/venv/bin/python -c "import backend.app.main"

# 6. Установить права
sudo chown -R www-data:www-data /var/www/daribri

# 7. Перезагрузить systemd
sudo systemctl daemon-reload

# 8. Запустить сервис
sudo systemctl start daribri

# 9. Проверить статус
sudo systemctl status daribri

# 10. Посмотреть логи
sudo journalctl -u daribri -f
```

## Диагностика конкретных ошибок

### Ошибка: "ModuleNotFoundError: No module named 'openpyxl'"

```bash
/var/www/daribri/venv/bin/pip install openpyxl>=3.1.0
```

### Ошибка: "ImportError: cannot import name 'admin_router'"

Проверьте, что файл `backend/app/routes/admin.py` существует и содержит правильный код.

### Ошибка: "AttributeError: 'Settings' object has no attribute 'WEBAPP_URL'"

Проверьте файл `.env` в `/var/www/daribri/.env` - должно быть:
```
WEBAPP_URL=https://your-domain.com
```

### Ошибка: "Connection refused" или "502 Bad Gateway"

1. Проверьте, что сервис запущен: `sudo systemctl status daribri`
2. Проверьте, что порт не занят: `sudo netstat -tulpn | grep 8000`
3. Проверьте логи nginx: `sudo tail -f /var/log/nginx/error.log`

## Быстрая проверка работоспособности

```bash
# Проверить, что API отвечает
curl http://localhost:8000/api/health

# Проверить, что админ API доступен (требует авторизации)
curl -H "X-Telegram-ID: YOUR_ADMIN_TELEGRAM_ID" http://localhost:8000/api/admin/analytics/platform
```

## Если ничего не помогает

1. Посмотрите полные логи: `sudo journalctl -u daribri -n 100 --no-pager`
2. Попробуйте запустить вручную: `/var/www/daribri/venv/bin/python /var/www/daribri/run_api.py`
3. Проверьте версию Python: `/var/www/daribri/venv/bin/python --version` (должна быть 3.10+)
4. Проверьте, что все файлы обновлены: `cd /var/www/daribri && git status`


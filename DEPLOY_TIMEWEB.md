# Развертывание на Timeweb Cloud

## Подготовка

### 1. Подключение к серверу

```bash
# Подключитесь к серверу через SSH
ssh root@your-server-ip
# или
ssh root@msk-1-vm-59zc  # если у вас есть имя сервера
```

### 2. Обновление системы

```bash
apt update && apt upgrade -y
```

### 3. Установка необходимых пакетов

```bash
# Python и pip
apt install -y python3 python3-pip python3-venv

# Nginx
apt install -y nginx

# Git
apt install -y git

# Дополнительные утилиты
apt install -y curl wget
```

## Развертывание приложения

### 1. Создание директории

```bash
mkdir -p /var/www/daribri
cd /var/www/daribri
```

### 2. Клонирование репозитория

```bash
# Клонируйте проект из GitHub
git clone https://github.com/sotnev2024-code/daribri-app.git .

# Настройте безопасность Git (если нужно)
git config --global --add safe.directory /var/www/daribri

# Проверьте, что файлы загружены
ls -la
```

### 3. Создание виртуального окружения

```bash
cd /var/www/daribri
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

```bash
# Создайте файл .env
nano .env
```

**Содержимое `.env` файла:**

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here
WEBAPP_URL=https://flow.plus-shop.ru

# Server
HOST=127.0.0.1
PORT=8000

# Database (путь будет автоматически определен)
# DATABASE_PATH=/var/www/daribri/database/miniapp.db

# Yandex Maps API (опционально)
YANDEX_API_KEY=your_yandex_api_key

# Telegram Bot Settings
SHOP_REQUESTS_GROUP_ID=-1003694178126
SHOP_REQUESTS_TOPIC_ID=2
ADMIN_IDS=your_telegram_id

# YooKassa Payments (опционально)
API_KEY_YOOKASSA=your_yookassa_key

# Security
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=False
```

**Сохраните файл:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 5. Создание необходимых директорий

```bash
# Создайте папки для медиа файлов
mkdir -p uploads/products uploads/shops uploads/shop_requests

# Создайте папку для базы данных (если нужно)
mkdir -p database

# Установите права доступа
chown -R www-data:www-data /var/www/daribri
chmod -R 755 /var/www/daribri
chmod 600 .env  # Секретный файл
```

### 6. Инициализация базы данных

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите инициализацию БД
python database/init_db.py
```

## Настройка Systemd

### 1. Копирование сервиса

```bash
cp /var/www/daribri/systemd/daribri.service /etc/systemd/system/
```

### 2. Редактирование сервиса (если нужно)

```bash
nano /etc/systemd/system/daribri.service
```

**Убедитесь, что пути правильные:**
- `WorkingDirectory=/var/www/daribri`
- `Environment="PATH=/var/www/daribri/venv/bin"`
- `ExecStart=/var/www/daribri/venv/bin/python /var/www/daribri/run_api.py`

### 3. Запуск сервиса

```bash
# Перезагрузите systemd
systemctl daemon-reload

# Включите автозапуск
systemctl enable daribri

# Запустите сервис
systemctl start daribri

# Проверьте статус
systemctl status daribri
```

## Настройка Nginx

### 1. Создание конфигурации

```bash
nano /etc/nginx/sites-available/daribri
```

**Содержимое файла:**

```nginx
server {
    listen 80;
    server_name flow.plus-shop.ru www.flow.plus-shop.ru;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    access_log /var/log/nginx/daribri_access.log;
    error_log /var/log/nginx/daribri_error.log;
}
```

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 2. Активация конфигурации

```bash
# Создайте символическую ссылку
ln -s /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/

# Удалите дефолтную конфигурацию (если есть)
rm -f /etc/nginx/sites-enabled/default

# Проверьте конфигурацию
nginx -t

# Перезагрузите Nginx
systemctl reload nginx
```

## Настройка SSL (HTTPS)

### 1. Установка Certbot

```bash
apt install -y certbot python3-certbot-nginx
```

### 2. Получение SSL сертификата

```bash
certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru
```

**Во время установки:**
1. Введите email для уведомлений
2. Согласитесь с условиями: `A`
3. Редирект HTTP → HTTPS: выберите `2` (Redirect)

### 3. Проверка автоматического обновления

```bash
# Проверьте таймер
systemctl status certbot.timer

# Тестовый запуск обновления
certbot renew --dry-run
```

## Проверка работы

### 1. Проверка API

```bash
curl http://localhost:8000/api/health
```

### 2. Проверка логов

```bash
# Логи приложения
journalctl -u daribri -f

# Логи Nginx
tail -f /var/log/nginx/daribri_access.log
tail -f /var/log/nginx/daribri_error.log
```

### 3. Проверка статуса

```bash
systemctl status daribri
systemctl status nginx
```

### 4. Проверка в браузере

Откройте:
- `https://flow.plus-shop.ru` - должен открыться приложение
- `http://flow.plus-shop.ru` - должен перенаправить на HTTPS

## Обновление приложения (после изменений)

### Вариант 1: Через Git (рекомендуется)

```bash
# На сервере
cd /var/www/daribri

# Остановите сервис
systemctl stop daribri

# Обновите код
git pull origin main

# Обновите зависимости (если изменились)
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Установите права
chown -R www-data:www-data /var/www/daribri
chmod -R 755 /var/www/daribri

# Запустите сервис
systemctl start daribri

# Проверьте статус
systemctl status daribri
```

### Вариант 2: Через скрипт

```bash
cd /var/www/daribri
chmod +x update.sh
sudo ./update.sh
```

## Устранение проблем

### Если сервис не запускается

```bash
# Проверьте логи
journalctl -u daribri -n 50 --no-pager

# Проверьте конфигурацию
cat /etc/systemd/system/daribri.service

# Проверьте права доступа
ls -la /var/www/daribri
```

### Если Nginx не работает

```bash
# Проверьте конфигурацию
nginx -t

# Проверьте логи
tail -f /var/log/nginx/error.log

# Проверьте статус
systemctl status nginx
```

### Если не открывается сайт

```bash
# Проверьте, что сервис работает
systemctl status daribri

# Проверьте, что Nginx работает
systemctl status nginx

# Проверьте, что порт 8000 слушается
netstat -tlnp | grep 8000

# Проверьте DNS
nslookup flow.plus-shop.ru
```

## Чеклист после развертывания

- [ ] Код клонирован из GitHub
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены
- [ ] Файл `.env` создан и заполнен
- [ ] Папки `uploads/` созданы
- [ ] База данных инициализирована
- [ ] Systemd сервис настроен и запущен
- [ ] Nginx настроен и работает
- [ ] SSL сертификат установлен
- [ ] Сайт открывается по HTTPS
- [ ] API отвечает на запросы
- [ ] Бот работает

## Готово! 🎉

Приложение развернуто на Timeweb Cloud и доступно по адресу:
- **https://flow.plus-shop.ru**

Для обновления кода используйте:
```bash
cd /var/www/daribri && git pull origin main && systemctl restart daribri
```


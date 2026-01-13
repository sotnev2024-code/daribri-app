# Возврат домена на flow.plus-shop.ru

## Шаг 1: Обновление конфигурации Nginx на сервере

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Обновите конфигурацию Nginx
sudo nano /etc/nginx/sites-available/daribri
```

**Замените содержимое на:**

```nginx
server {
    listen 80;
    server_name flow.plus-shop.ru www.flow.plus-shop.ru;

    # Максимальный размер загружаемых файлов
    client_max_body_size 50M;

    # Проксирование на FastAPI приложение
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

    # Логи
    access_log /var/log/nginx/daribri_access.log;
    error_log /var/log/nginx/daribri_error.log;
}
```

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

```bash
# Проверьте синтаксис
sudo nginx -t

# Перезагрузите Nginx
sudo systemctl reload nginx

# Проверьте статус
sudo systemctl status nginx
```

---

## Шаг 2: Обновление SSL сертификата (если был установлен для daribri.ru)

Если у вас был SSL сертификат для `daribri.ru`, нужно получить новый для `flow.plus-shop.ru`:

```bash
# Проверьте текущие сертификаты
sudo certbot certificates

# Если есть сертификат для daribri.ru, можно его удалить (опционально)
sudo certbot delete --cert-name daribri.ru

# Получите сертификат для flow.plus-shop.ru
sudo certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru
```

**Или если сертификат уже был для flow.plus-shop.ru:**

```bash
# Просто обновите конфигурацию Nginx
sudo certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru --force-renewal
```

---

## Шаг 3: Обновление конфигурации приложения (.env)

```bash
cd /var/www/daribri
sudo nano .env
```

**Обновите строку `WEBAPP_URL`:**

```env
WEBAPP_URL=https://flow.plus-shop.ru
```

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

```bash
# Перезапустите приложение
sudo systemctl restart daribri
sudo systemctl status daribri
```

---

## Шаг 4: Проверка работы

```bash
# 1. Проверьте конфигурацию Nginx
sudo nginx -t

# 2. Проверьте доступность
curl -I http://flow.plus-shop.ru
curl -I https://flow.plus-shop.ru

# 3. Проверьте статус сервисов
sudo systemctl status nginx
sudo systemctl status daribri
```

---

## Шаг 5: Проверка в браузере

Откройте в браузере:
- `https://flow.plus-shop.ru` - должен открыться приложение
- `http://flow.plus-shop.ru` - должен перенаправить на HTTPS

---

## Если нужно обновить Telegram Bot

Если у вас настроен Telegram Bot, обновите URL Mini App:

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/mybots`
3. Выберите вашего бота
4. Выберите "Bot Settings" → "Menu Button" или "Web App"
5. Установите URL: `https://flow.plus-shop.ru`

---

## Готово! ✅

После выполнения всех шагов домен `flow.plus-shop.ru` должен снова работать.

---

## Быстрое восстановление (все команды сразу)

```bash
# 1. Обновите конфигурацию Nginx
sudo nano /etc/nginx/sites-available/daribri
# Замените server_name на: flow.plus-shop.ru www.flow.plus-shop.ru

# 2. Проверьте и перезагрузите
sudo nginx -t
sudo systemctl reload nginx

# 3. Обновите .env
cd /var/www/daribri
sudo nano .env
# Измените: WEBAPP_URL=https://flow.plus-shop.ru

# 4. Перезапустите приложение
sudo systemctl restart daribri

# 5. Обновите SSL (если нужно)
sudo certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru

# 6. Проверьте
curl -I https://flow.plus-shop.ru
```


# Исправление ошибки Nginx: cannot load certificate

## Проблема

Nginx не запускается из-за ошибки:
```
nginx: [emerg] cannot load certificate "/etc/letsencrypt/live/daribri.ru/fullchain.pem"
```

Это означает, что в конфигурации Nginx указан SSL сертификат, которого не существует.

## Решение

### Шаг 1: Проверьте конфигурацию Nginx

```bash
# Проверьте конфигурацию
sudo cat /etc/nginx/sites-available/daribri
```

### Шаг 2: Временно отключите HTTPS блок

```bash
# Откройте конфигурацию
sudo nano /etc/nginx/sites-available/daribri
```

**Убедитесь, что конфигурация выглядит так (только HTTP, без HTTPS):**

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

**ВАЖНО:** Убедитесь, что нет блока `server` для порта 443 (HTTPS), который ссылается на несуществующий сертификат.

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Шаг 3: Проверьте синтаксис и запустите Nginx

```bash
# Проверьте синтаксис
sudo nginx -t

# Если всё ОК, запустите Nginx
sudo systemctl start nginx

# Проверьте статус
sudo systemctl status nginx
```

### Шаг 4: Проверьте работу

```bash
# Проверьте доступность
curl -I http://flow.plus-shop.ru
curl -I http://localhost

# Должны вернуть HTTP ответ
```

---

## Если нужно удалить старую HTTPS конфигурацию

Если в конфигурации есть блок для HTTPS с несуществующим сертификатом:

```bash
# Откройте конфигурацию
sudo nano /etc/nginx/sites-available/daribri
```

**Удалите или закомментируйте блок:**

```nginx
# Закомментируйте этот блок, если он есть:
# server {
#     listen 443 ssl http2;
#     server_name daribri.ru www.daribri.ru;
#     ...
#     ssl_certificate /etc/letsencrypt/live/daribri.ru/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/daribri.ru/privkey.pem;
#     ...
# }
```

**Оставьте только HTTP блок (порт 80) для flow.plus-shop.ru**

---

## После исправления: получение SSL сертификата

После того, как Nginx запустится на HTTP:

```bash
# 1. Убедитесь, что домен доступен
curl -I http://flow.plus-shop.ru
# Должен вернуть HTTP ответ

# 2. Добавьте location для acme-challenge
sudo nano /etc/nginx/sites-available/daribri
```

**Добавьте перед location /:**

```nginx
location /.well-known/acme-challenge/ {
    root /var/www/html;
    try_files $uri =404;
}
```

```bash
# 3. Создайте директорию
sudo mkdir -p /var/www/html/.well-known/acme-challenge
sudo chown -R www-data:www-data /var/www/html/.well-known
sudo chmod -R 755 /var/www/html/.well-known

# 4. Перезагрузите Nginx
sudo nginx -t
sudo systemctl reload nginx

# 5. Получите SSL сертификат
sudo certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru
```

Certbot автоматически добавит HTTPS блок в конфигурацию.

---

## Быстрое исправление (все команды сразу)

```bash
# 1. Откройте конфигурацию
sudo nano /etc/nginx/sites-available/daribri

# 2. Убедитесь, что есть только HTTP блок (порт 80) для flow.plus-shop.ru
#    Удалите или закомментируйте HTTPS блок с daribri.ru

# 3. Проверьте синтаксис
sudo nginx -t

# 4. Запустите Nginx
sudo systemctl start nginx

# 5. Проверьте статус
sudo systemctl status nginx

# 6. Проверьте работу
curl -I http://flow.plus-shop.ru
```

---

## Проверка текущих сертификатов

```bash
# Проверьте, какие сертификаты есть
sudo certbot certificates

# Если есть сертификат для flow.plus-shop.ru, он должен работать
# Если есть сертификат для daribri.ru, но его нет в файловой системе, удалите его:
# sudo certbot delete --cert-name daribri.ru
```

---

## Готово! ✅

После исправления конфигурации Nginx должен запуститься и работать на HTTP. Затем можно получить SSL сертификат для flow.plus-shop.ru.


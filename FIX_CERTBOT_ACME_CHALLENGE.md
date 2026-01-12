# Исправление ошибки Certbot: 404 на .well-known/acme-challenge

## Проблема

Certbot не может получить доступ к `.well-known/acme-challenge/` и выдает ошибку 404.

## Решение

### Шаг 1: Проверьте, что сайт работает по HTTP

```bash
# Проверьте на сервере
curl -I http://daribri.ru

# Должен вернуть HTTP/1.1 200 OK или 301/302 редирект
```

Если не работает, проверьте конфигурацию Nginx.

### Шаг 2: Проверьте конфигурацию Nginx

```bash
# Проверьте текущую конфигурацию
cat /etc/nginx/sites-available/daribri

# Проверьте, что server_name правильный
grep server_name /etc/nginx/sites-available/daribri
```

### Шаг 3: Обновите конфигурацию Nginx

```bash
sudo nano /etc/nginx/sites-available/daribri
```

**Убедитесь, что конфигурация выглядит так (ВАЖНО: без редиректа на HTTPS до получения сертификата):**

```nginx
server {
    listen 80;
    server_name daribri.ru www.daribri.ru;

    # ВАЖНО: Добавьте location для acme-challenge ПЕРЕД основным location /
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

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

### Шаг 4: Создайте директорию для acme-challenge

```bash
# Создайте директорию (если не существует)
sudo mkdir -p /var/www/html/.well-known/acme-challenge

# Установите права
sudo chown -R www-data:www-data /var/www/html/.well-known
sudo chmod -R 755 /var/www/html/.well-known
```

### Шаг 5: Проверьте и перезагрузите Nginx

```bash
# Проверьте синтаксис
sudo nginx -t

# Если всё ОК, перезагрузите
sudo systemctl reload nginx

# Проверьте статус
sudo systemctl status nginx
```

### Шаг 6: Проверьте доступность acme-challenge

```bash
# Создайте тестовый файл
echo "test" | sudo tee /var/www/html/.well-known/acme-challenge/test.txt

# Проверьте доступность
curl http://daribri.ru/.well-known/acme-challenge/test.txt

# Должен вернуть: test

# Удалите тестовый файл
sudo rm /var/www/html/.well-known/acme-challenge/test.txt
```

### Шаг 7: Проверьте DNS

```bash
# Проверьте, что DNS указывает на правильный IP
nslookup daribri.ru
nslookup www.daribri.ru

# Должны вернуться IP адреса вашего сервера
```

### Шаг 8: Проверьте firewall

```bash
# Проверьте статус firewall
sudo ufw status

# Если порт 80 закрыт, откройте его
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Проверьте, что порт слушается
sudo netstat -tulpn | grep :80
```

### Шаг 9: Попробуйте получить сертификат снова

```bash
# Получите сертификат
sudo certbot --nginx -d daribri.ru -d www.daribri.ru

# Если всё ещё не работает, попробуйте standalone режим
sudo systemctl stop nginx
sudo certbot certonly --standalone -d daribri.ru -d www.daribri.ru
sudo systemctl start nginx

# Затем настройте Nginx вручную (см. ниже)
```

---

## Альтернативное решение: Standalone режим

Если nginx режим не работает, используйте standalone:

### 1. Остановите Nginx

```bash
sudo systemctl stop nginx
```

### 2. Получите сертификат в standalone режиме

```bash
sudo certbot certonly --standalone -d daribri.ru -d www.daribri.ru
```

**Во время установки:**
- Введите email
- Согласитесь с условиями: `A`
- Выберите редирект: `2` (Redirect)

### 3. Запустите Nginx

```bash
sudo systemctl start nginx
```

### 4. Обновите конфигурацию Nginx вручную

```bash
sudo nano /etc/nginx/sites-available/daribri
```

**Добавьте HTTPS блок:**

```nginx
# HTTP - редирект на HTTPS
server {
    listen 80;
    server_name daribri.ru www.daribri.ru;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name daribri.ru www.daribri.ru;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/daribri.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/daribri.ru/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

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
    access_log /var/log/nginx/daribri_ssl_access.log;
    error_log /var/log/nginx/daribri_ssl_error.log;
}
```

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 5. Проверьте и перезагрузите

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Проверка после исправления

```bash
# Проверьте HTTP (должен редиректить на HTTPS)
curl -I http://daribri.ru

# Проверьте HTTPS
curl -I https://daribri.ru

# Проверьте в браузере
# Откройте: https://daribri.ru
```

---

## Частые причины ошибки 404

1. **DNS не указывает на сервер** - проверьте через `nslookup daribri.ru`
2. **Nginx не настроен для домена** - проверьте `server_name` в конфигурации
3. **Порт 80 закрыт в firewall** - откройте через `ufw allow 80/tcp`
4. **Приложение не работает** - проверьте `systemctl status daribri`
5. **Конфликт с другой конфигурацией** - проверьте `/etc/nginx/sites-enabled/`

---

## Диагностика

Если проблема не решается, выполните диагностику:

```bash
# 1. Проверьте все конфигурации Nginx
ls -la /etc/nginx/sites-enabled/

# 2. Проверьте логи Nginx
sudo tail -f /var/log/nginx/error.log

# 3. Проверьте, что порт 80 слушается
sudo netstat -tulpn | grep :80

# 4. Проверьте доступность с сервера
curl -v http://daribri.ru/.well-known/acme-challenge/test

# 5. Проверьте DNS с разных серверов
dig daribri.ru
dig www.daribri.ru
```

---

## Готово! ✅

После исправления Certbot должен успешно получить сертификат, и ваш сайт будет доступен по HTTPS.


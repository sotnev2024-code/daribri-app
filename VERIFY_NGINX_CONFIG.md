# Проверка конфигурации Nginx перед получением SSL

## Шаг 1: Проверьте текущую конфигурацию

```bash
# Посмотрите конфигурацию
sudo cat /etc/nginx/sites-available/daribri
```

## Шаг 2: Убедитесь, что конфигурация правильная

Конфигурация должна выглядеть так:

```nginx
server {
    listen 80;
    server_name flow.plus-shop.ru www.flow.plus-shop.ru;

    client_max_body_size 50M;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

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

## Шаг 3: Проверьте синтаксис

```bash
# Проверьте синтаксис
sudo nginx -t
```

**Должно быть:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Шаг 4: Проверьте доступность домена

```bash
# Проверьте доступность
curl -I http://flow.plus-shop.ru
curl http://flow.plus-shop.ru
```

**Должен вернуть HTTP ответ (200, 301, 302 и т.д.)**

## Шаг 5: Проверьте директорию для acme-challenge

```bash
# Проверьте, что директория существует
ls -la /var/www/html/.well-known/acme-challenge/

# Если нет, создайте
sudo mkdir -p /var/www/html/.well-known/acme-challenge
sudo chown -R www-data:www-data /var/www/html/.well-known
sudo chmod -R 755 /var/www/html/.well-known
```

## Шаг 6: Получите SSL сертификат

Если всё проверено и работает:

```bash
# Получите SSL сертификат
sudo certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru
```

**Во время установки:**
1. Введите email для уведомлений
2. Согласитесь с условиями: `A`
3. Редирект HTTP → HTTPS: выберите `2` (Redirect)

Certbot автоматически:
- Получит SSL сертификат
- Обновит конфигурацию Nginx для HTTPS
- Настроит редирект с HTTP на HTTPS

## Шаг 7: Проверьте работу HTTPS

```bash
# Проверьте HTTPS
curl -I https://flow.plus-shop.ru

# Должен вернуть HTTP/2 200 или подобное
```

## Если есть ошибки

### Ошибка: "location directive is not allowed here"

**Решение:** Убедитесь, что все `location` директивы находятся внутри блока `server { ... }`

### Ошибка: "certificate not found"

**Решение:** Certbot автоматически создаст сертификат, просто следуйте инструкциям

### Ошибка: "domain verification failed"

**Решение:**
1. Проверьте, что домен доступен: `curl -I http://flow.plus-shop.ru`
2. Проверьте, что директория для acme-challenge существует
3. Проверьте firewall: `sudo ufw allow 80/tcp`

## Готово! ✅

После получения SSL сертификата ваш сайт будет доступен по HTTPS.


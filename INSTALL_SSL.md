# Установка HTTPS (SSL) для flow.plus-shop.ru

## Шаг 1: Установка Certbot

```bash
# Обновление пакетов
apt update

# Установка Certbot и плагина для Nginx
apt install -y certbot python3-certbot-nginx
```

## Шаг 2: Получение SSL сертификата

```bash
# Получение сертификата для домена
certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru
```

Certbot автоматически:
- Получит SSL сертификат от Let's Encrypt
- Обновит конфигурацию Nginx для использования HTTPS
- Настроит редирект с HTTP на HTTPS

**Во время установки вас спросят:**
1. Email адрес - введите ваш email (для уведомлений об истечении сертификата)
2. Согласие с условиями - введите `A` (Agree)
3. Редирект HTTP на HTTPS - выберите `2` (Redirect) - рекомендуется

## Шаг 3: Проверка автоматического обновления

```bash
# Проверка, что автоматическое обновление настроено
systemctl status certbot.timer

# Тестовый запуск обновления
certbot renew --dry-run
```

## Шаг 4: Проверка работы HTTPS

```bash
# Проверка локально
curl -I https://flow.plus-shop.ru

# Проверка статуса Nginx
systemctl status nginx
```

## Шаг 5: Проверка в браузере

Откройте в браузере:
- `https://flow.plus-shop.ru` - должен открыться с зеленым замочком
- `http://flow.plus-shop.ru` - должен автоматически перенаправить на HTTPS

## Что изменилось

После установки Certbot автоматически обновит файл `/etc/nginx/sites-available/daribri`:
- Добавит блок `server` для порта 443 (HTTPS)
- Настроит SSL сертификаты
- Добавит редирект с HTTP на HTTPS

## Ручная настройка (если автоматическая не сработала)

Если Certbot не смог автоматически настроить Nginx, выполните:

```bash
# 1. Получите сертификат без автоматической настройки
certbot certonly --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru

# 2. Отредактируйте конфигурацию вручную
nano /etc/nginx/sites-available/daribri
```

Добавьте блок для HTTPS:

```nginx
server {
    listen 80;
    server_name flow.plus-shop.ru www.flow.plus-shop.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name flow.plus-shop.ru www.flow.plus-shop.ru;

    ssl_certificate /etc/letsencrypt/live/flow.plus-shop.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/flow.plus-shop.ru/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

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

    access_log /var/log/nginx/daribri_ssl_access.log;
    error_log /var/log/nginx/daribri_ssl_error.log;
}
```

Затем:
```bash
nginx -t
systemctl reload nginx
```

## Обновление сертификата

Сертификаты Let's Encrypt действительны 90 дней. Certbot автоматически обновляет их, но можно проверить вручную:

```bash
# Проверка статуса сертификата
certbot certificates

# Ручное обновление (если нужно)
certbot renew

# Перезагрузка Nginx после обновления
systemctl reload nginx
```

## Устранение проблем

### Если Certbot не может получить сертификат:

1. Проверьте, что домен указывает на ваш сервер:
   ```bash
   nslookup flow.plus-shop.ru
   ```

2. Проверьте, что порт 80 открыт:
   ```bash
   ufw status
   ufw allow 80/tcp
   ufw allow 443/tcp
   ```

3. Проверьте, что Nginx работает:
   ```bash
   systemctl status nginx
   ```

### Если HTTPS не работает после установки:

```bash
# Проверьте логи
tail -f /var/log/nginx/error.log

# Проверьте конфигурацию
nginx -t

# Проверьте, что сертификаты существуют
ls -la /etc/letsencrypt/live/flow.plus-shop.ru/
```

## Готово! 🎉

После установки SSL ваш сайт будет доступен по HTTPS:
- `https://flow.plus-shop.ru` - основной адрес
- `http://flow.plus-shop.ru` - автоматически перенаправит на HTTPS


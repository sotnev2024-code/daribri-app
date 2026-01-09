# Исправление: показывается дефолтная страница nginx

## Проблема
Открывается стандартная страница nginx вместо вашего приложения. Это означает, что конфигурация для домена `flow.plus-shop.ru` не активна.

## Решение

### Шаг 1: Отключите дефолтную конфигурацию nginx

```bash
# Удалите или переименуйте дефолтную конфигурацию
rm /etc/nginx/sites-enabled/default
# или
mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.disabled
```

### Шаг 2: Создайте/обновите конфигурацию для вашего домена

```bash
nano /etc/nginx/sites-available/daribri
```

Убедитесь, что конфигурация выглядит так:

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

**Важно:** Замените `flow.plus-shop.ru` на ваш домен, если он другой.

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### Шаг 3: Активируйте конфигурацию

```bash
# Создайте символическую ссылку (если её нет)
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/daribri

# Проверьте, что ссылка создана
ls -la /etc/nginx/sites-enabled/
```

### Шаг 4: Проверьте и перезагрузите Nginx

```bash
# Проверка синтаксиса
nginx -t

# Если проверка прошла успешно, перезагрузите
systemctl reload nginx

# Или перезапустите
systemctl restart nginx
```

### Шаг 5: Проверьте работу

```bash
# Проверка локально
curl -H "Host: flow.plus-shop.ru" http://localhost/

# Проверка статуса
systemctl status nginx
```

## Быстрое исправление (все в одном)

```bash
# 1. Отключите дефолтную конфигурацию
rm -f /etc/nginx/sites-enabled/default

# 2. Создайте правильную конфигурацию
cat > /etc/nginx/sites-available/daribri << 'EOF'
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
EOF

# 3. Активируйте конфигурацию
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/daribri

# 4. Проверьте и перезагрузите
nginx -t && systemctl reload nginx

# 5. Проверьте работу
curl -H "Host: flow.plus-shop.ru" http://localhost/ | head -20
```

## Проверка после исправления

1. Откройте в браузере: `http://flow.plus-shop.ru`
2. Должна открыться ваша главная страница приложения
3. Проверьте API: `http://flow.plus-shop.ru/api/health`

## Если все еще не работает

```bash
# Проверьте активные конфигурации
ls -la /etc/nginx/sites-enabled/

# Проверьте логи
tail -f /var/log/nginx/error.log

# Проверьте, что приложение работает
systemctl status daribri
curl http://localhost:8000/api/health
```


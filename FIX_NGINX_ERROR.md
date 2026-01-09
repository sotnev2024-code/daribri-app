# Исправление ошибки nginx: unknown directive "nginx"

## Проблема
Ошибка означает, что файл конфигурации поврежден или содержит неправильный синтаксис.

## Решение

### Шаг 1: Проверьте содержимое файла

```bash
cat /etc/nginx/sites-available/daribri
```

Если видите что-то странное, файл поврежден.

### Шаг 2: Удалите поврежденный файл

```bash
rm /etc/nginx/sites-available/daribri
rm /etc/nginx/sites-enabled/daribri
```

### Шаг 3: Создайте правильный файл

```bash
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
```

### Шаг 4: Активируйте конфигурацию

```bash
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/daribri
```

### Шаг 5: Отключите дефолтную конфигурацию

```bash
rm -f /etc/nginx/sites-enabled/default
```

### Шаг 6: Проверьте и перезагрузите

```bash
nginx -t
systemctl reload nginx
```

## Альтернативный способ (через редактор)

```bash
# Удалите старые файлы
rm /etc/nginx/sites-available/daribri
rm /etc/nginx/sites-enabled/daribri

# Создайте новый файл
nano /etc/nginx/sites-available/daribri
```

Скопируйте и вставьте ТОЛЬКО это (без лишних символов):

```
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

**Важно:** 
- Убедитесь, что нет лишних символов в начале файла
- Убедитесь, что нет BOM (Byte Order Mark)
- Сохраните файл: `Ctrl+O`, `Enter`, `Ctrl+X`

Затем:
```bash
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/daribri
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```


# Исправление ошибки Nginx конфигурации

## Проблема

```
nginx: [emerg] unknown directive "nginx" in /etc/nginx/sites-enabled/daribri:2
```

Это означает, что в файле конфигурации есть неправильный синтаксис или лишний текст.

## Решение

### 1. Удалите неправильный файл

```bash
# Удалите неправильную конфигурацию
rm -f /etc/nginx/sites-enabled/daribri
rm -f /etc/nginx/sites-available/daribri
```

### 2. Создайте правильную конфигурацию

```bash
# Создайте директории (если не существуют)
mkdir -p /etc/nginx/sites-available
mkdir -p /etc/nginx/sites-enabled

# Создайте правильную конфигурацию
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

### 3. Активируйте конфигурацию

```bash
# Создайте символическую ссылку
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/

# Удалите дефолтную конфигурацию
rm -f /etc/nginx/sites-enabled/default
```

### 4. Проверьте синтаксис

```bash
# Проверьте синтаксис
nginx -t
```

**Должно вывести:** `nginx: configuration file /etc/nginx/nginx.conf test is successful`

### 5. Перезагрузите Nginx

```bash
systemctl reload nginx
```

### 6. Проверьте работу

```bash
# Проверка через Nginx
curl http://localhost/api/health

# Проверка статуса
systemctl status nginx
```

## Альтернатива: Используйте conf.d

Если проблемы с `sites-available` продолжаются, используйте `conf.d`:

```bash
# Удалите все неправильные конфигурации
rm -f /etc/nginx/sites-enabled/daribri
rm -f /etc/nginx/sites-available/daribri

# Создайте конфигурацию в conf.d
cat > /etc/nginx/conf.d/daribri.conf << 'EOF'
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

# Проверьте и перезагрузите
nginx -t
systemctl reload nginx
```

## Проверка содержимого файла

Если хотите проверить, что в файле:

```bash
# Проверьте содержимое
cat /etc/nginx/sites-enabled/daribri

# Или если используете conf.d
cat /etc/nginx/conf.d/daribri.conf
```

Файл должен содержать ТОЛЬКО блок `server { ... }` без лишнего текста.

## Готово! 🎉

После исправления сайт должен работать.



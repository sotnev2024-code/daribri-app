# Настройка Nginx (если sites-available не существует)

## Проблема

Директория `/etc/nginx/sites-available` не существует. Это может означать:
1. Nginx не установлен
2. Nginx установлен, но использует другую структуру конфигурации

## Решение

### 1. Проверьте, установлен ли Nginx

```bash
# Проверьте, установлен ли Nginx
which nginx
nginx -v

# Если не установлен, установите
apt update
apt install -y nginx
```

### 2. Проверьте структуру конфигурации Nginx

```bash
# Проверьте, где находится конфигурация
ls -la /etc/nginx/

# Проверьте основной конфигурационный файл
cat /etc/nginx/nginx.conf | grep -E "include|conf.d"
```

### 3. Создайте директории (если нужно)

```bash
# Создайте директории
mkdir -p /etc/nginx/sites-available
mkdir -p /etc/nginx/sites-enabled

# Добавьте в nginx.conf (если нет)
# Проверьте, есть ли в /etc/nginx/nginx.conf строка:
# include /etc/nginx/sites-enabled/*;
```

### 4. Обновите nginx.conf

```bash
nano /etc/nginx/nginx.conf
```

**Найдите блок `http {` и добавьте (если нет):**

```nginx
http {
    # ... существующие настройки ...
    
    # Включите конфигурации из sites-enabled
    include /etc/nginx/sites-enabled/*;
    
    # ... остальные настройки ...
}
```

**Или если используется `conf.d`:**

```nginx
http {
    # ... существующие настройки ...
    
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
    
    # ... остальные настройки ...
}
```

### 5. Альтернатива: Используйте conf.d

Если не хотите создавать `sites-available`, используйте `conf.d`:

```bash
# Создайте конфигурацию в conf.d
nano /etc/nginx/conf.d/daribri.conf
```

**Содержимое:**

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

### 6. Проверьте и перезагрузите

```bash
# Проверьте синтаксис
nginx -t

# Перезагрузите Nginx
systemctl reload nginx
```

## Быстрое решение (рекомендуется)

Выполните все команды сразу:

```bash
# 1. Установите Nginx (если не установлен)
apt update
apt install -y nginx

# 2. Создайте директории
mkdir -p /etc/nginx/sites-available
mkdir -p /etc/nginx/sites-enabled

# 3. Проверьте nginx.conf
grep -q "sites-enabled" /etc/nginx/nginx.conf || echo "include /etc/nginx/sites-enabled/*;" >> /etc/nginx/nginx.conf

# 4. Создайте конфигурацию
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

# 5. Активируйте
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/

# 6. Удалите дефолтную конфигурацию (если есть)
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# 7. Проверьте и перезагрузите
nginx -t
systemctl reload nginx

# 8. Проверьте работу
curl http://localhost/api/health
```

## Проверка после настройки

```bash
# Проверьте статус
systemctl status nginx

# Проверьте порты
ss -tulpn | grep :80

# Проверьте конфигурацию
nginx -t

# Проверьте логи
tail -f /var/log/nginx/error.log
```

## Готово! 🎉

После выполнения этих команд Nginx должен быть настроен и сайт должен работать.



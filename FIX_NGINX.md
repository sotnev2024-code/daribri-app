# Исправление проблемы с открытием приложения по домену

## Диагностика проблемы

### Шаг 1: Проверьте, работает ли API локально

```bash
# На сервере
curl http://localhost:8000/api/health
curl http://localhost:8000/
```

Если API работает локально, переходите к следующему шагу.

### Шаг 2: Проверьте конфигурацию Nginx

```bash
# Проверьте, что конфигурация правильная
cat /etc/nginx/sites-available/daribri

# Проверьте синтаксис
nginx -t

# Проверьте, что конфигурация активна
ls -la /etc/nginx/sites-enabled/
```

### Шаг 3: Проверьте логи Nginx

```bash
# Логи ошибок
tail -f /var/log/nginx/error.log

# Логи доступа
tail -f /var/log/nginx/access.log
```

### Шаг 4: Проверьте статус Nginx

```bash
systemctl status nginx
```

## Решение проблемы

### Вариант 1: Обновление конфигурации Nginx

```bash
nano /etc/nginx/sites-available/daribri
```

Убедитесь, что конфигурация выглядит так (замените `your-domain.com` на ваш домен):

```nginx
server {
    listen 80;
    server_name ваш-домен.com www.ваш-домен.com;

    client_max_body_size 50M;

    # Проксирование на FastAPI
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

Сохраните и перезагрузите Nginx:

```bash
nginx -t
systemctl reload nginx
```

### Вариант 2: Проверка DNS

Убедитесь, что DNS настроен правильно:

```bash
# Проверьте, что домен указывает на ваш сервер
nslookup ваш-домен.com
# или
dig ваш-домен.com
```

### Вариант 3: Проверка файрвола

```bash
# Проверьте, открыт ли порт 80
ufw status
# или
iptables -L

# Если нужно, откройте порты
ufw allow 80/tcp
ufw allow 443/tcp
```

### Вариант 4: Проверка работы FastAPI

```bash
# Проверьте, что приложение запущено
systemctl status daribri

# Проверьте логи
journalctl -u daribri -n 50

# Проверьте, что приложение слушает на порту 8000
netstat -tulpn | grep 8000
# или
ss -tulpn | grep 8000
```

## Полная проверка

Выполните все команды по порядку:

```bash
# 1. Проверка API
curl http://localhost:8000/api/health
echo ""

# 2. Проверка главной страницы
curl http://localhost:8000/ | head -20
echo ""

# 3. Проверка статуса сервиса
systemctl status daribri --no-pager -l

# 4. Проверка Nginx
systemctl status nginx --no-pager
nginx -t

# 5. Проверка портов
ss -tulpn | grep -E ':(80|8000)'

# 6. Проверка конфигурации Nginx
cat /etc/nginx/sites-available/daribri | grep server_name
```

## Быстрое исправление (если ничего не помогло)

```bash
# 1. Пересоздайте конфигурацию Nginx
cat > /etc/nginx/sites-available/daribri << 'EOF'
server {
    listen 80;
    server_name ваш-домен.com www.ваш-домен.com;

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

# 2. Активируйте конфигурацию
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/

# 3. Проверьте и перезагрузите
nginx -t && systemctl reload nginx

# 4. Проверьте работу
curl -I http://localhost/
```

## Проверка из браузера

После исправления откройте в браузере:
- `http://ваш-домен.com` - должна открыться главная страница
- `http://ваш-домен.com/api/health` - должен вернуться JSON с статусом

## Если все еще не работает

Проверьте логи:

```bash
# Логи приложения
journalctl -u daribri -f

# Логи Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/daribri_error.log
```


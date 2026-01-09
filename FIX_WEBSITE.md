# Исправление проблем с сайтом

## Быстрое исправление

Выполните на сервере:

```bash
cd /var/www/daribri
chmod +x fix_website.sh
sudo ./fix_website.sh
```

## Ручное исправление (пошагово)

### 1. Проверьте, работает ли API локально

```bash
curl http://localhost:8000/api/health
```

**Должен вернуть:** `{"status":"healthy"}`

Если не работает:

```bash
# Проверьте статус сервиса
systemctl status daribri

# Перезапустите сервис
systemctl restart daribri

# Проверьте логи
journalctl -u daribri -n 50 --no-pager
```

### 2. Обновите конфигурацию Nginx

```bash
nano /etc/nginx/sites-available/daribri
```

**Замените содержимое на:**

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

### 3. Активируйте конфигурацию

```bash
# Создайте символическую ссылку
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/

# Удалите дефолтную конфигурацию
rm -f /etc/nginx/sites-enabled/default

# Проверьте синтаксис
nginx -t

# Перезагрузите Nginx
systemctl reload nginx
```

### 4. Проверьте работу

```bash
# Проверка API через Nginx
curl http://localhost/api/health

# Проверка главной страницы
curl http://localhost/ | head -20

# Проверка статуса
systemctl status daribri
systemctl status nginx
```

### 5. Проверка портов

```bash
# Проверьте, что порты слушаются
ss -tulpn | grep -E ':(80|8000)'
```

### 6. Проверка логов

```bash
# Логи Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/daribri_error.log

# Логи приложения
journalctl -u daribri -f
```

## Если сайт все еще не работает

### Проверьте файрвол

```bash
# Проверьте статус
ufw status

# Если нужно, откройте порты
ufw allow 80/tcp
ufw allow 443/tcp
```

### Проверьте DNS

```bash
# Проверьте, что домен указывает на сервер
nslookup flow.plus-shop.ru
dig flow.plus-shop.ru
```

### Полная диагностика

```bash
# 1. API работает?
curl http://localhost:8000/api/health && echo "✅ API работает" || echo "❌ API не работает"

# 2. Nginx работает?
systemctl is-active nginx && echo "✅ Nginx работает" || echo "❌ Nginx не работает"

# 3. Сервис работает?
systemctl is-active daribri && echo "✅ Сервис работает" || echo "❌ Сервис не работает"

# 4. Порты открыты?
ss -tulpn | grep -E ':(80|8000)' && echo "✅ Порты открыты" || echo "❌ Порты не открыты"

# 5. Конфигурация активна?
ls -la /etc/nginx/sites-enabled/ | grep daribri && echo "✅ Конфигурация активна" || echo "❌ Конфигурация не активна"
```

## Готово! 🎉

После выполнения этих шагов сайт должен работать:
- `http://flow.plus-shop.ru` - главная страница
- `http://flow.plus-shop.ru/api/health` - проверка API



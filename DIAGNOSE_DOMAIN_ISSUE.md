# Диагностика проблемы с доменом daribri.ru (IP: 147.45.100.252)

## Быстрая диагностика

Выполните эти команды на сервере:

```bash
# 1. Проверьте, что DNS указывает на правильный IP
echo "=== Проверка DNS ==="
dig daribri.ru A +short
dig www.daribri.ru A +short
echo "Ожидается: 147.45.100.252"
echo ""

# 2. Проверьте IP сервера
echo "=== IP адрес сервера ==="
hostname -I
ip addr show | grep "inet " | grep -v 127.0.0.1
echo ""

# 3. Проверьте, что порт 80 слушается
echo "=== Порт 80 ==="
sudo netstat -tulpn | grep :80
sudo ss -tulpn | grep :80
echo ""

# 4. Проверьте статус Nginx
echo "=== Статус Nginx ==="
sudo systemctl status nginx --no-pager | head -n 10
echo ""

# 5. Проверьте статус приложения
echo "=== Статус приложения ==="
sudo systemctl status daribri --no-pager | head -n 10
echo ""

# 6. Проверьте firewall
echo "=== Firewall ==="
sudo ufw status
echo ""

# 7. Проверьте доступность локально
echo "=== Локальная доступность ==="
curl -I http://localhost:8000 2>&1 | head -n 1
curl -I http://127.0.0.1:8000 2>&1 | head -n 1
echo ""

# 8. Проверьте конфигурацию Nginx
echo "=== Конфигурация Nginx ==="
sudo nginx -t
echo ""

# 9. Проверьте логи Nginx
echo "=== Последние ошибки Nginx ==="
sudo tail -n 20 /var/log/nginx/error.log
echo ""
```

---

## Решение проблем

### Проблема 1: DNS не указывает на 147.45.100.252

**Решение:**
1. Зайдите в панель управления доменом у регистратора
2. Убедитесь, что A записи указывают на `147.45.100.252`:
   - `daribri.ru` → `147.45.100.252`
   - `www.daribri.ru` → `147.45.100.252`
3. Подождите 5-30 минут для распространения DNS
4. Проверьте через: https://dnschecker.org/#A/daribri.ru

### Проблема 2: Порт 80 не слушается

**Решение:**
```bash
# Запустите Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Проверьте статус
sudo systemctl status nginx
```

### Проблема 3: Firewall блокирует порт 80

**Решение:**
```bash
# Откройте порты
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# Проверьте статус
sudo ufw status
```

### Проблема 4: Приложение не работает на порту 8000

**Решение:**
```bash
# Проверьте статус
sudo systemctl status daribri

# Если не работает, запустите
sudo systemctl start daribri
sudo systemctl enable daribri

# Проверьте логи
sudo journalctl -u daribri -n 50 --no-pager
```

### Проблема 5: Nginx не проксирует на приложение

**Решение:**
```bash
# Проверьте конфигурацию
sudo nano /etc/nginx/sites-available/daribri
```

**Убедитесь, что конфигурация правильная:**

```nginx
server {
    listen 80;
    server_name daribri.ru www.daribri.ru;

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

```bash
# Проверьте синтаксис
sudo nginx -t

# Перезагрузите Nginx
sudo systemctl reload nginx
```

---

## Проверка доступности с внешних сервисов

Проверьте доступность домена:

1. **С вашего компьютера:**
   ```bash
   curl -I http://daribri.ru
   curl -I http://147.45.100.252
   ```

2. **Через браузер:**
   - Откройте: `http://daribri.ru`
   - Откройте: `http://147.45.100.252`

3. **Через онлайн сервисы:**
   - https://downforeveryoneorjustme.com/daribri.ru
   - https://www.isitdownrightnow.com/daribri.ru.html

---

## Полная проверка конфигурации

```bash
# 1. Проверьте, что все сервисы запущены
sudo systemctl status nginx
sudo systemctl status daribri

# 2. Проверьте конфигурацию Nginx
sudo nginx -t
cat /etc/nginx/sites-available/daribri | grep server_name

# 3. Проверьте, что порты слушаются
sudo netstat -tulpn | grep -E ":(80|8000)"

# 4. Проверьте логи
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/daribri_error.log
sudo journalctl -u daribri -f
```

---

## Быстрое исправление (если всё сломано)

```bash
# 1. Остановите всё
sudo systemctl stop nginx
sudo systemctl stop daribri

# 2. Проверьте конфигурацию Nginx
sudo nano /etc/nginx/sites-available/daribri
# Убедитесь, что server_name правильный: daribri.ru www.daribri.ru

# 3. Проверьте синтаксис
sudo nginx -t

# 4. Запустите приложение
sudo systemctl start daribri
sudo systemctl status daribri

# 5. Запустите Nginx
sudo systemctl start nginx
sudo systemctl status nginx

# 6. Проверьте доступность
curl http://localhost:8000
curl http://localhost
```

---

## После исправления: получение SSL сертификата

После того, как HTTP заработает:

```bash
# 1. Убедитесь, что домен доступен
curl -I http://daribri.ru
# Должен вернуть HTTP ответ

# 2. Добавьте location для acme-challenge в Nginx
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

# 5. Получите сертификат
sudo certbot --nginx -d daribri.ru -d www.daribri.ru
```

---

## Частые ошибки и решения

### Ошибка: "502 Bad Gateway"

**Причина:** Приложение не работает на порту 8000

**Решение:**
```bash
sudo systemctl restart daribri
sudo journalctl -u daribri -n 50
```

### Ошибка: "Connection refused"

**Причина:** Порт закрыт или сервис не запущен

**Решение:**
```bash
sudo ufw allow 80/tcp
sudo systemctl start nginx
sudo systemctl start daribri
```

### Ошибка: "This site can't be reached"

**Причина:** DNS не указывает на правильный IP или порт закрыт

**Решение:**
1. Проверьте DNS: `dig daribri.ru A +short`
2. Должно вернуть: `147.45.100.252`
3. Если нет, обновите DNS записи

---

## Готово! ✅

После исправления всех проблем домен должен работать по HTTP, и вы сможете получить SSL сертификат.


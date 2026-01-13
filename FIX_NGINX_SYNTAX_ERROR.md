# Исправление ошибки Nginx: "location" directive is not allowed here

## Проблема

Ошибка:
```
nginx: [emerg] "location" directive is not allowed here in /etc/nginx/sites-enabled/daribri:25
```

Это означает, что директива `location` находится не внутри блока `server`.

## Решение

### Шаг 1: Проверьте конфигурацию

```bash
# Посмотрите конфигурацию
sudo cat /etc/nginx/sites-available/daribri
```

### Шаг 2: Исправьте конфигурацию

```bash
# Откройте конфигурацию
sudo nano /etc/nginx/sites-available/daribri
```

**Убедитесь, что конфигурация выглядит правильно:**

```nginx
server {
    listen 80;
    server_name flow.plus-shop.ru www.flow.plus-shop.ru;

    # Максимальный размер загружаемых файлов
    client_max_body_size 50M;

    # Location для acme-challenge (для Certbot)
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

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

**ВАЖНО:** 
- Все `location` директивы должны быть **внутри** блока `server { ... }`
- Блок `server` должен начинаться с `server {` и заканчиваться `}`
- Не должно быть лишних закрывающих или открывающих скобок

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

### Шаг 3: Проверьте синтаксис

```bash
# Проверьте синтаксис
sudo nginx -t
```

Если всё ОК, вы увидите:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### Шаг 4: Перезагрузите Nginx

```bash
# Перезагрузите Nginx
sudo systemctl reload nginx

# Проверьте статус
sudo systemctl status nginx
```

### Шаг 5: Проверьте работу

```bash
# Проверьте доступность
curl http://flow.plus-shop.ru
curl http://localhost

# Должны вернуть содержимое приложения
```

---

## Частые ошибки в конфигурации

### Ошибка 1: Лишние закрывающие скобки

**Неправильно:**
```nginx
server {
    location / {
        ...
    }
}  # Лишняя закрывающая скобка
}
```

**Правильно:**
```nginx
server {
    location / {
        ...
    }
}
```

### Ошибка 2: location вне блока server

**Неправильно:**
```nginx
server {
    ...
}

location / {  # ОШИБКА: location вне server блока
    ...
}
```

**Правильно:**
```nginx
server {
    location / {
        ...
    }
}
```

### Ошибка 3: Неправильная структура

**Неправильно:**
```nginx
server {
    listen 80;
location / {  # ОШИБКА: нет server_name перед location
    ...
}
```

**Правильно:**
```nginx
server {
    listen 80;
    server_name flow.plus-shop.ru;
    
    location / {
        ...
    }
}
```

---

## Быстрое исправление (полная правильная конфигурация)

Если не уверены, скопируйте эту конфигурацию полностью:

```bash
# Создайте резервную копию
sudo cp /etc/nginx/sites-available/daribri /etc/nginx/sites-available/daribri.backup

# Создайте правильную конфигурацию
sudo nano /etc/nginx/sites-available/daribri
```

**Вставьте полностью:**

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

**Сохраните:** `Ctrl+O`, `Enter`, `Ctrl+X`

```bash
# Проверьте и перезагрузите
sudo nginx -t
sudo systemctl reload nginx
```

---

## После исправления: получение SSL сертификата

После того, как конфигурация исправлена и Nginx работает:

```bash
# Получите SSL сертификат
sudo certbot --nginx -d flow.plus-shop.ru -d www.flow.plus-shop.ru
```

Certbot автоматически обновит конфигурацию для HTTPS.

---

## Готово! ✅

После исправления синтаксиса Nginx должен работать корректно.


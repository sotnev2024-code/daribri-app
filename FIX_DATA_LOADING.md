# Исправление проблемы: данные не загружаются на сайте

## Диагностика проблемы

Если сайт открывается, но данные (категории, товары) не загружаются, выполните следующие шаги:

### 1. Проверка данных в базе на сервере

Подключитесь к серверу и выполните диагностический скрипт:

```bash
cd /var/www/daribri
source venv/bin/activate
python database/check_data.py
```

Скрипт покажет:
- Сколько категорий, магазинов, товаров и подписок в базе
- Есть ли активные подписки
- Сколько товаров видно на сайте (только товары магазинов с активной подпиской)

### 2. Возможные проблемы и решения

#### Проблема 1: Нет активных подписок

**Симптомы:**
- Категории загружаются
- Товары НЕ загружаются (каталог пустой)
- В логах скрипта: "Нет активных подписок"

**Решение:**

1. Создайте активную подписку для магазина:

```bash
cd /var/www/daribri
source venv/bin/activate
python database/set_infinite_subscription.py --shop-id 1
```

Или через SQL:

```bash
sqlite3 database/miniapp.db
```

```sql
-- Проверьте ID магазина
SELECT id, name FROM shops;

-- Проверьте ID плана подписки
SELECT id, name FROM subscription_plans;

-- Деактивируйте старые подписки
UPDATE shop_subscriptions SET is_active = 0 WHERE shop_id = 1;

-- Создайте новую активную подписку
INSERT INTO shop_subscriptions (shop_id, plan_id, start_date, end_date, is_active, payment_id)
VALUES (
    1,  -- ID магазина
    (SELECT id FROM subscription_plans LIMIT 1),  -- ID плана
    datetime('now'),
    '2099-12-31 23:59:59',  -- "Бесконечная" подписка
    1,
    'admin_setup'
);
```

#### Проблема 2: Нет категорий

**Симптомы:**
- Категории не загружаются
- В логах скрипта: "Нет категорий"

**Решение:**

Переинициализируйте базу данных:

```bash
cd /var/www/daribri
source venv/bin/activate
python database/init_db.py
```

#### Проблема 3: Нет товаров

**Симптомы:**
- Категории загружаются
- Товары НЕ загружаются
- В логах скрипта: "Нет видимых товаров"

**Решение:**

1. Проверьте, есть ли товары в базе:
```bash
sqlite3 database/miniapp.db "SELECT COUNT(*) FROM products WHERE is_active = 1;"
```

2. Если товары есть, но не отображаются, проверьте подписки (см. Проблема 1)

3. Если товаров нет, добавьте их через админ-панель или API

#### Проблема 4: Проблемы с API

**Симптомы:**
- В консоли браузера (F12) видны ошибки 404, 500 или CORS
- API не отвечает

**Решение:**

1. Проверьте, запущен ли сервис:
```bash
systemctl status daribri
```

2. Проверьте логи приложения:
```bash
journalctl -u daribri -n 50 --no-pager
```

3. Проверьте, отвечает ли API локально:
```bash
curl http://127.0.0.1:8000/api/health
```

4. Проверьте логи Nginx:
```bash
tail -f /var/log/nginx/daribri_error.log
```

### 3. Проверка в браузере

Откройте консоль браузера (F12) и проверьте:

1. **Ошибки в консоли:**
   - Откройте вкладку "Console"
   - Ищите ошибки красного цвета
   - Обратите внимание на ошибки типа `Failed to fetch`, `404`, `500`

2. **Сетевые запросы:**
   - Откройте вкладку "Network"
   - Обновите страницу
   - Проверьте запросы к `/api/categories` и `/api/products`
   - Посмотрите статус ответов (должно быть 200)

3. **API URL:**
   - В консоли должно быть: `API baseUrl: https://flow.plus-shop.ru` (или ваш домен)
   - Если видите `http://localhost:8080`, значит проблема в определении URL

### 4. Быстрое исправление (если нет подписок)

Если проблема в отсутствии активных подписок, выполните:

```bash
cd /var/www/daribri
source venv/bin/activate

# Создайте подписку для всех магазинов
sqlite3 database/miniapp.db <<EOF
-- Деактивируем все старые подписки
UPDATE shop_subscriptions SET is_active = 0;

-- Создаем активные подписки для всех активных магазинов
INSERT INTO shop_subscriptions (shop_id, plan_id, start_date, end_date, is_active, payment_id)
SELECT 
    s.id,
    (SELECT id FROM subscription_plans LIMIT 1),
    datetime('now'),
    '2099-12-31 23:59:59',
    1,
    'admin_setup'
FROM shops s
WHERE s.is_active = 1
AND NOT EXISTS (
    SELECT 1 FROM shop_subscriptions ss 
    WHERE ss.shop_id = s.id 
    AND ss.is_active = 1 
    AND ss.end_date > datetime('now')
);
EOF

# Проверьте результат
python database/check_data.py
```

### 5. Проверка после исправления

1. Обновите страницу в браузере (Ctrl+F5 для полной перезагрузки)
2. Откройте консоль (F12) и проверьте, что данные загружаются
3. Проверьте, что категории и товары отображаются

## Частые вопросы

**Q: Почему товары не отображаются, хотя они есть в базе?**
A: Товары показываются только для магазинов с активной подпиской. Проверьте подписки командой `python database/check_data.py`.

**Q: Как проверить, работает ли API?**
A: Выполните `curl http://127.0.0.1:8000/api/health` на сервере. Должен вернуться `{"status":"healthy"}`.

**Q: В консоли браузера ошибка CORS. Что делать?**
A: Проверьте настройки CORS в `backend/app/config.py`. Должно быть `CORS_ORIGINS: list = ["*"]` или список ваших доменов.

**Q: API отвечает, но возвращает пустые массивы.**
A: Скорее всего, проблема в отсутствии активных подписок. Выполните диагностику `python database/check_data.py`.




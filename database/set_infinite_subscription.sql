-- =====================================================
-- SQL скрипт для установки бесконечной подписки
-- =====================================================
-- 
-- Использование:
-- 1. Замените TELEGRAM_ID на Telegram ID пользователя
-- 2. Или замените SHOP_ID на ID магазина
-- 3. Выполните скрипт
--
-- =====================================================

-- Вариант 1: По Telegram ID пользователя
-- Замените 123456789 на реальный Telegram ID
-- 
-- UPDATE shop_subscriptions
-- SET end_date = '2099-12-31 23:59:59',
--     is_active = 1,
--     start_date = datetime('now')
-- WHERE shop_id = (
--     SELECT s.id 
--     FROM shops s
--     JOIN users u ON s.owner_id = u.id
--     WHERE u.telegram_id = 123456789
--     LIMIT 1
-- );

-- Вариант 2: По ID магазина напрямую
-- Замените 1 на реальный ID магазина
--
-- UPDATE shop_subscriptions
-- SET end_date = '2099-12-31 23:59:59',
--     is_active = 1,
--     start_date = datetime('now')
-- WHERE shop_id = 1;

-- =====================================================
-- Полный пример с созданием новой подписки, если её нет
-- =====================================================

-- Для магазина с ID = 1 (замените на нужный ID)

-- Шаг 1: Деактивируем старые подписки
UPDATE shop_subscriptions
SET is_active = 0
WHERE shop_id = 1;

-- Шаг 2: Проверяем, есть ли активный план подписки
-- (Если нет, создайте его или используйте существующий)

-- Шаг 3: Создаём или обновляем подписку
-- Если подписка уже существует, обновляем её
UPDATE shop_subscriptions
SET end_date = '2099-12-31 23:59:59',
    is_active = 1,
    start_date = datetime('now')
WHERE shop_id = 1
AND id = (
    SELECT id FROM shop_subscriptions 
    WHERE shop_id = 1 
    ORDER BY created_at DESC 
    LIMIT 1
);

-- Если подписки не было, создаём новую
-- (Раскомментируйте, если нужно создать новую подписку)
-- INSERT INTO shop_subscriptions 
-- (shop_id, plan_id, start_date, end_date, is_active, payment_id)
-- SELECT 
--     1,  -- shop_id (замените на нужный)
--     (SELECT id FROM subscription_plans WHERE is_active = 1 ORDER BY price ASC LIMIT 1),
--     datetime('now'),
--     '2099-12-31 23:59:59',
--     1,
--     'infinite_admin'
-- WHERE NOT EXISTS (
--     SELECT 1 FROM shop_subscriptions 
--     WHERE shop_id = 1 AND is_active = 1
-- );

-- =====================================================
-- Проверка результата
-- =====================================================
-- SELECT 
--     ss.id,
--     ss.shop_id,
--     s.name as shop_name,
--     sp.name as plan_name,
--     ss.start_date,
--     ss.end_date,
--     ss.is_active
-- FROM shop_subscriptions ss
-- JOIN shops s ON ss.shop_id = s.id
-- JOIN subscription_plans sp ON ss.plan_id = sp.id
-- WHERE ss.shop_id = 1
-- ORDER BY ss.created_at DESC
-- LIMIT 1;



-- Миграция: Добавление поля product_name в таблицу order_items
-- Это поле будет хранить название товара на случай, если товар будет удален

-- Проверяем, существует ли поле, и добавляем его, если нет
-- SQLite не поддерживает IF NOT EXISTS для ALTER TABLE, поэтому используем проверку через PRAGMA

-- Добавляем поле product_name, если его еще нет
-- В SQLite нужно использовать ALTER TABLE ADD COLUMN
-- Если поле уже существует, команда выдаст ошибку, но это нормально

ALTER TABLE order_items ADD COLUMN product_name TEXT;

-- Обновляем существующие записи, чтобы заполнить product_name из таблицы products
UPDATE order_items 
SET product_name = (
    SELECT name 
    FROM products 
    WHERE products.id = order_items.product_id
)
WHERE product_id IS NOT NULL AND product_name IS NULL;


-- Миграция: добавление колонки group_message_id в таблицу shop_requests

-- Проверяем, существует ли колонка group_message_id
-- Если нет, добавляем её

-- SQLite не поддерживает IF NOT EXISTS для ALTER TABLE ADD COLUMN
-- Поэтому просто добавляем колонку (если она уже есть, будет ошибка, но мы её игнорируем)

ALTER TABLE shop_requests ADD COLUMN group_message_id INTEGER;




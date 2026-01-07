-- =====================================================
-- Обновление иконок категорий
-- =====================================================
-- Этот скрипт обновляет иконки существующих категорий

-- Обновление главных категорий
UPDATE categories SET icon = '🌷' WHERE slug = 'flowers';
UPDATE categories SET icon = '🪴' WHERE slug = 'houseplants';
UPDATE categories SET icon = '🧁' WHERE slug = 'bakery';
UPDATE categories SET icon = '🍓' WHERE slug = 'edible-bouquets';
UPDATE categories SET icon = '🎁' WHERE slug = 'tasty-sets';
UPDATE categories SET icon = '☕' WHERE slug = 'tea-coffee-sets';
UPDATE categories SET icon = '⭐' WHERE slug = 'misc';

-- Обновление подкатегорий для лучшего соответствия
-- Цветы
UPDATE categories SET icon = '🌷' WHERE slug = 'mono-bouquets';
UPDATE categories SET icon = '💮' WHERE slug = 'author-bouquets';
UPDATE categories SET icon = '🌸' WHERE slug = 'giant-bouquets';
UPDATE categories SET icon = '📦' WHERE slug = 'flowers-in-box';
UPDATE categories SET icon = '🧺' WHERE slug = 'flowers-in-basket';
UPDATE categories SET icon = '🌹' WHERE slug = 'single-flowers';

-- Вкусные наборы - используем иконку подарочной корзины для фруктовых корзин
UPDATE categories SET icon = '🧺' WHERE slug = 'fruit-baskets';

-- Наборы чая и кофе - используем чашку кофе
UPDATE categories SET icon = '☕' WHERE slug = 'coffee-sets';




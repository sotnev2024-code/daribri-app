# Модульная структура приложения

Файл `app.js` был разделен на модули для улучшения организации кода.

## Созданные модули

### 1. `modules/state.js`
- Глобальное состояние приложения (`state`)
- DOM элементы (`elements`)
- Инициализация элементов (`initElements`)

### 2. `modules/utils.js`
- Утилиты: `formatPrice`, `formatDate`, `showToast`, `showLoading`
- Обновление badge: `updateCartBadge`, `updateFavoritesBadge`
- Вспомогательные функции: `debounce`, `getMediaUrl`, `getOrderStatusText`

### 3. `modules/catalog.js`
- Загрузка данных: `loadCategories`, `loadProducts`
- Рендеринг: `renderCategories`, `renderProducts`, `renderSubcategories`
- Фильтры: `applyClientFilters`, `openFilterModal`, `closeFilterModal`, `applyFilters`, `resetFilters`
- Категории: `selectCategory`, `findCategory`, `getCategoryIconFileName`
- Карточки товаров: `createProductCard`, `initProductCardSlider`

### 4. `modules/cart.js`
- Загрузка: `loadCart`
- Рендеринг: `renderCart`, `updateCartSummary`
- Операции: `updateCartQuantity`, `removeFromCart`, `clearCart`

### 5. `modules/favorites.js`
- Загрузка: `loadFavorites`, `renderFavorites`
- Операции: `toggleFavorite`, `isProductFavorite`, `updateFavoriteButtons`

### 6. `modules/product.js`
- Страница товара: `openProductPage`, `closeProductPage`
- Галерея: `initGalleryNavigation`, `changeGallerySlide`, `goToGallerySlide`
- Товары продавца: `loadSellerProducts`
- Корзина: `updateQuantity`, `addToCart`

### 7. `modules/navigation.js`
- Навигация: `navigateTo`
- Поиск: `openSearch`, `closeSearch`, `handleSearch`

### 8. `modules/shop.js`
- Страница магазина: `openShopPage`, `loadShopData`
- Карта: `loadShopMap`
- Отзывы: `loadShopReviews`
- Товары: `loadShopProducts`

### 9. `modules/checkout.js`
- Заглушка для будущего модуля оформления заказа
- Экспортирует константу `DELIVERY_FEE`

### 10. `modules/myshop.js`
- Заглушка для будущего модуля "Мой магазин"
- Основная логика пока остается в `app.js`

## Использование модулей

Все модули экспортируют функции в два места:
1. `window.App.{moduleName}` - для доступа через объект App
2. Глобальный `window` - для обратной совместимости

Пример:
```javascript
// Через App объект
window.App.catalog.loadCategories();

// Через глобальные функции (обратная совместимость)
loadCategories();
```

## Что еще нужно сделать

1. **checkout.js** - перенести функции оформления заказа (очень большой, ~1500 строк)
2. **myshop.js** - перенести функции моего магазина (очень большой, ~3000+ строк)
3. Удалить дублирующиеся функции из `app.js` после полного переноса
4. Добавить комментарии с указанием, какие функции были вынесены

## Структура модулей

Каждый модуль использует паттерн IIFE (Immediately Invoked Function Expression):
```javascript
(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    const getApi = () => window.api;
    
    // Функции модуля
    
    window.App = window.App || {};
    window.App.{moduleName} = {
        // Экспорт функций
    };
    
    // Глобальный экспорт для обратной совместимости
    window.{functionName} = {functionName};
})();
```

## Примечания

- Модули загружаются в определенном порядке (см. `index.html`)
- Все модули доступны через `window.App` после загрузки
- Для обратной совместимости функции также экспортируются в глобальный `window`
- Большие модули (checkout, myshop) пока остаются в `app.js`, но структура готова для постепенного переноса




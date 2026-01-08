/**
 * Profile Module - профиль пользователя
 * Этот модуль предоставляет дополнительные функции профиля
 * Основной loadProfile находится в main.js
 */

// Функции для кнопок профиля (заглушки для будущего функционала)
function openMyShop() { 
    // Функционал реализован в myshop.js
    console.log('[PROFILE] openMyShop called');
}

function openAddProduct() { 
    // Функционал реализован в myshop.js
    console.log('[PROFILE] openAddProduct called');
}

function openSubscription() { 
    // Функционал реализован в subscription.js
    console.log('[PROFILE] openSubscription called');
}

// Expose to window
window.openMyShop = openMyShop;
window.openAddProduct = openAddProduct;
window.openSubscription = openSubscription;

console.log('[PROFILE] Profile module loaded');

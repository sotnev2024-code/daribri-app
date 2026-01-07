/**
 * Utils Module - утилиты и вспомогательные функции
 */

(function() {
    'use strict';
    
    // Получаем ссылки на state и elements из глобального объекта App
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getApi = () => window.api;

    function getMediaUrl(url) {
        if (!url) return '';
        
        // Если это blob URL, возвращаем как есть
        if (url.startsWith('blob:')) {
            return url;
        }
        
        // Если URL уже полный (начинается с http:// или https://), возвращаем как есть
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }
        
        // Если это base64 data URL, возвращаем как есть
        if (url.startsWith('data:')) {
            return url;
        }
        
        const api = getApi();
        if (!api) return url;
        
        // Если относительный URL (начинается с /), добавляем baseUrl API
        if (url.startsWith('/')) {
            return api.baseUrl + url;
        }
        
        // Для остальных случаев добавляем baseUrl и слэш
        return api.baseUrl + '/' + url;
    }

    function formatPrice(price) {
        return new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
        }).format(price);
    }

    function formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
        });
    }

    function getOrderStatusText(status) {
        const statuses = {
            pending: 'Ожидает',
            confirmed: 'Подтверждён',
            processing: 'В обработке',
            shipped: 'Доставляется',
            delivered: 'Доставлен',
            cancelled: 'Отменён',
        };
        return statuses[status] || status;
    }

    function updateCartBadge() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements?.cartBadge) return;
        
        const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);
        elements.cartBadge.textContent = count;
        elements.cartBadge.hidden = count === 0;
        if (elements.cartNavBadge) {
            elements.cartNavBadge.textContent = count;
            elements.cartNavBadge.hidden = count === 0;
        }
    }

    function updateFavoritesBadge() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements?.favoritesBadge) return;
        
        const count = state.favorites.length;
        elements.favoritesBadge.textContent = count;
        elements.favoritesBadge.hidden = count === 0;
    }

    function showLoading(show) {
        const elements = getElements();
        if (!elements) return;
        
        if (elements.loadingIndicator) {
            elements.loadingIndicator.hidden = !show;
        }
        if (elements.productsGrid) {
            elements.productsGrid.style.display = show ? 'none' : '';
        }
    }

    function showToast(message, type = 'info') {
        const elements = getElements();
        if (!elements?.toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        elements.toastContainer.appendChild(toast);
        
        setTimeout(() => toast.remove(), 3000);
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function formatOrderDate(dateString) {
        if (!dateString) return 'Не указана';
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
    }

    function formatDeliveryDate(dateString) {
        if (!dateString) return 'Не указана';
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
    }

    function pluralize(count, one, few, many) {
        const mod10 = count % 10;
        const mod100 = count % 100;
        
        if (mod100 >= 11 && mod100 <= 19) {
            return many;
        }
        if (mod10 === 1) {
            return one;
        }
        if (mod10 >= 2 && mod10 <= 4) {
            return few;
        }
        return many;
    }

    // Экспортируем функции
    window.App = window.App || {};
    window.App.utils = {
        getMediaUrl,
        formatPrice,
        formatDate,
        getOrderStatusText,
        updateCartBadge,
        updateFavoritesBadge,
        showLoading,
        showToast,
        debounce,
        formatOrderDate,
        formatDeliveryDate,
        pluralize
    };

    // Также экспортируем как глобальные функции для обратной совместимости
    window.getMediaUrl = getMediaUrl;
    window.formatPrice = formatPrice;
    window.formatDate = formatDate;
    window.getOrderStatusText = getOrderStatusText;
    window.updateCartBadge = updateCartBadge;
    window.updateFavoritesBadge = updateFavoritesBadge;
    window.showLoading = showLoading;
    window.showToast = showToast;
    window.debounce = debounce;
    window.formatOrderDate = formatOrderDate;
    window.formatDeliveryDate = formatDeliveryDate;
    window.pluralize = pluralize;
})();



/**
 * Cart Module - корзина
 */

(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    const getApi = () => window.api;
    
    // Загрузка корзины
    async function loadCart() {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        try {
            state.cart = await api.getCart();
            if (utils.updateCartBadge) utils.updateCartBadge();
        } catch (error) {
            console.error('Error loading cart:', error);
            state.cart = [];
        }
    }
    
    // Рендеринг корзины
    function renderCart() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        if (!state || !elements) return;
        
        if (state.cart.length === 0) {
            elements.cartItems.innerHTML = '';
            elements.cartEmpty.hidden = false;
            elements.cartSummary.hidden = true;
            return;
        }
        
        elements.cartEmpty.hidden = true;
        elements.cartSummary.hidden = false;
        
        const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
        
        elements.cartItems.innerHTML = state.cart.map(item => `
            <div class="cart-item" data-item-id="${item.id}">
                <div class="cart-item-image">
                    ${item.product_image_url 
                        ? `<img src="${item.product_image_url}" alt="${item.product_name}">`
                        : '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:2rem;">🌸</div>'
                    }
                </div>
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.product_name}</div>
                    <div class="cart-item-shop">${item.shop_name}</div>
                    <div class="cart-item-bottom">
                        <span class="cart-item-price">${formatPrice(item.product_discount_price || item.product_price)}</span>
                        <div class="cart-item-qty">
                            <button onclick="window.updateCartQuantity(${item.id}, ${item.quantity - 1})">−</button>
                            <span>${item.quantity}</span>
                            <button onclick="window.updateCartQuantity(${item.id}, ${item.quantity + 1})">+</button>
                            <button class="cart-item-delete" onclick="window.removeFromCart(${item.id})">✕</button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        updateCartSummary();
    }
    
    // Обновление итогов корзины
    function updateCartSummary() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        if (!state || !elements) return;
        
        const items = state.cart;
        const count = items.reduce((sum, item) => sum + item.quantity, 0);
        const subtotal = items.reduce((sum, item) => {
            return sum + (parseFloat(item.product_price) * item.quantity);
        }, 0);
        const total = items.reduce((sum, item) => {
            const price = item.product_discount_price || item.product_price;
            return sum + (parseFloat(price) * item.quantity);
        }, 0);
        const discount = subtotal - total;
        
        const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
        
        elements.summaryCount.textContent = count;
        elements.summarySubtotal.textContent = formatPrice(subtotal);
        elements.summaryTotal.textContent = formatPrice(total);
        
        if (discount > 0) {
            elements.summaryDiscountRow.hidden = false;
            elements.summaryDiscount.textContent = `-${formatPrice(discount)}`;
        } else {
            elements.summaryDiscountRow.hidden = true;
        }
    }
    
    // Обновление количества товара в корзине
    async function updateCartQuantity(itemId, quantity) {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        if (quantity < 1) {
            removeFromCart(itemId);
            return;
        }
        
        try {
            await api.updateCartItem(itemId, { quantity });
            await loadCart();
            renderCart();
        } catch (error) {
            console.error('Error updating cart quantity:', error);
            if (utils.showToast) utils.showToast('Ошибка обновления корзины', 'error');
        }
    }
    
    // Удаление товара из корзины
    async function removeFromCart(itemId) {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        try {
            await api.removeFromCart(itemId);
            await loadCart();
            renderCart();
            if (utils.showToast) utils.showToast('Товар удалён из корзины', 'success');
        } catch (error) {
            console.error('Error removing from cart:', error);
            if (utils.showToast) utils.showToast('Ошибка удаления товара', 'error');
        }
    }
    
    // Очистка корзины
    async function clearCart() {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        if (!confirm('Очистить всю корзину?')) return;
        
        try {
            await api.clearCart();
            await loadCart();
            renderCart();
            if (utils.showToast) utils.showToast('Корзина очищена', 'success');
        } catch (error) {
            console.error('Error clearing cart:', error);
            if (utils.showToast) utils.showToast('Ошибка очистки корзины', 'error');
        }
    }
    
    // Обновление количества на странице товара
    function updateQuantity(delta) {
        const elements = getElements();
        if (!elements?.qtyValue) return;
        const current = parseInt(elements.qtyValue.textContent) || 1;
        const newQty = Math.max(1, current + delta);
        elements.qtyValue.textContent = newQty;
    }
    
    // Добавление товара в корзину
    async function addToCart() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        const api = getApi();
        if (!state || !elements || !api) return;
        
        if (!state.currentProduct) return;
        const quantity = parseInt(elements.qtyValue.textContent) || 1;
        const currentProduct = state.currentProduct;
        
        // Проверяем, есть ли в корзине товары из другого магазина
        if (state.cart && state.cart.length > 0) {
            const cartShopId = state.cart[0].shop_id;
            const newProductShopId = currentProduct.shop_id;
            
            if (cartShopId && newProductShopId && cartShopId !== newProductShopId) {
                // Показываем предупреждение
                const confirmed = await showDifferentShopWarning(currentProduct, quantity);
                if (!confirmed) return;
            }
        }
        
        try {
            await api.addToCart(currentProduct.id, quantity);
            if (utils.showToast) utils.showToast('Товар добавлен в корзину', 'success');
            await loadCart();
            
            // Обновляем UI кнопок
            updateProductPageCartUI(currentProduct.id);
        } catch (error) {
            console.error('Error adding to cart:', error);
            if (utils.showToast) utils.showToast('Ошибка добавления в корзину', 'error');
        }
    }
    
    // Обновляет UI кнопок корзины на странице товара
    function updateProductPageCartUI(productId) {
        const state = getState();
        const elements = getElements();
        
        if (!state || !elements) return;
        
        const cartItem = state.cart.find(item => item.product_id === productId);
        
        if (cartItem) {
            // Товар в корзине - показываем кнопки +/- и "Перейти в корзину"
            if (elements.addToCartBtn) elements.addToCartBtn.hidden = true;
            if (elements.inCartControls) elements.inCartControls.hidden = false;
            if (elements.cartQtyValue) elements.cartQtyValue.textContent = cartItem.quantity;
        } else {
            // Товара нет в корзине - показываем кнопку "Добавить"
            if (elements.addToCartBtn) elements.addToCartBtn.hidden = false;
            if (elements.inCartControls) elements.inCartControls.hidden = true;
        }
    }
    
    // Обновляет количество товара на странице товара
    async function updateProductCartQuantity(delta) {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        const utils = getUtils();
        if (!state || !elements || !api || !state.currentProduct) return;
        
        const productId = state.currentProduct.id;
        const currentProduct = state.currentProduct;
        const cartItem = state.cart.find(item => item.product_id === productId);
        
        if (!cartItem) return;
        
        const newQuantity = cartItem.quantity + delta;
        
        // Проверка на максимальное количество (наличие)
        if (delta > 0 && currentProduct.quantity && newQuantity > currentProduct.quantity) {
            if (utils.showToast) {
                utils.showToast(`Нельзя добавить больше ${currentProduct.quantity} шт. (столько в наличии)`, 'warning');
            }
            return;
        }
        
        if (newQuantity < 1) {
            // Удаляем товар из корзины
            try {
                await api.removeFromCart(cartItem.id);
                await loadCart();
                updateProductPageCartUI(productId);
                if (utils.showToast) utils.showToast('Товар удалён из корзины', 'success');
            } catch (error) {
                console.error('Error removing from cart:', error);
            }
        } else {
            // Обновляем количество
            try {
                await api.updateCartItem(cartItem.id, newQuantity);
                await loadCart();
                updateProductPageCartUI(productId);
            } catch (error) {
                console.error('Error updating cart:', error);
                if (utils.showToast) utils.showToast('Ошибка обновления корзины', 'error');
            }
        }
    }
    
    // Показывает предупреждение о товарах из разных магазинов
    async function showDifferentShopWarning(newProduct, quantity) {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        return new Promise((resolve) => {
            // Создаём модальное окно
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.id = 'differentShopModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 400px; background: var(--bg-secondary, #fff); border-radius: 16px; margin: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
                    <div class="modal-header" style="padding: 20px 20px 10px; text-align: center;">
                        <h2 style="margin: 0; font-size: 18px;">⚠️ Разные магазины</h2>
                    </div>
                    <div class="modal-body" style="padding: 10px 20px 20px; text-align: center;">
                        <p style="margin-bottom: 15px;">В корзине уже есть товары из другого магазина.</p>
                        <p style="color: var(--text-secondary); font-size: 14px; margin: 0;">Вы можете оформить заказ только из одного магазина за раз.</p>
                    </div>
                    <div class="modal-footer" style="display: flex; gap: 10px; padding: 15px 20px 20px;">
                        <button class="btn btn-secondary" id="cancelDifferentShop" style="flex: 1; padding: 12px; border-radius: 12px; border: none; background: var(--bg-tertiary, #f0f0f0); cursor: pointer;">Отмена</button>
                        <button class="btn btn-primary" id="clearCartAndAdd" style="flex: 1; padding: 12px; border-radius: 12px; border: none; background: var(--primary, #007AFF); color: white; cursor: pointer;">Очистить корзину</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Обработчики кнопок
            document.getElementById('cancelDifferentShop').onclick = () => {
                modal.remove();
                resolve(false);
            };
            
            document.getElementById('clearCartAndAdd').onclick = async () => {
                try {
                    // Очищаем корзину
                    await api.clearCart();
                    state.cart = [];
                    
                    // Добавляем новый товар
                    await api.addToCart(newProduct.id, quantity);
                    if (utils.showToast) utils.showToast('Корзина очищена, товар добавлен', 'success');
                    
                    // Перезагружаем корзину
                    await loadCart();
                    
                    modal.remove();
                    resolve(false); // false, потому что уже добавили товар
                } catch (error) {
                    console.error('Error clearing cart:', error);
                    if (utils.showToast) utils.showToast('Ошибка очистки корзины', 'error');
                    modal.remove();
                    resolve(false);
                }
            };
            
            // Закрытие по клику на фон
            modal.onclick = (e) => {
                if (e.target === modal) {
                    modal.remove();
                    resolve(false);
                }
            };
        });
    }
    
    // Улучшаем updateCartQuantity для обработки ошибок
    async function updateCartQuantity(itemId, quantity) {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        console.log('[updateCartQuantity] Called with:', { itemId, quantity, type: typeof quantity });
        
        // Убеждаемся, что quantity - это число
        let quantityNum;
        if (typeof quantity === 'object' && quantity !== null && 'quantity' in quantity) {
            quantityNum = typeof quantity.quantity === 'number' ? quantity.quantity : parseInt(quantity.quantity, 10);
            console.log('[updateCartQuantity] Extracted from object:', quantityNum);
        } else if (typeof quantity === 'number') {
            quantityNum = quantity;
        } else {
            quantityNum = parseInt(quantity, 10);
        }
        
        console.log('[updateCartQuantity] Final quantityNum:', quantityNum, 'type:', typeof quantityNum);
        
        if (isNaN(quantityNum) || quantityNum < 1) {
            if (quantityNum < 1) {
                removeFromCart(itemId);
                return;
            }
            console.error('[updateCartQuantity] Invalid quantity:', quantity);
            if (utils.showToast) utils.showToast('Некорректное количество', 'error');
            return;
        }
        
        try {
            console.log('[updateCartQuantity] Calling api.updateCartItem with:', { itemId, quantityNum });
            await api.updateCartItem(itemId, quantityNum);
            await loadCart();
            renderCart();
        } catch (error) {
            console.error('Error updating cart quantity:', error);
            // Парсим ошибку от бэкенда
            let errorMessage = 'Ошибка обновления корзины';
            if (error.response) {
                const detail = error.response.detail;
                if (typeof detail === 'string') {
                    errorMessage = detail;
                } else if (Array.isArray(detail) && detail.length > 0) {
                    errorMessage = detail[0].msg || detail[0].message || errorMessage;
                } else if (typeof detail === 'object' && detail.message) {
                    errorMessage = detail.message;
                }
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            if (errorMessage.includes('Not enough') || errorMessage.includes('недостаточно') || errorMessage.includes('stock')) {
                if (utils.showToast) utils.showToast('Недостаточно товара на складе', 'error');
            } else {
                if (utils.showToast) utils.showToast(errorMessage, 'error');
            }
            // Обновляем корзину чтобы показать актуальные данные
            await loadCart();
            renderCart();
        }
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.cart = {
        loadCart,
        renderCart,
        updateCartSummary,
        updateCartQuantity,
        removeFromCart,
        clearCart,
        updateQuantity,
        addToCart,
        updateProductPageCartUI,
        updateProductCartQuantity
    };
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.loadCart = loadCart;
    window.renderCart = renderCart;
    window.updateCartSummary = updateCartSummary;
    window.updateCartQuantity = updateCartQuantity;
    window.removeFromCart = removeFromCart;
    window.clearCart = clearCart;
    window.updateQuantity = updateQuantity;
    window.addToCart = addToCart;
    window.updateProductPageCartUI = updateProductPageCartUI;
    window.updateProductCartQuantity = updateProductCartQuantity;
})();

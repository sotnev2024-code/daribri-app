/**
 * Orders Module - заказы магазина и пользователя
 */

(function() {
    'use strict';
    
    // Получаем ссылки на state, elements, api и utils
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getApi = () => window.api;
    const getUtils = () => window.App?.utils || {};
    
    // Состояние заказов магазина
    let shopOrdersState = {
        orders: [],
        currentStatus: '',
        loading: false
    };
    
    // ==================== Shop Orders ====================
    
    async function loadShopOrders(status = '') {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        console.log('[SHOP ORDERS] Loading orders, status:', status);
        
        // Если магазин не загружен, загружаем его
        if (!state.myShop) {
            console.log('[SHOP ORDERS] Shop not loaded, loading now...');
            try {
                state.myShop = await api.getMyShop();
                console.log('[SHOP ORDERS] Shop loaded:', state.myShop);
            } catch (error) {
                console.error('[SHOP ORDERS] Error loading shop:', error);
                if (utils.showToast) utils.showToast('Магазин не найден', 'error');
                return;
            }
        }
        
        if (!state.myShop) {
            console.error('[SHOP ORDERS] Shop not found!');
            if (utils.showToast) utils.showToast('Магазин не найден', 'error');
            return;
        }
        
        shopOrdersState.currentStatus = status;
        shopOrdersState.loading = true;
        
        const ordersList = document.getElementById('shopOrdersList');
        const ordersEmpty = document.getElementById('shopOrdersEmpty');
        
        console.log('[SHOP ORDERS] Shop ID:', state.myShop.id);
        console.log('[SHOP ORDERS] Elements:', { ordersList: !!ordersList, ordersEmpty: !!ordersEmpty });
        
        try {
            const orders = await api.getShopOrders(state.myShop.id, {
                status: status || undefined,
                limit: 50
            });
            
            console.log('[SHOP ORDERS] Loaded orders:', orders?.length || 0);
            
            // Проверяем, что orders - массив
            if (!Array.isArray(orders)) {
                console.error('[SHOP ORDERS] Invalid orders format:', orders);
                throw new Error('Неверный формат данных заказов');
            }
            
            shopOrdersState.orders = orders;
            
            if (orders.length === 0) {
                if (ordersList) ordersList.innerHTML = '';
                if (ordersEmpty) ordersEmpty.hidden = false;
            } else {
                if (ordersEmpty) ordersEmpty.hidden = true;
                if (ordersList) {
                    ordersList.innerHTML = orders.map(order => renderShopOrderCard(order)).join('');
                    
                    // Добавляем обработчики для изменения статуса
                    ordersList.querySelectorAll('.order-status-select').forEach(select => {
                        select.addEventListener('change', (e) => {
                            const orderId = parseInt(e.target.dataset.orderId);
                            const newStatus = e.target.value;
                            updateOrderStatus(orderId, newStatus);
                        });
                    });
                }
            }
            
            // Обновляем активные вкладки фильтров
            document.querySelectorAll('.filter-tab').forEach(tab => {
                tab.classList.toggle('active', tab.dataset.status === status);
            });
            
            // Инициализируем обработчики фильтров после первой загрузки
            if (!document.querySelector('.filter-tab')?.hasAttribute('data-listener')) {
                initOrderFilters();
                document.querySelectorAll('.filter-tab').forEach(tab => {
                    tab.setAttribute('data-listener', 'true');
                });
            }
        } catch (error) {
            console.error('[SHOP ORDERS] Error loading shop orders:', error);
            console.error('[SHOP ORDERS] Error details:', {
                message: error.message,
                stack: error.stack,
                shopId: state.myShop?.id
            });
            
            if (utils.showToast) {
                const errorMessage = error.message || 'Ошибка загрузки заказов';
                utils.showToast(errorMessage, 'error');
            }
            
            if (ordersList) ordersList.innerHTML = '';
            if (ordersEmpty) ordersEmpty.hidden = false;
        } finally {
            shopOrdersState.loading = false;
        }
    }
    
    function formatDeliveryDate(dateString) {
        if (!dateString) return 'Не указана';
        try {
            // Парсим дату (может быть в формате YYYY-MM-DD или ISO)
            if (typeof dateString === 'string' && dateString.includes('-')) {
                const parts = dateString.split('-');
                if (parts.length === 3) {
                    // Формат YYYY-MM-DD
                    const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                    return date.toLocaleDateString('ru-RU', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                    });
                }
            }
            // Пробуем распарсить как ISO дату
            const date = new Date(dateString);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString('ru-RU', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                });
            }
            return dateString;
        } catch (e) {
            console.error('Error formatting delivery date:', e, dateString);
            return dateString || 'Не указана';
        }
    }
    
    function renderShopOrderCard(order) {
        const utils = getUtils();
        const formatPrice = utils.formatPrice || ((price) => new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
        }).format(price));
        
        const statusLabels = {
            'pending': 'Ожидает',
            'processing': 'В обработке',
            'delivered': 'Доставлен',
            'cancelled': 'Отменён'
        };
        
        const statusColors = {
            'pending': '#FFA726',
            'processing': '#42A5F5',
            'delivered': '#66BB6A',
            'cancelled': '#EF5350'
        };
        
        const statusLabel = statusLabels[order.status] || order.status;
        const statusColor = statusColors[order.status] || '#757575';
        
        const orderDate = new Date(order.created_at);
        const dateStr = orderDate.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // Безопасная обработка items - проверяем, что items существует и является массивом
        const itemsList = (order.items && Array.isArray(order.items) && order.items.length > 0)
            ? order.items.map(item => {
                const itemPrice = item.discount_price || item.price;
                const quantity = item.quantity || 1;
                return `
                    <div class="order-item-mini">
                        <span class="order-item-name">${item.product_name || 'Товар удалён'} × ${quantity}</span>
                        <span class="order-item-price">${formatPrice(parseFloat(itemPrice || 0) * quantity)}</span>
                    </div>
                `;
            }).join('')
            : '<div class="order-item-mini"><span class="order-item-name">Товары недоступны</span></div>';
        
        return `
            <div class="shop-order-card" data-order-id="${order.id}">
                <div class="order-card-header">
                    <div class="order-number">${order.order_number}</div>
                    <div class="order-date">${dateStr}</div>
                </div>
                
                <div class="order-customer-info">
                    <div class="info-row">
                        <span class="info-label">Клиент:</span>
                        <span>${order.recipient_name || 'Не указано'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Телефон:</span>
                        <span>${order.recipient_phone || 'Не указан'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Адрес:</span>
                        <span>${order.delivery_address || 'Не указан'}</span>
                    </div>
                    ${order.delivery_date ? `
                    <div class="info-row">
                        <span class="info-label">Дата доставки:</span>
                        <span>${formatDeliveryDate(order.delivery_date)}</span>
                    </div>
                    ` : ''}
                    ${order.delivery_time ? `
                    <div class="info-row">
                        <span class="info-label">Время доставки:</span>
                        <span>${order.delivery_time}</span>
                    </div>
                    ` : ''}
                </div>
                
                <div class="order-items-list">
                    ${itemsList}
                </div>
                
                <div class="order-card-footer">
                    <div class="order-total">
                        <span>Итого:</span>
                        <span class="total-amount">${formatPrice(order.total_amount)}</span>
                    </div>
                    <div class="order-status-control">
                        <select class="order-status-select" data-order-id="${order.id}" style="border-color: ${statusColor}">
                            <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>Ожидает</option>
                            <option value="processing" ${order.status === 'processing' ? 'selected' : ''}>В обработке</option>
                            <option value="delivered" ${order.status === 'delivered' ? 'selected' : ''}>Доставлен</option>
                            <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>Отменён</option>
                        </select>
                    </div>
                </div>
                
                ${order.comment ? `<div class="order-comment"><strong>Комментарий:</strong> ${order.comment}</div>` : ''}
            </div>
        `;
    }
    
    async function updateOrderStatus(orderId, newStatus) {
        const api = getApi();
        const utils = getUtils();
        
        try {
            await api.updateOrderStatus(orderId, newStatus);
            if (utils.showToast) utils.showToast('Статус заказа обновлён', 'success');
            await loadShopOrders(shopOrdersState.currentStatus);
        } catch (error) {
            console.error('Error updating order status:', error);
            if (utils.showToast) utils.showToast('Ошибка обновления статуса', 'error');
            // Перезагружаем заказы, чтобы вернуть предыдущий статус
            await loadShopOrders(shopOrdersState.currentStatus);
        }
    }
    
    function initOrderFilters() {
        document.querySelectorAll('.filter-tab').forEach(tab => {
            // Удаляем старые обработчики
            const newTab = tab.cloneNode(true);
            tab.parentNode.replaceChild(newTab, tab);
            
            // Добавляем новый обработчик
            newTab.addEventListener('click', () => {
                const status = newTab.dataset.status;
                loadShopOrders(status);
            });
        });
    }
    
    // ==================== User Orders ====================
    
    async function loadUserOrders(status = '') {
        const elements = getElements();
        const api = getApi();
        const utils = getUtils();
        
        console.log('[USER ORDERS] Loading orders, status:', status);
        const ordersList = elements?.userOrdersList;
        const ordersEmpty = elements?.userOrdersEmpty;
        
        if (!ordersList || !ordersEmpty) {
            console.error('[USER ORDERS] Elements not found:', {
                ordersList: !!ordersList,
                ordersEmpty: !!ordersEmpty
            });
            return;
        }
        
        try {
            const orders = await api.getOrders({
                status: status || undefined,
                limit: 50
            });
            
            console.log('[USER ORDERS] Orders loaded:', orders.length);
            
            if (orders.length === 0) {
                ordersList.innerHTML = '';
                ordersEmpty.hidden = false;
            } else {
                ordersEmpty.hidden = true;
                ordersList.innerHTML = orders.map(order => renderUserOrderCard(order)).join('');
            }
            
            // Обновляем активные вкладки фильтров
            const filterTabs = document.querySelectorAll('#myOrdersPage .filter-tab');
            filterTabs.forEach(tab => {
                tab.classList.toggle('active', tab.dataset.status === status);
            });
            
            // Инициализируем обработчики фильтров
            filterTabs.forEach(tab => {
                const newTab = tab.cloneNode(true);
                tab.parentNode.replaceChild(newTab, tab);
                
                newTab.addEventListener('click', () => {
                    const filterStatus = newTab.dataset.status;
                    loadUserOrders(filterStatus);
                });
            });
        } catch (error) {
            console.error('[USER ORDERS] Error loading orders:', error);
            if (utils.showToast) utils.showToast('Ошибка загрузки заказов', 'error');
            if (ordersEmpty) ordersEmpty.hidden = false;
        }
    }
    
    function renderUserOrderCard(order) {
        const utils = getUtils();
        const formatPrice = utils.formatPrice || ((price) => new Intl.NumberFormat('ru-RU', {
            style: 'currency',
            currency: 'RUB',
            minimumFractionDigits: 0,
        }).format(price));
        
        const getMediaUrl = utils.getMediaUrl || ((url) => {
            if (!url) return '';
            if (url.startsWith('blob:') || url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
                return url;
            }
            const api = getApi();
            if (!api) return url;
            if (url.startsWith('/')) {
                return api.baseUrl + url;
            }
            return api.baseUrl + '/media/' + url;
        });
        
        const statusLabels = {
            'pending': 'Ожидает',
            'processing': 'В обработке',
            'delivered': 'Доставлен',
            'cancelled': 'Отменен'
        };
        
        const statusColors = {
            'pending': '#FFA726',
            'processing': '#42A5F5',
            'delivered': '#66BB6A',
            'cancelled': '#EF5350'
        };
        
        const statusLabel = statusLabels[order.status] || order.status;
        const statusColor = statusColors[order.status] || '#9CA3AF';
        
        const itemsHtml = order.items?.map(item => {
            const imageUrl = item.product_image_url ? getMediaUrl(item.product_image_url) : '';
            return `
                <div class="order-item">
                    ${imageUrl ? `<img src="${imageUrl}" alt="${item.product_name || 'Товар'}" class="order-item-image">` : '<div class="order-item-image-placeholder">📦</div>'}
                    <div class="order-item-info">
                        <div class="order-item-name">${item.product_name || 'Товар'}</div>
                        <div class="order-item-details">
                            <span>${item.quantity} шт.</span>
                            <span>×</span>
                            <span>${formatPrice(item.price)}</span>
                        </div>
                    </div>
                    <div class="order-item-total">${formatPrice(item.quantity * item.price)}</div>
                </div>
            `;
        }).join('') || '';
        
        return `
            <div class="user-order-card">
                <div class="order-header">
                    <div class="order-info">
                        <div class="order-number">Заказ #${order.order_number || order.id}</div>
                        <div class="order-date">${formatOrderDate(order.created_at)}</div>
                    </div>
                    <div class="order-status-badge" style="background-color: ${statusColor}20; color: ${statusColor};">
                        ${statusLabel}
                    </div>
                </div>
                <div class="order-shop">
                    <span class="order-shop-label">Магазин:</span>
                    <span class="order-shop-name">${order.shop_name || 'Неизвестный магазин'}</span>
                </div>
                <div class="order-items">
                    ${itemsHtml}
                </div>
                ${order.delivery_address ? `
                <div class="order-delivery">
                    <span class="order-delivery-label">Адрес доставки:</span>
                    <span class="order-delivery-address">${order.delivery_address}</span>
                </div>
                ` : ''}
                ${order.delivery_date ? `
                <div class="order-delivery-info">
                    <span class="order-delivery-label">Дата доставки:</span>
                    <span>${formatDeliveryDate(order.delivery_date)}</span>
                </div>
                ` : ''}
                ${order.delivery_time ? `
                <div class="order-delivery-info">
                    <span class="order-delivery-label">Время доставки:</span>
                    <span>${order.delivery_time}</span>
                </div>
                ` : ''}
                <div class="order-footer">
                    <div class="order-total">
                        <span class="order-total-label">Итого:</span>
                        <span class="order-total-value">${formatPrice(order.total_amount)}</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    function formatOrderDate(dateString) {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            return dateString;
        }
    }
    
    // Экспорт функций
    window.App = window.App || {};
    window.App.orders = {
        // Shop Orders
        loadShopOrders,
        renderShopOrderCard,
        updateOrderStatus,
        initOrderFilters,
        // User Orders
        loadUserOrders,
        renderUserOrderCard,
        // Utils
        formatDeliveryDate,
        formatOrderDate
    };
    
    // Глобальный экспорт для обратной совместимости
    window.loadShopOrders = loadShopOrders;
    window.loadUserOrders = loadUserOrders;
    window.updateOrderStatus = updateOrderStatus;
    window.renderShopOrderCard = renderShopOrderCard;
    window.renderUserOrderCard = renderUserOrderCard;
    window.initOrderFilters = initOrderFilters;
    
    console.log('[ORDERS] Orders module loaded with shop and user order functions.');
})();


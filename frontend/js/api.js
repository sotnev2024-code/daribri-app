/**
 * API клиент для Telegram Mini App
 */

console.log('📡 api.js загружен!');

class API {
    constructor(baseUrl = '') {
        // Определяем baseUrl для API
        if (window.location.protocol === 'file:' || window.location.port === '63342') {
            // Открыто как файл или через IDE
            this.baseUrl = 'http://localhost:8080';
        } else if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.hostname === '') {
            // Открыто через локальный сервер - API всегда на порту 8080
            this.baseUrl = `http://${window.location.hostname}:8080`;
        } else {
            // Продакшн или другой хост
            this.baseUrl = baseUrl || window.location.origin;
        }
        
        // Telegram ID (будет установлен из Telegram WebApp)
        this.telegramId = null;
        
        // Получаем ID из Telegram WebApp если доступен
        if (window.Telegram?.WebApp?.initDataUnsafe?.user) {
            this.telegramId = window.Telegram.WebApp.initDataUnsafe.user.id;
        }
        
        console.log('📡 API initialized');
        console.log('  baseUrl:', this.baseUrl);
        console.log('  telegramId:', this.telegramId);
        console.log('  location:', window.location.href);
    }

    /**
     * Устанавливает Telegram ID для авторизации
     */
    setTelegramId(id) {
        this.telegramId = id;
    }

    /**
     * Выполняет HTTP запрос
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}/api${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.telegramId) {
            headers['X-Telegram-ID'] = String(this.telegramId);
        }

        console.log(`🌐 API Request: ${options.method || 'GET'} ${url}`);
        console.log(`🌐 Headers:`, headers);
        if (options.body) {
            console.log(`🌐 Request body (raw):`, options.body);
            // Пытаемся распарсить body если это JSON строка
            try {
                const parsed = JSON.parse(options.body);
                console.log(`🌐 Request body (parsed):`, parsed);
            } catch (e) {
                console.log(`🌐 Request body is not JSON string`);
            }
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            console.log(`📥 API Response: ${response.status} ${response.statusText}`);
            console.log(`📥 Response headers:`, Object.fromEntries(response.headers.entries()));

            if (!response.ok) {
                let errorData;
                try {
                    const text = await response.text();
                    console.error(`❌ Response body:`, text);
                    errorData = JSON.parse(text);
                } catch {
                    errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
                }
                
                // Обработка различных форматов ошибок
                let errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
                if (Array.isArray(errorData.detail)) {
                    // Pydantic validation errors
                    errorMessage = errorData.detail.map(e => e.msg || e.message || String(e)).join(', ');
                }
                
                const error = new Error(errorMessage);
                error.status = response.status;
                error.data = errorData;
                console.error(`❌ API Error: ${endpoint}`, error);
                throw error;
            }

            if (response.status === 204) {
                return null;
            }

            const data = await response.json();
            console.log(`✅ API Success: ${endpoint}`, Array.isArray(data) ? `Array(${data.length})` : typeof data);
            return data;
        } catch (error) {
            console.error(`❌ API Error: ${endpoint}`, error);
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.error('💡 Возможно, сервер не запущен или недоступен по адресу:', this.baseUrl);
                console.error('💡 Проверьте:');
                console.error('   1. Сервер запущен: python run_api.py');
                console.error('   2. Сервер доступен: http://localhost:8080/health');
                console.error('   3. CORS настроен правильно');
            }
            throw error;
        }
    }

    // ==================== Users ====================

    async createOrUpdateUser(userData) {
        return this.request('/users/', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    }

    async getMe() {
        return this.request('/users/me');
    }

    // ==================== Categories ====================

    async getCategories() {
        return this.request('/categories/');
    }

    async getCategoriesFlat() {
        return this.request('/categories/flat');
    }

    async getCategory(id) {
        return this.request(`/categories/${id}`);
    }

    async getCategoryProducts(id, options = {}) {
        const params = new URLSearchParams();
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        if (options.includeSubcategories !== undefined) {
            params.append('include_subcategories', options.includeSubcategories);
        }
        return this.request(`/categories/${id}/products?${params}`);
    }

    // ==================== Products ====================

    async getProducts(options = {}) {
        const params = new URLSearchParams();
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        if (options.categoryId) params.append('category_id', options.categoryId);
        if (options.search) params.append('search', options.search);
        if (options.minPrice !== undefined && options.minPrice !== null) params.append('min_price', options.minPrice);
        if (options.maxPrice !== undefined && options.maxPrice !== null) params.append('max_price', options.maxPrice);
        if (options.trending) params.append('trending', 'true');
        if (options.discounted) params.append('discounted', 'true');
        if (options.inStock !== undefined) params.append('in_stock', options.inStock ? 'true' : 'false');
        return this.request(`/products/?${params}`);
    }

    async getTrendingProducts(limit = 10) {
        return this.request(`/products/trending?limit=${limit}`);
    }

    async getDiscountedProducts(limit = 20) {
        return this.request(`/products/discounted?limit=${limit}`);
    }

    async getProduct(id) {
        const params = this.telegramId ? `?x_telegram_id=${this.telegramId}` : '';
        return this.request(`/products/${id}${params}`);
    }

    // ==================== Cart ====================

    async getCart() {
        return this.request('/cart/');
    }

    async getCartSummary() {
        return this.request('/cart/summary');
    }

    async addToCart(productId, quantity = 1) {
        return this.request('/cart/', {
            method: 'POST',
            body: JSON.stringify({ product_id: productId, quantity }),
        });
    }

    async updateCartItem(itemId, quantity) {
        // Принимаем quantity - должно быть число
        console.log(`[updateCartItem] START: itemId=${itemId}`);
        console.log(`[updateCartItem] quantity parameter:`, quantity);
        console.log(`[updateCartItem] quantity type:`, typeof quantity);
        console.log(`[updateCartItem] quantity is object:`, typeof quantity === 'object' && quantity !== null);
        if (typeof quantity === 'object') {
            console.log(`[updateCartItem] quantity keys:`, Object.keys(quantity));
            console.log(`[updateCartItem] quantity JSON:`, JSON.stringify(quantity));
        }
        
        // Извлекаем число из любого формата
        let quantityNum;
        
        // Если передан объект {quantity: ...}
        if (quantity && typeof quantity === 'object' && quantity !== null && !Array.isArray(quantity)) {
            if ('quantity' in quantity) {
                quantityNum = quantity.quantity;
                console.log(`[updateCartItem] Extracted from object:`, quantityNum);
            } else {
                // Если объект не имеет поля quantity, это ошибка
                throw new Error(`Invalid quantity object: expected {quantity: number}, got ${JSON.stringify(quantity)}`);
            }
        } 
        // Если уже число
        else if (typeof quantity === 'number') {
            quantityNum = quantity;
        } 
        // Если строка или что-то другое
        else {
            quantityNum = parseInt(String(quantity), 10);
        }
        
        // Финальная проверка и нормализация
        // Явно приводим к числу
        if (typeof quantityNum === 'string') {
            quantityNum = parseInt(quantityNum, 10);
        }
        quantityNum = Number(quantityNum);
        
        console.log(`[updateCartItem] After processing: quantityNum=${quantityNum}, type=${typeof quantityNum}`);
        
        if (isNaN(quantityNum) || !Number.isInteger(quantityNum) || quantityNum < 1) {
            throw new Error(`Invalid quantity: ${quantity} -> ${quantityNum}`);
        }
        
        // КРИТИЧЕСКИ ВАЖНО: убеждаемся что quantityNum - это ПРИМИТИВНОЕ число, не объект
        // Используем Number() для явного преобразования
        const finalQuantity = Number(quantityNum);
        
        if (typeof finalQuantity !== 'number' || !Number.isInteger(finalQuantity)) {
            console.error(`[updateCartItem] ERROR: finalQuantity is not an integer!`, finalQuantity, typeof finalQuantity);
            throw new Error(`Invalid quantity: ${finalQuantity} is not a number`);
        }
        
        // Создаем объект напрямую - quantity должен быть ПРИМИТИВНЫМ числом
        const requestBody = { quantity: finalQuantity };
        
        // ВАЖНО: проверяем структуру ПЕРЕД stringify
        console.log(`[updateCartItem] requestBody before stringify:`, requestBody);
        console.log(`[updateCartItem] requestBody.quantity:`, requestBody.quantity);
        console.log(`[updateCartItem] requestBody.quantity type:`, typeof requestBody.quantity);
        
        // Проверяем что quantity не является объектом
        if (typeof requestBody.quantity === 'object') {
            console.error(`[updateCartItem] CRITICAL: requestBody.quantity is an object!`, requestBody.quantity);
            throw new Error(`Quantity is an object instead of number: ${JSON.stringify(requestBody.quantity)}`);
        }
        
        // Преобразуем в JSON строку
        const bodyString = JSON.stringify(requestBody);
        
        console.log(`[updateCartItem] bodyString:`, bodyString);
        
        // Дополнительная проверка после stringify - парсим обратно
        try {
            const parsedCheck = JSON.parse(bodyString);
            console.log(`[updateCartItem] Parsed check:`, parsedCheck);
            console.log(`[updateCartItem] Parsed quantity:`, parsedCheck.quantity, `type:`, typeof parsedCheck.quantity);
            
            // Проверяем что после парсинга quantity - это число, а не объект
            if (typeof parsedCheck.quantity === 'object') {
                console.error(`[updateCartItem] CRITICAL ERROR: parsed quantity is an object!`, parsedCheck);
                throw new Error(`After stringify/parse, quantity is an object: ${JSON.stringify(parsedCheck.quantity)}`);
            }
            
            if (typeof parsedCheck.quantity !== 'number') {
                console.error(`[updateCartItem] CRITICAL ERROR: quantity is not a number after stringify!`, parsedCheck);
                throw new Error(`Failed to create valid request body: quantity is ${typeof parsedCheck.quantity}`);
            }
        } catch (e) {
            console.error(`[updateCartItem] ERROR in validation:`, e);
            throw e;
        }
        
        console.log(`[updateCartItem] Sending request with body:`, bodyString);
        
        // ВАЖНО: передаем строку, а не объект
        return this.request(`/cart/${itemId}`, {
            method: 'PATCH',
            body: bodyString,
        });
    }

    async removeFromCart(itemId) {
        return this.request(`/cart/${itemId}`, {
            method: 'DELETE',
        });
    }

    async clearCart() {
        return this.request('/cart/', {
            method: 'DELETE',
        });
    }

    // ==================== Favorites ====================

    async getFavorites() {
        return this.request('/favorites/');
    }

    async addToFavorites(productId) {
        return this.request('/favorites/', {
            method: 'POST',
            body: JSON.stringify({ product_id: productId }),
        });
    }

    async removeFromFavorites(productId) {
        return this.request(`/favorites/${productId}`, {
            method: 'DELETE',
        });
    }

    async toggleFavorite(productId) {
        return this.request(`/favorites/toggle/${productId}`, {
            method: 'POST',
        });
    }

    // ==================== Orders ====================

    async getOrders(options = {}) {
        const params = new URLSearchParams();
        if (options.status) params.append('status', options.status);
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        return this.request(`/orders/?${params}`);
    }

    async getOrder(id) {
        return this.request(`/orders/${id}`);
    }

    async createOrder(orderData) {
        return this.request('/orders/', {
            method: 'POST',
            body: JSON.stringify(orderData),
        });
    }

    async cancelOrder(id) {
        return this.request(`/orders/${id}/cancel`, {
            method: 'PATCH',
        });
    }

    async updateOrderStatus(orderId, status) {
        return this.request(`/orders/${orderId}/status?status=${status}`, {
            method: 'PATCH',
        });
    }

    // ==================== Shops ====================

    async getShops(options = {}) {
        const params = new URLSearchParams();
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        if (options.search) params.append('search', options.search);
        return this.request(`/shops/?${params}`);
    }

    async getMyShop() {
        return this.request('/shops/my');
    }

    async getShop(id) {
        return this.request(`/shops/${id}`);
    }

    async getShopProducts(shopId, options = {}) {
        const params = new URLSearchParams();
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        return this.request(`/shops/${shopId}/products?${params}`);
    }

    async createShop(shopData) {
        return this.request('/shops/', {
            method: 'POST',
            body: JSON.stringify(shopData),
        });
    }

    async updateShop(id, shopData) {
        return this.request(`/shops/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(shopData),
        });
    }

    async uploadShopPhoto(shopId, file) {
        if (!file) {
            throw new Error('File is required');
        }
        
        const formData = new FormData();
        formData.append('photo', file);
        
        const url = `${this.baseUrl}/api/shops/${shopId}/photo`;
        const headers = {};
        
        if (this.telegramId) {
            headers['X-Telegram-ID'] = String(this.telegramId);
        }
        
        // НЕ устанавливаем Content-Type вручную - браузер должен установить его автоматически с boundary
        // для multipart/form-data
        
        console.log(`🌐 API Request: POST ${url}`);
        console.log(`🌐 File info: name=${file.name}, type=${file.type}, size=${file.size}`);
        console.log(`🌐 FormData entries:`, Array.from(formData.entries()).map(([k, v]) => [k, v instanceof File ? `File(${v.name})` : v]));
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: formData,
            });
            
            console.log(`📥 API Response: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
                }
                
                let errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
                if (Array.isArray(errorData.detail)) {
                    errorMessage = errorData.detail.map(e => e.msg || e.message || String(e)).join(', ');
                }
                
                const error = new Error(errorMessage);
                error.status = response.status;
                error.data = errorData;
                console.error(`❌ API Error: /shops/${shopId}/photo`, error);
                throw error;
            }
            
            const data = await response.json();
            console.log(`✅ API Success: /shops/${shopId}/photo`, data);
            return data;
        } catch (error) {
            console.error(`❌ API Error: /shops/${shopId}/photo`, error);
            throw error;
        }
    }

    // ==================== Shop Orders ====================

    async getShopOrders(shopId, options = {}) {
        const params = new URLSearchParams();
        if (options.status) params.append('status', options.status);
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        return this.request(`/orders/shop/${shopId}?${params}`);
    }

    // ==================== Reviews ====================

    async getShopReviews(shopId, options = {}) {
        const params = new URLSearchParams();
        if (options.skip) params.append('skip', options.skip);
        if (options.limit) params.append('limit', options.limit);
        return this.request(`/reviews/shop/${shopId}?${params}`);
    }

    // ==================== Statistics ====================

    async getShopStatistics(startDate, endDate) {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        return this.request(`/shops/my/statistics?${params}`);
    }

    async createReview(reviewData) {
        return this.request('/reviews/', {
            method: 'POST',
            body: JSON.stringify(reviewData),
        });
    }

    // ==================== Banners ====================

    async getBanners(activeOnly = true) {
        return this.request(`/banners/?active_only=${activeOnly}`);
    }

    // ==================== Subscriptions ====================

    async getSubscriptionPlans() {
        return this.request('/subscriptions/plans');
    }

    async getMySubscription() {
        return this.request('/subscriptions/my');
    }

    async subscribe(planId) {
        return this.request(`/subscriptions/subscribe/${planId}`, {
            method: 'POST',
        });
    }

    async requestSubscriptionPayment(planId) {
        // ВРЕМЕННО используем диагностический эндпоинт для отладки
        // TODO: Вернуть обратно на /subscriptions/request-payment/${planId} после исправления
        return this.request(`/subscriptions/request-payment-direct/${planId}`, {
            method: 'POST',
        });
    }

    async getSubscriptionHistory() {
        return this.request('/subscriptions/history');
    }

    async getSubscriptionUsage() {
        return this.request('/subscriptions/usage');
    }

    // ==================== Promo Codes ====================

    async validatePromoCode(code, shopId, totalAmount, isFirstOrder = false) {
        return this.request('/promo/validate', {
            method: 'POST',
            body: JSON.stringify({
                code,
                shop_id: shopId,
                total_amount: totalAmount,
                is_first_order: isFirstOrder
            }),
        });
    }
}

// Глобальный экземпляр API
const api = new API();

// Делаем доступным глобально для отладки
window.api = api;


/**
 * My Shop Module - мой магазин и статистика
 */

(function() {
    'use strict';
    
    // Получаем ссылки на state, elements, api и utils
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getApi = () => window.api;
    const getUtils = () => window.App?.utils || {};
    
    // Константа города (приложение работает только в Екатеринбурге)
    const APP_CITY = 'Екатеринбург';
    
    /**
     * Нормализует адрес магазина для отображения
     * Убирает любые упоминания города из адреса и добавляет "г. Екатеринбург" в начало
     * @param {string} address - исходный адрес
     * @returns {string} - нормализованный адрес в формате "г. Екатеринбург, {адрес}"
     */
    function normalizeShopAddress(address) {
        if (!address || !address.trim()) {
            return `г. ${APP_CITY}`;
        }
        
        let cleanedAddress = address.trim();
        
        // Шаг 1: Убираем все упоминания "г. Екатеринбург" или "Екатеринбург" из адреса (в любом месте)
        const cityPatterns = [
            new RegExp(`г\\.?\\s*${APP_CITY}\\s*,?\\s*`, 'gi'),
            new RegExp(`г\\.?\\s*${APP_CITY.toLowerCase()}\\s*,?\\s*`, 'gi'),
            new RegExp(`\\s*,?\\s*${APP_CITY}\\s*,?\\s*`, 'gi'),
            new RegExp(`\\s*,?\\s*${APP_CITY.toLowerCase()}\\s*,?\\s*`, 'gi'),
        ];
        
        for (const pattern of cityPatterns) {
            cleanedAddress = cleanedAddress.replace(pattern, ' ').trim();
        }
        
        // Шаг 2: Убираем любые упоминания "г. " в начале адреса (независимо от города)
        cleanedAddress = cleanedAddress.replace(/^г\.?\s*[^,]+,\s*/i, '').trim();
        cleanedAddress = cleanedAddress.replace(/^г\.?\s*[^,гул]+(?=\s*(г\.|ул\.|улица|,))/i, '').trim();
        
        // Шаг 3: Убираем лишние запятые, пробелы и двойные пробелы
        cleanedAddress = cleanedAddress.replace(/^,\s*|\s*,/g, '').trim();
        cleanedAddress = cleanedAddress.replace(/\s+/g, ' ').trim();
        
        // Если адрес стал пустым, возвращаем только город
        if (!cleanedAddress) {
            return `г. ${APP_CITY}`;
        }
        
        // Всегда добавляем город в начало
        return `г. ${APP_CITY}, ${cleanedAddress}`;
    }
    
    // Глобальная переменная для хранения экземпляров графиков Chart.js
    let statisticsCharts = {
        revenue: null,
        orders: null,
        status: null,
        topProducts: null
    };
    
    // ==================== Shop Statistics ====================
    
    async function loadShopStatistics() {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        console.log('[STATISTICS] Loading shop statistics...');
        
        // Если магазин не загружен, загружаем его
        if (!state.myShop) {
            console.log('[STATISTICS] Shop not loaded, loading now...');
            try {
                state.myShop = await api.getMyShop();
                console.log('[STATISTICS] Shop loaded:', state.myShop);
            } catch (error) {
                console.error('[STATISTICS] Error loading shop:', error);
                if (utils.showToast) utils.showToast('Магазин не найден', 'error');
                return;
            }
        }
        
        if (!state.myShop) {
            console.error('[STATISTICS] Shop not found!');
            if (utils.showToast) utils.showToast('Магазин не найден', 'error');
            return;
        }
        
        const loadingEl = document.getElementById('statisticsLoading');
        const emptyEl = document.getElementById('statisticsEmpty');
        const contentEl = document.querySelector('#shopStatisticsPage .page-content > .statistics-cards');
        
        console.log('[STATISTICS] Elements:', { loadingEl: !!loadingEl, emptyEl: !!emptyEl, contentEl: !!contentEl });
        
        if (loadingEl) loadingEl.hidden = false;
        if (emptyEl) emptyEl.hidden = true;
        if (contentEl) contentEl.style.opacity = '0.5';
        
        try {
            const startDate = document.getElementById('statisticsStartDate')?.value;
            const endDate = document.getElementById('statisticsEndDate')?.value;
            
            // Проверка доступности метода
            if (typeof api === 'undefined' || !api || typeof api.getShopStatistics !== 'function') {
                console.error('[STATISTICS] API or method not available');
                console.error('[STATISTICS] api:', api);
                if (api) {
                    console.error('[STATISTICS] Available methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(api)).filter(m => typeof api[m] === 'function'));
                }
                throw new Error('API метод getShopStatistics недоступен. Обновите страницу (Ctrl+F5)');
            }
            
            const stats = await api.getShopStatistics(startDate, endDate);
            
            // Обновляем основные метрики
            const formatPrice = utils.formatPrice || ((price) => new Intl.NumberFormat('ru-RU', {
                style: 'currency',
                currency: 'RUB',
                minimumFractionDigits: 0,
            }).format(price));
            
            document.getElementById('statTotalOrders').textContent = stats.total_orders || 0;
            document.getElementById('statTotalRevenue').textContent = formatPrice(stats.total_revenue || 0);
            document.getElementById('statAvgOrderValue').textContent = formatPrice(stats.average_order_value || 0);
            
            // Отрисовываем графики
            renderStatisticsCharts(stats);
            
            if (loadingEl) loadingEl.hidden = true;
            if (contentEl) contentEl.style.opacity = '1';
            
            if (stats.total_orders === 0) {
                if (emptyEl) emptyEl.hidden = false;
            } else {
                if (emptyEl) emptyEl.hidden = true;
            }
        } catch (error) {
            console.error('[STATISTICS] Error loading statistics:', error);
            if (utils.showToast) utils.showToast('Ошибка загрузки статистики', 'error');
            if (loadingEl) loadingEl.hidden = true;
            if (contentEl) contentEl.style.opacity = '1';
        }
    }
    
    function renderStatisticsCharts(stats) {
        renderRevenueChart(stats.revenue_by_day);
        renderOrdersChart(stats.orders_by_day);
        renderStatusChart(stats.orders_by_status_count);
        renderTopProductsChart(stats.top_products);
    }
    
    function renderRevenueChart(data) {
        const ctx = document.getElementById('revenueChart');
        if (!ctx) return;
        
        if (statisticsCharts.revenue) {
            statisticsCharts.revenue.destroy();
        }
        
        const labels = data.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
        });
        const values = data.map(item => item.revenue);
        
        statisticsCharts.revenue = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Выручка, ₽',
                    data: values,
                    borderColor: '#dbff00',
                    backgroundColor: 'rgba(255, 140, 105, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString('ru-RU') + ' ₽';
                            }
                        }
                    }
                }
            }
        });
    }
    
    function renderOrdersChart(data) {
        const ctx = document.getElementById('ordersChart');
        if (!ctx) return;
        
        if (statisticsCharts.orders) {
            statisticsCharts.orders.destroy();
        }
        
        const labels = data.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
        });
        const values = data.map(item => item.count);
        
        statisticsCharts.orders = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Заказов',
                    data: values,
                    backgroundColor: '#e5ff33',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
    
    function renderStatusChart(data) {
        const ctx = document.getElementById('statusChart');
        if (!ctx) return;
        
        if (statisticsCharts.status) {
            statisticsCharts.status.destroy();
        }
        
        const statusLabels = {
            'pending': 'Ожидают',
            'processing': 'В обработке',
            'delivered': 'Доставлены',
            'cancelled': 'Отменены'
        };
        
        const labels = Object.keys(data).map(key => statusLabels[key] || key);
        const values = Object.values(data);
        const colors = ['#FFA726', '#42A5F5', '#66BB6A', '#EF5350'];
        
        statisticsCharts.status = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, values.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
    
    function renderTopProductsChart(data) {
        const ctx = document.getElementById('topProductsChart');
        if (!ctx) return;
        
        if (statisticsCharts.topProducts) {
            statisticsCharts.topProducts.destroy();
        }
        
        if (!data || data.length === 0) {
            const canvas = ctx.getContext('2d');
            if (canvas) canvas.clearRect(0, 0, ctx.width || 400, ctx.height || 300);
            return;
        }
        
        const top5 = data.slice(0, 5);
        const labels = top5.map(item => {
            const name = item.product_name || 'Неизвестный товар';
            return name.length > 20 ? name.substring(0, 20) + '...' : name;
        });
        const values = top5.map(item => item.total_quantity);
        
        statisticsCharts.topProducts = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Количество продаж',
                    data: values,
                    backgroundColor: '#dbff00',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
    
    function initStatisticsDashboard() {
        document.getElementById('loadStatisticsBtn')?.addEventListener('click', () => {
            loadShopStatistics();
        });
        
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const period = btn.dataset.period;
                const endDate = new Date();
                const startDate = new Date();
                
                if (period === '7') {
                    startDate.setDate(endDate.getDate() - 7);
                } else if (period === '30') {
                    startDate.setDate(endDate.getDate() - 30);
                } else if (period === '90') {
                    startDate.setDate(endDate.getDate() - 90);
                } else if (period === 'month') {
                    startDate.setDate(1);
                }
                
                const startInput = document.getElementById('statisticsStartDate');
                const endInput = document.getElementById('statisticsEndDate');
                
                if (startInput) {
                    startInput.value = startDate.toISOString().split('T')[0];
                }
                if (endInput) {
                    endInput.value = endDate.toISOString().split('T')[0];
                }
                
                loadShopStatistics();
            });
        });
        
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - 30);
        
        const startInput = document.getElementById('statisticsStartDate');
        const endInput = document.getElementById('statisticsEndDate');
        
        if (startInput && !startInput.value) {
            startInput.value = startDate.toISOString().split('T')[0];
        }
        if (endInput && !endInput.value) {
            endInput.value = endDate.toISOString().split('T')[0];
        }
    }
    
    // ==================== Shop Management ====================
    
    async function checkAndShowMyShopButton() {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        
        // Проверяет наличие магазина и показывает/скрывает кнопку 'Мой магазин'.
        console.log('[PROFILE] Checking for shop...');
        console.log('[PROFILE] myShopBtn element:', elements?.myShopBtn);
        
        if (!elements?.myShopBtn) {
            console.error('[PROFILE] ❌ myShopBtn element not found!');
            return;
        }
        
        try {
            const shop = await api.getMyShop();
            console.log('[PROFILE] Shop response:', shop);
            
            // Проверяем, что shop не null и не undefined
            if (shop && typeof shop === 'object' && (shop.id || shop.name)) {
                // Показываем кнопку, если магазин есть
                elements.myShopBtn.removeAttribute('hidden');
                elements.myShopBtn.style.display = '';
                state.myShop = shop; // Сохраняем в state для дальнейшего использования
                console.log('[PROFILE] ✅ Shop found:', shop.name || shop.id);
                console.log('[PROFILE] Button display style:', window.getComputedStyle(elements.myShopBtn).display);
                console.log('[PROFILE] Button hidden attribute:', elements.myShopBtn.hasAttribute('hidden'));
            } else {
                // Скрываем кнопку, если магазина нет
                elements.myShopBtn.setAttribute('hidden', '');
                elements.myShopBtn.style.display = 'none';
                state.myShop = null;
                console.log('[PROFILE] ❌ No shop found, button hidden');
            }
        } catch (error) {
            // Если ошибка (например, 404 - магазин не найден), скрываем кнопку
            console.log('[PROFILE] Error checking shop:', error);
            console.log('[PROFILE] Error details:', {
                message: error.message,
                status: error.status,
                data: error.data
            });
            
            // Если это 404, значит магазина нет - это нормально
            if (error.status === 404) {
                console.log('[PROFILE] Shop not found (404) - this is normal');
                elements.myShopBtn.setAttribute('hidden', '');
                elements.myShopBtn.style.display = 'none';
                state.myShop = null;
            } else {
                // Другая ошибка - показываем в консоли
                console.error('[PROFILE] Unexpected error:', error);
                // Все равно скрываем кнопку при ошибке
                elements.myShopBtn.setAttribute('hidden', '');
                elements.myShopBtn.style.display = 'none';
                state.myShop = null;
            }
        }
    }
    
    async function loadMyShop() {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        const elements = getElements();
        
        console.log('[MY SHOP] Loading shop data...');
        console.log('[MY SHOP] Elements check:', {
            shopBlockedSection: !!elements?.shopBlockedSection,
            shopCreateSection: !!elements?.shopCreateSection,
            shopDashboard: !!elements?.shopDashboard
        });
        
        try {
            state.myShop = await api.getMyShop();
            console.log('[MY SHOP] Shop loaded:', state.myShop);
            console.log('[MY SHOP] Shop is_active:', state.myShop?.is_active, 'Type:', typeof state.myShop?.is_active);
            
            try {
                state.mySubscription = await api.getMySubscription();
                console.log('[MY SHOP] Subscription loaded:', state.mySubscription);
            } catch (subError) {
                console.warn('[MY SHOP] Could not load subscription:', subError);
                state.mySubscription = null;
            }
            
            renderShopPage();
        } catch (error) {
            console.error('[MY SHOP] Error loading shop:', error);
            state.myShop = null;
            state.mySubscription = null;
            renderShopPage();
        }
    }
    
    function renderShopPage() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        
        console.log('[MY SHOP] ========== Rendering shop page ==========');
        console.log('[MY SHOP] Shop data:', state.myShop);
        console.log('[MY SHOP] Elements check:', {
            shopCreateSection: !!elements?.shopCreateSection,
            shopBlockedSection: !!elements?.shopBlockedSection,
            shopDashboard: !!elements?.shopDashboard,
            dashboardShopName: !!elements?.dashboardShopName,
            myShopPage: !!elements?.myShopPage
        });
        
        // Проверяем, что элементы существуют, и находим их если нужно
        if (!elements?.shopBlockedSection) {
            console.warn('[MY SHOP] ⚠️ shopBlockedSection not in elements, trying getElementById...');
            const blockedSection = document.getElementById('shopBlockedSection');
            if (blockedSection) {
                console.log('[MY SHOP] ✅ Found shopBlockedSection via getElementById');
                if (elements) {
                    elements.shopBlockedSection = blockedSection;
                }
            } else {
                console.error('[MY SHOP] ❌ shopBlockedSection not found in DOM!');
                console.error('[MY SHOP] Available elements in myShopPage:', 
                    elements?.myShopPage ? Array.from(elements.myShopPage.children).map(c => c.id || c.className) : 'myShopPage not found');
            }
        } else {
            console.log('[MY SHOP] ✅ shopBlockedSection found in elements');
        }
        
        // Получаем актуальную ссылку на элемент
        const shopBlockedSection = elements?.shopBlockedSection || document.getElementById('shopBlockedSection');
        const shopCreateSection = elements?.shopCreateSection || document.getElementById('shopCreateSection');
        const shopDashboard = elements?.shopDashboard || document.getElementById('shopDashboard');
        
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
        
        if (state.myShop) {
            // Проверяем, заблокирован ли магазин
            // is_active может быть boolean (false) или integer (0) в зависимости от источника данных
            const isActive = state.myShop.is_active;
            // Более надежная проверка: любое falsy значение или явно 0
            const isBlocked = !isActive || isActive === false || isActive === 0 || isActive === '0' || String(isActive).toLowerCase() === 'false';
            
            console.log('[MY SHOP] Shop is_active value:', isActive, 'Type:', typeof isActive, 'Is blocked:', isBlocked);
            console.log('[MY SHOP] Full shop object:', JSON.stringify(state.myShop, null, 2));
            
            if (isBlocked) {
                // Показываем сообщение о блокировке
                console.log('[MY SHOP] ⚠️⚠️⚠️ Shop is BLOCKED, showing blocked message ⚠️⚠️⚠️');
                
                // Скрываем все остальные секции
                if (shopCreateSection) {
                    shopCreateSection.hidden = true;
                    shopCreateSection.style.display = 'none';
                    console.log('[MY SHOP] ✅ shopCreateSection hidden');
                }
                if (shopDashboard) {
                    shopDashboard.hidden = true;
                    shopDashboard.style.display = 'none';
                    console.log('[MY SHOP] ✅ shopDashboard hidden');
                }
                
                // Показываем блокированную секцию
                if (shopBlockedSection) {
                    shopBlockedSection.removeAttribute('hidden');
                    shopBlockedSection.hidden = false;
                    shopBlockedSection.style.display = 'block';
                    shopBlockedSection.style.visibility = 'visible';
                    console.log('[MY SHOP] ✅✅✅ shopBlockedSection SHOWN (hidden=false, display=block)');
                    console.log('[MY SHOP] Blocked section computed style:', window.getComputedStyle(shopBlockedSection).display);
                } else {
                    console.error('[MY SHOP] ❌❌❌ shopBlockedSection element STILL NOT FOUND!');
                    // Создаем временное сообщение, если элемент не найден
                    const myShopPage = elements?.myShopPage || document.getElementById('myShopPage');
                    if (myShopPage) {
                        const tempMsg = document.createElement('div');
                        tempMsg.className = 'shop-blocked-section';
                        tempMsg.id = 'shopBlockedSection';
                        tempMsg.innerHTML = `
                            <div class="blocked-message">
                                <div class="blocked-icon">🚫</div>
                                <h2>Магазин заблокирован</h2>
                                <p>Ваш магазин был заблокирован администратором.</p>
                                <p>Для получения дополнительной информации и решения вопроса, пожалуйста, обратитесь в поддержку.</p>
                                <button class="support-btn" id="contactSupportBtn">
                                    <span>Связаться с поддержкой</span>
                                </button>
                            </div>
                        `;
                        myShopPage.appendChild(tempMsg);
                        console.log('[MY SHOP] Created temporary blocked message element');
                        // Инициализируем обработчик для кнопки
                        const supportBtn = tempMsg.querySelector('#contactSupportBtn');
                        if (supportBtn) {
                            supportBtn.addEventListener('click', () => {
                                const supportUrl = 'https://t.me/daribri_support';
                                if (window.Telegram?.WebApp?.openTelegramLink) {
                                    window.Telegram.WebApp.openTelegramLink(supportUrl);
                                } else if (window.Telegram?.WebApp?.openLink) {
                                    window.Telegram.WebApp.openLink(supportUrl);
                                } else {
                                    window.open(supportUrl, '_blank');
                                }
                            });
                        }
                    }
                }
                return;
            }
            
            // Показываем панель управления (магазин не заблокирован)
            console.log('[MY SHOP] ✅ Shop is ACTIVE, showing dashboard');
            if (shopCreateSection) {
                shopCreateSection.hidden = true;
                shopCreateSection.style.display = 'none';
            }
            if (shopBlockedSection) {
                shopBlockedSection.hidden = true;
                shopBlockedSection.style.display = 'none';
            }
            if (shopDashboard) {
                shopDashboard.hidden = false;
                shopDashboard.style.display = 'block';
            }
            
            // Заполняем данные магазина
            if (elements?.dashboardShopName) elements.dashboardShopName.textContent = state.myShop.name || 'Магазин';
            if (elements?.dashboardShopRating) elements.dashboardShopRating.textContent = state.myShop.average_rating || '0.0';
            if (elements?.dashboardReviewsCount) elements.dashboardReviewsCount.textContent = state.myShop.total_reviews || state.myShop.reviews_count || 0;
            if (elements?.dashboardProductsCount) elements.dashboardProductsCount.textContent = state.myShop.products_count || 0;
            if (elements?.dashboardOrdersCount) elements.dashboardOrdersCount.textContent = state.myShop.orders_count || 0;
            if (elements?.dashboardRedemptionRate) elements.dashboardRedemptionRate.textContent = (state.myShop.redemption_rate || 0) + '%';
            
            if (elements?.dashboardShopPhoto) {
                if (state.myShop.photo_url) {
                    const photoUrl = getMediaUrl(state.myShop.photo_url);
                    elements.dashboardShopPhoto.innerHTML = `<img src="${photoUrl}" alt="${state.myShop.name}">`;
                } else {
                    elements.dashboardShopPhoto.innerHTML = '<div style="font-size: 4rem;">🏪</div>';
                }
            }
            
            // Подписка
            if (elements?.subscriptionInfo && elements?.noSubscription && elements?.subscriptionStatus) {
                if (state.mySubscription && state.mySubscription.is_active) {
                    elements.subscriptionInfo.hidden = false;
                    elements.noSubscription.hidden = true;
                    elements.subscriptionStatus.textContent = 'Активна';
                    elements.subscriptionStatus.className = 'subscription-status active';
                    if (elements.currentPlanName) elements.currentPlanName.textContent = state.mySubscription.plan_name || 'Подписка';
                    if (elements.daysRemaining) elements.daysRemaining.textContent = state.mySubscription.days_remaining || 0;
                } else {
                    elements.subscriptionInfo.hidden = true;
                    elements.noSubscription.hidden = false;
                    elements.subscriptionStatus.textContent = 'Неактивна';
                    elements.subscriptionStatus.className = 'subscription-status inactive';
                }
            }
        } else {
            // Показываем форму создания
            if (elements?.shopCreateSection) elements.shopCreateSection.hidden = false;
            if (elements?.shopDashboard) elements.shopDashboard.hidden = true;
        }
    }
    
    async function handleCreateShop(e) {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        const utils = getUtils();
        
        e.preventDefault();
        
        const name = elements?.shopName?.value?.trim();
        const description = elements?.shopDescription?.value?.trim();
        const address = elements?.shopAddress?.value?.trim();
        const phone = elements?.shopPhone?.value?.trim();
        const email = elements?.shopEmail?.value?.trim();
        
        if (!name) {
            if (utils.showToast) utils.showToast('Введите название магазина', 'error');
            return;
        }
        
        // Показываем загрузку
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn?.textContent;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Создание...';
        }
        
        try {
            // Подготавливаем данные (убираем пустые строки)
            const shopData = {
                name,
                description: description || null,
                address: address || null,
                phone: phone || null,
                email: email || null
            };
            
            console.log('Creating shop with data:', shopData);
            
            const shop = await api.createShop(shopData);
            
            state.myShop = shop;
            if (utils.showToast) utils.showToast('✅ Магазин успешно создан!', 'success');
            renderShopPage();
            
            // Показываем кнопку "Мой магазин" в профиле
            await checkAndShowMyShopButton();
            
            // Очищаем форму
            if (elements?.shopCreateForm) elements.shopCreateForm.reset();
            if (elements?.shopPhotoPreview) {
                elements.shopPhotoPreview.innerHTML = '<span>📷</span><p>Нажмите для загрузки</p>';
            }
        } catch (error) {
            console.error('Error creating shop:', error);
            
            // Улучшенная обработка ошибок
            let errorMessage = 'Ошибка создания магазина';
            if (error.message) {
                if (error.message.includes('already has a shop')) {
                    errorMessage = 'У вас уже есть магазин';
                } else if (error.message.includes('not found') || error.message.includes('404')) {
                    errorMessage = 'Сервер недоступен. Проверьте, что сервер запущен.';
                } else if (error.message.includes('required') || error.message.includes('missing')) {
                    errorMessage = 'Заполните обязательные поля';
                } else {
                    errorMessage = error.message;
                }
            }
            
            if (utils.showToast) utils.showToast(errorMessage, 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }
    
    // ==================== Shop Editing ====================
    
    function openEditShopModal() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        
        if (!state.myShop) return;
        
        document.getElementById('editShopName').value = state.myShop.name || '';
        document.getElementById('editShopDescription').value = state.myShop.description || '';
        document.getElementById('editShopAddress').value = state.myShop.address || '';
        document.getElementById('editShopPhone').value = state.myShop.phone || '';
        document.getElementById('editShopEmail').value = state.myShop.email || '';
        
        // Отображаем текущее фото магазина
        const editShopPhotoPreview = document.getElementById('editShopPhotoPreview');
        const editShopPhoto = document.getElementById('editShopPhoto');
        
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
        
        if (editShopPhotoPreview) {
            if (state.myShop.photo_url) {
                const photoUrl = getMediaUrl(state.myShop.photo_url);
                editShopPhotoPreview.innerHTML = `<img src="${photoUrl}" alt="Shop photo">`;
            } else {
                editShopPhotoPreview.innerHTML = '<span>📷</span><p>Нажмите для загрузки</p>';
            }
        }
        
        // Сбрасываем выбор файла
        if (editShopPhoto) {
            editShopPhoto.value = '';
        }
        
        if (elements?.editShopModal) {
            elements.editShopModal.hidden = false;
        }
    }
    
    async function handleUpdateShop(e) {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        const utils = getUtils();
        
        e.preventDefault();
        
        const name = document.getElementById('editShopName')?.value?.trim();
        const description = document.getElementById('editShopDescription')?.value?.trim();
        const addressInput = document.getElementById('editShopAddress');
        const address = addressInput?.value?.trim() || '';
        const phone = document.getElementById('editShopPhone')?.value?.trim();
        const email = document.getElementById('editShopEmail')?.value?.trim();
        const editShopPhoto = document.getElementById('editShopPhoto');
        
        console.log('[SHOP UPDATE] Form values:', {
            name,
            description,
            address,
            phone,
            email,
            addressInputValue: addressInput?.value,
            addressInputExists: !!addressInput
        });
        
        try {
            // Сначала загружаем фото, если оно выбрано
            let photoUrl = state.myShop?.photo_url;
            if (editShopPhoto && editShopPhoto.files && editShopPhoto.files[0]) {
                console.log('[SHOP] Uploading shop photo...');
                const photoResponse = await api.uploadShopPhoto(state.myShop.id, editShopPhoto.files[0]);
                photoUrl = photoResponse.photo_url;
                console.log('[SHOP] Photo uploaded, new URL:', photoUrl);
            }
            
            // Обновляем данные магазина (включая photo_url если была загрузка)
            const updateData = {
                name,
                description,
                address: address || null,  // Явно передаем null если пусто
                phone: phone || null,
                email: email || null
            };
            
            console.log('[SHOP UPDATE] Sending update data:', updateData);
            
            // Если фото было загружено, добавляем photo_url к данным обновления
            if (photoUrl !== state.myShop?.photo_url) {
                updateData.photo_url = photoUrl;
            }
            
            const shop = await api.updateShop(state.myShop.id, updateData);
            console.log('[SHOP UPDATE] Server response:', shop);
            
            state.myShop = { ...state.myShop, ...shop };
            if (utils.showToast) utils.showToast('Магазин обновлён', 'success');
            if (elements?.editShopModal) elements.editShopModal.hidden = true;
            renderShopPage();
            
            // Перезагружаем данные магазина, если открыта страница магазина
            if (state.currentShopId === state.myShop.id) {
                console.log('[SHOP UPDATE] Reloading shop page data...');
                try {
                    if (window.loadShopData && typeof window.loadShopData === 'function') {
                        await window.loadShopData(state.myShop.id);
                    } else if (window.App?.shop?.loadShopData) {
                        await window.App.shop.loadShopData(state.myShop.id);
                    }
                } catch (error) {
                    console.error('[SHOP UPDATE] Error reloading shop page:', error);
                }
            }
            
            // Обновляем данные в checkout, если checkout открыт
            const checkoutState = window.checkoutState;
            if (checkoutState && checkoutState.shopId === state.myShop.id) {
                console.log('[SHOP UPDATE] Updating checkout shop data...');
                try {
                    // Обновляем данные магазина в checkout
                    checkoutState.shopCity = 'Екатеринбург'; // Всегда Екатеринбург
                    checkoutState.shopAddress = shop.address || null;
                    checkoutState.shopLatitude = shop.latitude || null;
                    checkoutState.shopLongitude = shop.longitude || null;
                    
                    // Если открыт шаг 2 (адрес) и выбран самовывоз, обновляем отображение
                    if (checkoutState.step === 2 && checkoutState.deliveryType === 'pickup') {
                        const shopAddressText = document.getElementById('shopAddressText');
                        if (shopAddressText && checkoutState.shopAddress) {
                            // Нормализуем адрес для отображения
                            const normalizedAddress = normalizeShopAddress(checkoutState.shopAddress);
                            shopAddressText.textContent = normalizedAddress;
                        }
                    }
                } catch (error) {
                    console.error('[SHOP UPDATE] Error updating checkout data:', error);
                }
            }
        } catch (error) {
            console.error('Error updating shop:', error);
            let errorMessage = 'Ошибка обновления';
            if (error.message) {
                if (error.message.includes('файл слишком большой')) {
                    errorMessage = 'Файл слишком большой (максимум 5MB)';
                } else if (error.message.includes('неподдерживаемый тип')) {
                    errorMessage = 'Неподдерживаемый тип файла. Используйте изображение (JPG, PNG, WebP)';
                } else {
                    errorMessage = error.message;
                }
            }
            if (utils.showToast) utils.showToast(errorMessage, 'error');
        }
    }
    
    // ==================== Shop Products ====================
    
    async function loadMyProducts() {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        console.log('[MY PRODUCTS] Loading products...');
        
        // Если магазин не загружен, загружаем его
        if (!state.myShop) {
            console.log('[MY PRODUCTS] Shop not loaded, loading now...');
            try {
                state.myShop = await api.getMyShop();
                console.log('[MY PRODUCTS] Shop loaded:', state.myShop);
            } catch (error) {
                console.error('[MY PRODUCTS] Error loading shop:', error);
                if (utils.showToast) utils.showToast('Магазин не найден', 'error');
                return;
            }
        }
        
        if (!state.myShop) {
            console.error('[MY PRODUCTS] Shop not found!');
            return;
        }
        
        try {
            console.log('[MY PRODUCTS] Loading products for shop:', state.myShop.id);
            const products = await api.request(`/shops/${state.myShop.id}/products`);
            console.log('[MY PRODUCTS] Loaded products:', products.length, 'items');
            // Убеждаемся, что is_active определено (может быть 0 или 1 в базе данных)
            state.myProducts = products.map(p => ({
                ...p,
                is_active: p.is_active !== 0 && p.is_active !== false // Нормализуем к boolean
            }));
            renderMyProducts();
        } catch (error) {
            console.error('[MY PRODUCTS] Error loading products:', error);
            state.myProducts = [];
            renderMyProducts();
        }
    }
    
    function renderMyProducts() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        
        console.log('[MY PRODUCTS] Rendering products:', state.myProducts?.length || 0);
        console.log('[MY PRODUCTS] Elements:', { 
            myProductsList: !!elements?.myProductsList, 
            myProductsEmpty: !!elements?.myProductsEmpty 
        });
        
        if (!elements?.myProductsList || !elements?.myProductsEmpty) {
            console.error('[MY PRODUCTS] Required elements not found!');
            return;
        }
        
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
        
        if (!state.myProducts || state.myProducts.length === 0) {
            elements.myProductsList.innerHTML = '';
            elements.myProductsEmpty.hidden = false;
            return;
        }
        
        elements.myProductsEmpty.hidden = true;
        
        elements.myProductsList.innerHTML = state.myProducts.map(product => {
            const isActive = product.is_active !== false;
            const hasDiscount = product.discount_price && product.discount_price < product.price;
            const isOutOfStock = (product.quantity || 0) === 0;
            const mediaCount = product.media ? product.media.length : (product.primary_image ? 1 : 0);
            
            // Получаем URL изображения: сначала primary_image, потом первое из media, потом пусто
            let imageUrl = '';
            if (product.primary_image) {
                imageUrl = getMediaUrl(product.primary_image);
            } else if (product.media && Array.isArray(product.media) && product.media.length > 0) {
                // Ищем первое изображение (не видео)
                const firstImage = product.media.find(m => m.media_type !== 'video') || product.media[0];
                if (firstImage && firstImage.url) {
                    imageUrl = getMediaUrl(firstImage.url);
                }
            }
            
            console.log('[MY PRODUCTS] Product image:', {
                id: product.id,
                name: product.name,
                primary_image: product.primary_image,
                media_count: product.media?.length || 0,
                imageUrl: imageUrl
            });
            
            return `
            <div class="my-product-item ${!isActive ? 'inactive' : ''} ${isOutOfStock ? 'out-of-stock' : ''}" data-product-id="${product.id}">
                <div class="my-product-image">
                    ${imageUrl 
                        ? `<img src="${imageUrl}" alt="${product.name}" loading="lazy">`
                        : '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:1.5rem;background:var(--bg-tertiary);">🌸</div>'
                    }
                    ${!isActive ? '<div class="product-status-badge inactive-badge">Неактивен</div>' : ''}
                    ${isOutOfStock ? '<div class="product-status-badge stock-badge">Нет в наличии</div>' : ''}
                    ${mediaCount > 0 ? `<div class="product-media-count">📷 ${mediaCount}</div>` : ''}
                </div>
                <div class="my-product-info">
                    <div class="my-product-header">
                        <div class="my-product-name" title="${product.name}">${product.name}</div>
                        ${product.is_trending ? '<span class="trending-badge">🔥</span>' : ''}
                    </div>
                    <div class="my-product-price-row">
                        ${hasDiscount 
                            ? `<span class="my-product-price discount">${formatPrice(product.discount_price)}</span>
                               <span class="my-product-price-old">${formatPrice(product.price)}</span>`
                            : `<span class="my-product-price">${formatPrice(product.price)}</span>`
                        }
                    </div>
                    <div class="my-product-stats">
                        <span title="Просмотры">👁 ${product.views_count || 0}</span>
                        <span title="Продажи">🛒 ${product.sales_count || 0}</span>
                        <span class="${isOutOfStock ? 'text-danger' : ''}" title="Количество">📦 ${product.quantity || 0} шт</span>
                    </div>
                </div>
                <div class="my-product-actions">
                    <button data-product-id="${product.id}" data-action="edit" title="Редактировать" class="action-btn edit-btn" type="button">✏️</button>
                    <button data-product-id="${product.id}" data-action="toggle" data-current-status="${isActive}" 
                            title="${isActive ? 'Деактивировать' : 'Активировать'}" 
                            class="action-btn status-btn ${isActive ? 'active' : ''}" type="button">
                        ${isActive ? '👁️' : '👁️‍🗨️'}
                    </button>
                    <button data-product-id="${product.id}" data-action="delete" title="Удалить" class="action-btn delete-btn" type="button">🗑️</button>
                </div>
            </div>
            `;
        }).join('');
        
        // Добавляем обработчики событий для кнопок действий (используем делегирование)
        elements.myProductsList.querySelectorAll('[data-action]').forEach(button => {
            // Удаляем старые обработчики перед добавлением новых
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            newButton.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                const productId = parseInt(newButton.dataset.productId);
                const action = newButton.dataset.action;
                
                console.log('[MY PRODUCTS] Button clicked:', action, 'productId:', productId);
                
                if (!productId || isNaN(productId)) {
                    console.error('[MY PRODUCTS] Invalid product ID:', newButton.dataset.productId);
                    if (utils.showToast) utils.showToast('Ошибка: неверный ID товара', 'error');
                    return;
                }
                
                switch (action) {
                    case 'edit':
                        editProduct(productId);
                        break;
                    case 'toggle':
                        const currentStatus = newButton.dataset.currentStatus === 'true';
                        toggleProductStatus(productId, currentStatus);
                        break;
                    case 'delete':
                        deleteProduct(productId);
                        break;
                }
            });
        });
    }
    
    async function editProduct(productId) {
        const utils = getUtils();
        
        // Проверяем, что ID валидный
        if (!productId || isNaN(productId)) {
            console.error('[EDIT] Invalid product ID:', productId);
            if (utils.showToast) utils.showToast('Ошибка: неверный ID товара', 'error');
            return;
        }
        
        console.log('[EDIT] Opening edit modal for product:', productId);
        // Используем глобальную функцию openAddProductModal из app.js
        if (typeof window.openAddProductModal === 'function') {
            await window.openAddProductModal(parseInt(productId));
        } else {
            console.error('[EDIT] openAddProductModal not available');
            if (utils.showToast) utils.showToast('Функция редактирования недоступна', 'error');
        }
    }
    
    async function toggleProductStatus(productId, currentStatus) {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        // Проверяем, что ID валидный
        if (!productId || isNaN(productId)) {
            console.error('[TOGGLE] Invalid product ID:', productId);
            if (utils.showToast) utils.showToast('Ошибка: неверный ID товара', 'error');
            return;
        }
        
        try {
            const newStatus = !currentStatus;
            console.log('[TOGGLE] Toggling product status:', productId, 'to', newStatus);
            await api.request(`/products/${productId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: newStatus })
            });
            
            if (utils.showToast) utils.showToast(newStatus ? 'Товар активирован' : 'Товар деактивирован', 'success');
            await loadMyProducts();
            await loadMyShop();
        } catch (error) {
            console.error('[TOGGLE] Error toggling product status:', error);
            if (utils.showToast) utils.showToast('Ошибка изменения статуса', 'error');
        }
    }
    
    async function deleteProduct(productId) {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        // Проверяем, что ID валидный
        if (!productId || isNaN(productId)) {
            console.error('[DELETE] Invalid product ID:', productId);
            if (utils.showToast) utils.showToast('Ошибка: неверный ID товара', 'error');
            return;
        }
        
        if (!confirm('Удалить этот товар?\n\nЭто действие нельзя отменить. Товар будет полностью удален из базы данных.')) return;
        
        try {
            console.log('[DELETE] Deleting product:', productId);
            await api.request(`/products/${productId}`, { method: 'DELETE' });
            if (utils.showToast) utils.showToast('Товар удалён', 'success');
            // Обновляем список товаров и статистику магазина
            await loadMyProducts();
            // Перезагружаем данные магазина, чтобы обновился счетчик товаров
            await loadMyShop();
        } catch (error) {
            console.error('[DELETE] Error deleting product:', error);
            if (utils.showToast) utils.showToast('Ошибка удаления: ' + (error.message || 'Неизвестная ошибка'), 'error');
        }
    }
    
    // ==================== Shop Reviews ====================
    
    async function loadShopReviewsPage() {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        console.log('[SHOP REVIEWS] Loading shop reviews...');
        
        // Если магазин не загружен, загружаем его
        if (!state.myShop) {
            console.log('[SHOP REVIEWS] Shop not loaded, loading now...');
            try {
                state.myShop = await api.getMyShop();
                console.log('[SHOP REVIEWS] Shop loaded:', state.myShop);
            } catch (error) {
                console.error('[SHOP REVIEWS] Error loading shop:', error);
                if (utils.showToast) utils.showToast('Магазин не найден', 'error');
                return;
            }
        }
        
        if (!state.myShop) {
            console.error('[SHOP REVIEWS] Shop not found!');
            if (utils.showToast) utils.showToast('Магазин не найден', 'error');
            return;
        }
        
        const reviewsList = document.getElementById('shopReviewsListFull');
        const reviewsEmpty = document.getElementById('shopReviewsEmptyFull');
        const statsCard = document.getElementById('reviewsStatsCard');
        
        console.log('[SHOP REVIEWS] Shop ID:', state.myShop.id);
        console.log('[SHOP REVIEWS] Elements:', { reviewsList: !!reviewsList, reviewsEmpty: !!reviewsEmpty, statsCard: !!statsCard });
        
        try {
            // Загружаем статистику отзывов
            console.log('[SHOP REVIEWS] Loading stats...');
            const stats = await api.request(`/reviews/shop/${state.myShop.id}/stats`);
            console.log('[SHOP REVIEWS] Stats received:', stats);
            renderReviewsStats(stats);
            
            // Загружаем отзывы
            console.log('[SHOP REVIEWS] Loading reviews...');
            const reviews = await api.getShopReviews(state.myShop.id, { limit: 100 });
            console.log('[SHOP REVIEWS] Reviews received:', reviews.length, 'items');
            
            if (reviews.length === 0) {
                if (reviewsList) reviewsList.innerHTML = '';
                if (reviewsEmpty) reviewsEmpty.hidden = false;
            } else {
                if (reviewsEmpty) reviewsEmpty.hidden = true;
                if (reviewsList) {
                    reviewsList.innerHTML = reviews.map(review => renderShopReviewCard(review)).join('');
                }
            }
        } catch (error) {
            console.error('Error loading shop reviews:', error);
            if (utils.showToast) utils.showToast('Ошибка загрузки отзывов', 'error');
            if (reviewsEmpty) reviewsEmpty.hidden = false;
        }
    }
    
    function renderReviewsStats(stats) {
        const averageRating = parseFloat(stats.average || 0).toFixed(1);
        const totalReviews = stats.total || 0;
        
        const averageRatingEl = document.getElementById('reviewsAverageRating');
        const starsDisplayEl = document.getElementById('reviewsStarsDisplay');
        const totalCountEl = document.getElementById('reviewsTotalCount');
        const breakdownEl = document.getElementById('reviewsRatingBreakdown');
        
        if (averageRatingEl) averageRatingEl.textContent = averageRating;
        if (totalCountEl) {
            const pluralize = (count, one, few, many) => {
                const mod10 = count % 10;
                const mod100 = count % 100;
                if (mod100 >= 11 && mod100 <= 19) return many;
                if (mod10 === 1) return one;
                if (mod10 >= 2 && mod10 <= 4) return few;
                return many;
            };
            totalCountEl.textContent = `${totalReviews} ${pluralize(totalReviews, 'отзыв', 'отзыва', 'отзывов')}`;
        }
        
        if (starsDisplayEl) {
            const fullStars = Math.round(parseFloat(averageRating));
            starsDisplayEl.innerHTML = '⭐'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
        }
        
        if (breakdownEl && totalReviews > 0) {
            breakdownEl.innerHTML = `
                <div class="rating-bar" data-rating="5">
                    <span class="rating-label">5 ⭐</span>
                    <div class="rating-bar-container">
                        <div class="rating-bar-fill" style="width: ${((stats.five_star || 0) / totalReviews * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="rating-count">${stats.five_star || 0}</span>
                </div>
                <div class="rating-bar" data-rating="4">
                    <span class="rating-label">4 ⭐</span>
                    <div class="rating-bar-container">
                        <div class="rating-bar-fill" style="width: ${((stats.four_star || 0) / totalReviews * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="rating-count">${stats.four_star || 0}</span>
                </div>
                <div class="rating-bar" data-rating="3">
                    <span class="rating-label">3 ⭐</span>
                    <div class="rating-bar-container">
                        <div class="rating-bar-fill" style="width: ${((stats.three_star || 0) / totalReviews * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="rating-count">${stats.three_star || 0}</span>
                </div>
                <div class="rating-bar" data-rating="2">
                    <span class="rating-label">2 ⭐</span>
                    <div class="rating-bar-container">
                        <div class="rating-bar-fill" style="width: ${((stats.two_star || 0) / totalReviews * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="rating-count">${stats.two_star || 0}</span>
                </div>
                <div class="rating-bar" data-rating="1">
                    <span class="rating-label">1 ⭐</span>
                    <div class="rating-bar-container">
                        <div class="rating-bar-fill" style="width: ${((stats.one_star || 0) / totalReviews * 100).toFixed(0)}%"></div>
                    </div>
                    <span class="rating-count">${stats.one_star || 0}</span>
                </div>
            `;
        } else if (breakdownEl) {
            breakdownEl.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">Нет данных</p>';
        }
    }
    
    function renderShopReviewCard(review) {
        const reviewDate = new Date(review.created_at);
        const dateStr = reviewDate.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        
        return `
            <div class="shop-review-card-full">
                <div class="review-header">
                    <div class="review-author">
                        <span class="author-avatar">${review.user_name ? review.user_name.charAt(0).toUpperCase() : 'П'}</span>
                        <div class="author-info">
                            <div class="author-name">${review.user_name || 'Пользователь'}</div>
                            <div class="review-date">${dateStr}</div>
                        </div>
                    </div>
                    <div class="review-rating-display">
                        ${'⭐'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}
                    </div>
                </div>
                ${review.comment ? `<div class="review-comment">${review.comment}</div>` : ''}
                ${review.is_verified ? '<div class="review-verified">✓ Проверенная покупка</div>' : ''}
            </div>
        `;
    }
    
    // ==================== Subscription Management ====================
    
    async function loadSubscriptionManagement() {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        const utils = getUtils();
        
        try {
            // Загружаем текущую подписку
            const subscription = await api.getMySubscription();
            
            if (subscription) {
                renderSubscriptionManagementInfo(subscription);
                if (elements?.subscriptionLimitsCard) elements.subscriptionLimitsCard.hidden = false;
                
                // Загружаем статистику использования
                await loadSubscriptionUsage();
            } else {
                // Нет активной подписки
                renderNoSubscription();
                if (elements?.subscriptionLimitsCard) elements.subscriptionLimitsCard.hidden = true;
            }
            
            // Загружаем историю
            await loadSubscriptionHistory();
            
        } catch (error) {
            console.error('Error loading subscription management:', error);
            if (utils.showToast) utils.showToast('Ошибка загрузки данных подписки', 'error');
        }
    }
    
    async function loadSubscriptionUsage() {
        const elements = getElements();
        const api = getApi();
        
        try {
            const usage = await api.getSubscriptionUsage();
            
            // Обновляем использование товаров
            if (elements?.productsUsage && elements?.productsLimitFill) {
                const productsPercent = usage.max_products > 0 
                    ? Math.min(100, (usage.products_count / usage.max_products) * 100) 
                    : 0;
                elements.productsUsage.textContent = `${usage.products_count} / ${usage.max_products}`;
                elements.productsLimitFill.style.width = `${productsPercent}%`;
            }
            
            // Обновляем использование промо
            if (elements?.promotionsUsage && elements?.promotionsLimitFill) {
                const promotionsPercent = usage.max_promotions > 0 
                    ? Math.min(100, (usage.promotions_count / usage.max_promotions) * 100) 
                    : 0;
                elements.promotionsUsage.textContent = `${usage.promotions_count} / ${usage.max_promotions}`;
                elements.promotionsLimitFill.style.width = `${promotionsPercent}%`;
            }
            
        } catch (error) {
            console.error('Error loading subscription usage:', error);
        }
    }
    
    function renderSubscriptionManagementInfo(subscription) {
        const elements = getElements();
        const utils = getUtils();
        
        if (!subscription) {
            console.warn('[SUBSCRIPTION] renderSubscriptionManagementInfo called with undefined subscription');
            return;
        }
        
        if (!subscription.start_date) {
            console.warn('[SUBSCRIPTION] renderSubscriptionManagementInfo: subscription has no start_date', subscription);
            return;
        }
        
        if (!elements?.subscriptionStatusBadge || !elements?.managementPlanName) {
            console.warn('[SUBSCRIPTION] renderSubscriptionManagementInfo: required DOM elements not found');
            return;
        }
        
        const pluralize = utils.pluralize || ((count, one, few, many) => {
            const mod10 = count % 10;
            const mod100 = count % 100;
            if (mod100 >= 11 && mod100 <= 19) return many;
            if (mod10 === 1) return one;
            if (mod10 >= 2 && mod10 <= 4) return few;
            return many;
        });
        
        const formatDateObject = (date) => {
            if (!date) return '';
            return new Intl.DateTimeFormat('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }).format(date);
        };
        
        const startDate = new Date(subscription.start_date);
        const endDate = new Date(subscription.end_date);
        const now = new Date();
        const totalDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
        const remainingDays = Math.max(0, Math.ceil((endDate - now) / (1000 * 60 * 60 * 24)));
        const progress = totalDays > 0 ? ((totalDays - remainingDays) / totalDays * 100) : 0;
        
        // Статус
        const statusText = remainingDays > 0 ? 'Активна' : 'Истекла';
        const statusClass = remainingDays > 0 ? 'active' : 'expired';
        if (elements.subscriptionStatusBadge) {
            elements.subscriptionStatusBadge.textContent = statusText;
            elements.subscriptionStatusBadge.className = `subscription-status-badge ${statusClass}`;
        }
        
        // План
        if (elements.managementPlanName) {
            elements.managementPlanName.textContent = subscription.plan_name || 'План';
        }
        
        // Даты
        if (elements.subscriptionStartDate) {
            elements.subscriptionStartDate.textContent = formatDateObject(startDate);
        }
        if (elements.subscriptionEndDate) {
            elements.subscriptionEndDate.textContent = formatDateObject(endDate);
        }
        if (elements.subscriptionDaysRemaining) {
            elements.subscriptionDaysRemaining.textContent = `${remainingDays} ${pluralize(remainingDays, 'день', 'дня', 'дней')}`;
        }
        
        // Прогресс
        if (elements.subscriptionProgressFill) {
            elements.subscriptionProgressFill.style.width = `${Math.min(100, progress)}%`;
        }
    }
    
    function renderNoSubscription() {
        const elements = getElements();
        
        if (elements?.subscriptionStatusBadge) {
            elements.subscriptionStatusBadge.textContent = 'Нет подписки';
            elements.subscriptionStatusBadge.className = 'subscription-status-badge inactive';
        }
        if (elements?.managementPlanName) elements.managementPlanName.textContent = '—';
        if (elements?.subscriptionStartDate) elements.subscriptionStartDate.textContent = '—';
        if (elements?.subscriptionEndDate) elements.subscriptionEndDate.textContent = '—';
        if (elements?.subscriptionDaysRemaining) elements.subscriptionDaysRemaining.textContent = '0 дней';
        if (elements?.subscriptionProgressFill) elements.subscriptionProgressFill.style.width = '0%';
    }
    
    async function loadSubscriptionHistory() {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        
        try {
            const history = await api.getSubscriptionHistory();
            
            if (!elements?.subscriptionHistoryList || !elements?.subscriptionHistoryEmpty) {
                console.error('[SUBSCRIPTION] History elements not found');
                return;
            }
            
            if (history.length === 0) {
                elements.subscriptionHistoryList.innerHTML = '';
                elements.subscriptionHistoryEmpty.hidden = false;
                return;
            }
            
            elements.subscriptionHistoryEmpty.hidden = true;
            
            const formatDateObject = (date) => {
                if (!date) return '';
                return new Intl.DateTimeFormat('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                }).format(date);
            };
            
            // Показываем только последние 3 по умолчанию
            const showAll = state.showAllSubscriptionHistory || false;
            const displayHistory = showAll ? history : history.slice(0, 3);
            
            elements.subscriptionHistoryList.innerHTML = displayHistory.map(sub => {
                const startDate = new Date(sub.start_date);
                const endDate = new Date(sub.end_date);
                const now = new Date();
                const isActive = sub.is_active && endDate > now;
                const isExpired = endDate < now;
                
                return `
                    <div class="history-item ${isActive ? 'active' : isExpired ? 'expired' : ''}">
                        <div class="history-item-header">
                            <span class="history-plan-name">${sub.plan_name}</span>
                            <span class="history-status ${isActive ? 'active' : isExpired ? 'expired' : 'inactive'}">
                                ${isActive ? 'Активна' : isExpired ? 'Истекла' : 'Неактивна'}
                            </span>
                        </div>
                        <div class="history-item-dates">
                            <span>${formatDateObject(startDate)} — ${formatDateObject(endDate)}</span>
                        </div>
                        <div class="history-item-payment">
                            <span>ID: ${sub.payment_id || 'N/A'}</span>
                        </div>
                    </div>
                `;
            }).join('');
            
            // Кнопка "Показать все"
            if (elements?.showAllHistoryBtn) {
                if (history.length > 3) {
                    elements.showAllHistoryBtn.hidden = false;
                    elements.showAllHistoryBtn.textContent = showAll ? 'Скрыть' : `Показать все (${history.length})`;
                } else {
                    elements.showAllHistoryBtn.hidden = true;
                }
            }
            
        } catch (error) {
            console.error('Error loading subscription history:', error);
            if (elements?.subscriptionHistoryList) elements.subscriptionHistoryList.innerHTML = '';
            if (elements?.subscriptionHistoryEmpty) elements.subscriptionHistoryEmpty.hidden = false;
        }
    }
    
    function initSubscriptionManagementHandlers() {
        const state = getState();
        const elements = getElements();
        
        // Показать всю историю
        elements?.showAllHistoryBtn?.addEventListener('click', () => {
            state.showAllSubscriptionHistory = !state.showAllSubscriptionHistory;
            loadSubscriptionHistory();
        });
    }
    
    function initShopBlockedHandlers() {
        const elements = getElements();
        
        // Кнопка "Связаться с поддержкой"
        elements?.contactSupportBtn?.addEventListener('click', () => {
            // Открываем поддержку через Telegram
            const supportUrl = 'https://t.me/daribri_support';
            if (window.Telegram && window.Telegram.WebApp) {
                if (window.Telegram.WebApp.openTelegramLink) {
                    window.Telegram.WebApp.openTelegramLink(supportUrl);
                } else if (window.Telegram.WebApp.openLink) {
                    window.Telegram.WebApp.openLink(supportUrl);
                } else {
                    // Fallback: открываем в новом окне
                    window.open(supportUrl, '_blank');
                }
            } else {
                // Если не в Telegram WebApp, открываем в новом окне
                window.open(supportUrl, '_blank');
            }
        });
    }
    
    // Экспорт функций
    window.App = window.App || {};
    window.App.myshop = {
        // Statistics
        loadShopStatistics,
        renderStatisticsCharts,
        renderRevenueChart,
        renderOrdersChart,
        renderStatusChart,
        renderTopProductsChart,
        initStatisticsDashboard,
        // Shop Management
        checkAndShowMyShopButton,
        loadMyShop,
        renderShopPage,
        handleCreateShop,
        // Shop Editing
        openEditShopModal,
        handleUpdateShop,
        // Shop Products
        loadMyProducts,
        renderMyProducts,
        editProduct,
        toggleProductStatus,
        deleteProduct,
        // Shop Reviews
        loadShopReviewsPage,
        renderReviewsStats,
        renderShopReviewCard,
        // Subscription Management
        loadSubscriptionManagement,
        loadSubscriptionUsage,
        renderSubscriptionManagementInfo,
        renderNoSubscription,
        loadSubscriptionHistory,
        initSubscriptionManagementHandlers
    };
    
    // Глобальный экспорт для обратной совместимости
    window.loadShopStatistics = loadShopStatistics;
    window.renderStatisticsCharts = renderStatisticsCharts;
    window.initStatisticsDashboard = initStatisticsDashboard;
    window.checkAndShowMyShopButton = checkAndShowMyShopButton;
    window.loadMyShop = loadMyShop;
    window.renderShopPage = renderShopPage;
    window.handleCreateShop = handleCreateShop;
    window.openEditShopModal = openEditShopModal;
    window.handleUpdateShop = handleUpdateShop;
    window.loadMyProducts = loadMyProducts;
    window.renderMyProducts = renderMyProducts;
    window.editProduct = editProduct;
    window.toggleProductStatus = toggleProductStatus;
    window.deleteProduct = deleteProduct;
    window.loadShopReviewsPage = loadShopReviewsPage;
    window.renderReviewsStats = renderReviewsStats;
    window.renderShopReviewCard = renderShopReviewCard;
    window.loadSubscriptionManagement = loadSubscriptionManagement;
    window.loadSubscriptionUsage = loadSubscriptionUsage;
    window.renderSubscriptionManagementInfo = renderSubscriptionManagementInfo;
    window.renderNoSubscription = renderNoSubscription;
    window.loadSubscriptionHistory = loadSubscriptionHistory;
    window.initSubscriptionManagementHandlers = initSubscriptionManagementHandlers;
    
    // ==================== Product Form Management ====================
    
    // Состояние формы добавления товара
    const productFormState = {
        photos: [],
        video: null,
        editingProductId: null, // ID товара для редактирования, null если создание
    };
    
    async function openAddProductModal(productId = null) {
        const state = getState();
        const api = getApi();
        const elements = getElements();
        const utils = getUtils();
        
        // Нормализуем productId - должен быть либо null (новый товар), либо валидное число (редактирование)
        console.log('[MODAL] openAddProductModal called with:', productId, 'type:', typeof productId);
        
        // Если значение null или undefined - оставляем null (режим создания)
        if (productId === null || productId === undefined) {
            productId = null;
        }
        // Если это объект события - игнорируем (не должно происходить после исправления обработчиков)
        else if (productId instanceof Event || (typeof productId === 'object' && productId !== null && 'target' in productId)) {
            console.warn('[MODAL] Event object passed as productId, ignoring');
            productId = null;
        }
        // Если это уже число
        else if (typeof productId === 'number') {
            // Проверяем что число валидное
            if (isNaN(productId) || !isFinite(productId) || productId <= 0) {
                console.warn('[MODAL] Invalid number passed as productId, ignoring:', productId);
                productId = null;
            }
            // Иначе оставляем как есть
        }
        // Если это строка
        else if (typeof productId === 'string') {
            const trimmed = productId.trim();
            if (trimmed === '' || trimmed === 'null' || trimmed === 'undefined') {
                productId = null;
            } else {
                const parsed = parseInt(trimmed, 10);
                if (isNaN(parsed) || !isFinite(parsed) || parsed <= 0) {
                    console.warn('[MODAL] Invalid string passed as productId, ignoring:', productId);
                    productId = null;
                } else {
                    productId = parsed;
                }
            }
        }
        // Любое другое значение - устанавливаем null
        else {
            console.warn('[MODAL] Invalid productId type/value, ignoring:', productId, typeof productId);
            productId = null;
        }
        
        console.log('[MODAL] Opening product modal, productId:', productId);
        // Проверяем подписку
        if (!state.mySubscription || !state.mySubscription.is_active) {
            if (utils.showToast) utils.showToast('Для добавления товаров нужна подписка', 'error');
            // Навигация на страницу подписки вместо открытия модального окна
            return;
        }
        
        // Загружаем категории для селекта
        if (elements.productCategoryInput && elements.productCategoryInput.options.length <= 1) {
            try {
                const flatCategories = await api.getCategoriesFlat();
                flatCategories.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat.id;
                    option.textContent = cat.parent_id ? `  └ ${cat.name}` : cat.name;
                    elements.productCategoryInput.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading categories:', error);
            }
        }
        
        // Устанавливаем режим редактирования или создания
        productFormState.editingProductId = productId;
        
        // Если редактирование - загружаем данные товара
        if (productId) {
            await loadProductForEdit(productId);
        } else {
            // Сбрасываем форму для создания
            resetProductForm();
        }
        
        // Обновляем заголовок модалки
        const modalTitle = document.querySelector('#addProductModal .modal-header h2');
        if (modalTitle) {
            modalTitle.textContent = productId ? 'Редактировать товар' : 'Добавить товар';
        }
        
        // Обновляем текст кнопки
        const submitBtn = document.getElementById('submitProductBtn');
        if (submitBtn) {
            const btnText = submitBtn.querySelector('.btn-text');
            if (btnText) {
                btnText.textContent = productId ? 'Сохранить изменения' : 'Добавить товар';
            } else {
                submitBtn.textContent = productId ? 'Сохранить изменения' : 'Добавить товар';
            }
        }
        
        // Инициализируем обработчики формы
        initProductFormHandlers();
        
        if (elements.addProductModal) {
            elements.addProductModal.hidden = false;
            
            // Показываем кнопку "Назад" Telegram при открытии модального окна
            const tg = window.tg || window.Telegram?.WebApp || null;
            if (tg && tg.BackButton) {
                tg.BackButton.show();
            }
        }
    }
    
    async function loadProductForEdit(productId) {
        const api = getApi();
        const utils = getUtils();
        
        try {
            console.log('[EDIT] Loading product for edit:', productId);
            const product = await api.getProduct(productId);
            console.log('[EDIT] Product loaded:', product);
            
            if (!product) {
                throw new Error('Товар не найден');
            }
            
            // Заполняем поля формы с проверкой существования элементов
            const nameInput = document.getElementById('productNameInput');
            const descInput = document.getElementById('productDescInput');
            const categoryInput = document.getElementById('productCategoryInput');
            const priceInput = document.getElementById('productPriceInput');
            const discountInput = document.getElementById('productDiscountInput');
            const quantityInput = document.getElementById('productQuantityInput');
            const trendingInput = document.getElementById('productTrendingInput');
            
            if (nameInput) nameInput.value = product.name || '';
            if (descInput) descInput.value = product.description || '';
            if (categoryInput) categoryInput.value = product.category_id || '';
            if (priceInput) priceInput.value = product.price || '';
            
            // Скидка
            const discountPercent = product.discount_percent || 
                (product.discount_price && product.price ? 
                    Math.round((1 - product.discount_price / product.price) * 100) : null);
            if (discountInput) discountInput.value = discountPercent || '';
            
            // Количество, тренд и активность
            if (quantityInput) quantityInput.value = product.quantity || 0;
            if (trendingInput) trendingInput.checked = product.is_trending || false;
            
            // Статус активности (если есть поле)
            const activeInput = document.getElementById('productActiveInput');
            if (activeInput) {
                activeInput.checked = product.is_active !== false;
            }
            
            // Загружаем существующие медиа
            productFormState.photos = [];
            productFormState.video = null;
            
            if (product.media && Array.isArray(product.media)) {
                product.media.forEach(media => {
                    // Проверяем тип медиа - может быть media_type или type
                    const mediaType = media.media_type || media.type || 'photo';
                    
                    if (mediaType === 'photo' || mediaType === 'image') {
                        productFormState.photos.push({
                            file: null, // Файл уже на сервере
                            preview: media.url,
                            mediaId: media.id,
                            isExisting: true,
                            url: media.url // Сохраняем URL для отображения
                        });
                    } else if (mediaType === 'video') {
                        productFormState.video = {
                            file: null,
                            url: media.url,
                            mediaId: media.id,
                            isExisting: true
                        };
                    }
                });
                
                console.log('[EDIT] Loaded media:', {
                    photos: productFormState.photos.length,
                    video: productFormState.video ? 'yes' : 'no'
                });
            }
            
            // Обновляем превью
            renderPhotosPreviews();
            
            // Обновляем превью видео
            if (productFormState.video) {
                const videoElement = document.getElementById('videoElement');
                const videoPreview = document.getElementById('videoPreview');
                const videoPlaceholder = document.getElementById('videoPlaceholder');
                
                if (videoElement && productFormState.video.url) {
                    // Очищаем предыдущий blob URL если есть
                    if (videoElement.src && videoElement.src.startsWith('blob:')) {
                        try {
                            URL.revokeObjectURL(videoElement.src);
                        } catch (e) {
                            // Игнорируем ошибки
                        }
                    }
                    
                    // Для существующего видео используем getMediaUrl
                    // Для нового видео (blob) используем напрямую
                    const videoUrl = productFormState.video.url;
                    
                    // Если это blob URL, используем напрямую, иначе обрабатываем через getMediaUrl
                    if (videoUrl.startsWith('blob:')) {
                        videoElement.src = videoUrl;
                    } else {
                        const getMediaUrl = utils.getMediaUrl || window.getMediaUrl;
                        if (getMediaUrl) {
                            videoElement.src = getMediaUrl(videoUrl);
                        } else {
                            videoElement.src = videoUrl;
                        }
                    }
                    
                    if (videoPreview) videoPreview.hidden = false;
                    if (videoPlaceholder) videoPlaceholder.hidden = true;
                }
            }
            
            // Обновляем превью скидки (если функция доступна)
            if (typeof window.updateDiscountPreview === 'function') {
                window.updateDiscountPreview();
            } else {
                // Если функция еще не определена, вызываем после небольшой задержки
                setTimeout(() => {
                    if (typeof window.updateDiscountPreview === 'function') {
                        window.updateDiscountPreview();
                    }
                }, 100);
            }
            
        } catch (error) {
            console.error('[EDIT] Error loading product for edit:', error);
            const errorMessage = error.message || 'Ошибка загрузки товара';
            if (utils.showToast) utils.showToast(`Ошибка загрузки товара: ${errorMessage}`, 'error');
            // Не закрываем модальное окно, чтобы пользователь мог попробовать снова
        }
    }
    
    function resetProductForm() {
        const elements = getElements();
        const utils = getUtils();
        
        // Очищаем все blob URL из состояния формы ПЕРЕД очисткой состояния
        productFormState.photos.forEach(photo => {
            if (photo.preview && photo.preview.startsWith('blob:')) {
                try {
                    URL.revokeObjectURL(photo.preview);
                } catch (e) {
                    // Игнорируем ошибки
                }
            }
        });
        
        // Очищаем blob URL из видео
        if (productFormState.video) {
            if (productFormState.video.url && productFormState.video.url.startsWith('blob:')) {
                try {
                    URL.revokeObjectURL(productFormState.video.url);
                } catch (e) {
                    // Игнорируем ошибки
                }
            }
        }
        
        productFormState.photos = [];
        productFormState.video = null;
        productFormState.editingProductId = null;
        
        // Сбрасываем форму
        const form = document.getElementById('addProductForm');
        if (form) form.reset();
        
        // Очищаем превью фото
        renderPhotosPreviews();
        
        // Очищаем видео
        const videoElement = document.getElementById('videoElement');
        const videoPreview = document.getElementById('videoPreview');
        const videoPlaceholder = document.getElementById('videoPlaceholder');
        if (videoElement) {
            // Очищаем текущий src
            if (videoElement.src && videoElement.src.startsWith('blob:')) {
                try {
                    URL.revokeObjectURL(videoElement.src);
                } catch (e) {
                    // Игнорируем ошибки
                }
            }
            // Очищаем сохраненный blob URL
            if (videoElement.dataset.blobUrl) {
                try {
                    URL.revokeObjectURL(videoElement.dataset.blobUrl);
                } catch (e) {
                    // Игнорируем ошибки
                }
                videoElement.dataset.blobUrl = '';
            }
            videoElement.src = '';
            videoElement.load(); // Сбрасываем состояние элемента
        }
        if (videoPreview) videoPreview.hidden = true;
        if (videoPlaceholder) videoPlaceholder.hidden = false;
        
        // Сбрасываем превью скидки
        const discountPreview = document.getElementById('discountPreview');
        if (discountPreview) discountPreview.hidden = true;
    }
    
    function initProductFormHandlers() {
        const api = getApi();
        const elements = getElements();
        const utils = getUtils();
        
        // Добавление фото
        const addPhotoBtn = document.getElementById('addPhotoBtn');
        const productPhotos = document.getElementById('productPhotos');
        
        if (addPhotoBtn && productPhotos) {
            // Убираем атрибут capture если он есть (для предотвращения режима 4:3)
            productPhotos.removeAttribute('capture');
            
            addPhotoBtn.onclick = () => productPhotos.click();
            
            productPhotos.onchange = (e) => {
                const files = Array.from(e.target.files);
                const remaining = 5 - productFormState.photos.length;
                
                if (files.length > remaining) {
                    if (utils.showToast) utils.showToast(`Можно добавить ещё ${remaining} фото`, 'error');
                }
                
                files.slice(0, remaining).forEach(file => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        productFormState.photos.push({
                            file: file,
                            preview: e.target.result
                        });
                        renderPhotosPreviews();
                    };
                    reader.readAsDataURL(file);
                });
                
                productPhotos.value = '';
            };
        }
        
        // Добавление видео
        const videoUploadArea = document.getElementById('videoUploadArea');
        const productVideo = document.getElementById('productVideo');
        const videoPlaceholder = document.getElementById('videoPlaceholder');
        const removeVideoBtn = document.getElementById('removeVideoBtn');
        
        if (videoPlaceholder && productVideo) {
            videoPlaceholder.onclick = () => productVideo.click();
            
            productVideo.onchange = (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                // Проверяем размер (50 МБ)
                if (file.size > 50 * 1024 * 1024) {
                    if (utils.showToast) utils.showToast('Видео слишком большое (макс. 50 МБ)', 'error');
                    return;
                }
                
                // Если было существующее видео, удаляем его из состояния
                const oldVideo = productFormState.video;
                if (oldVideo && oldVideo.isExisting && oldVideo.mediaId && productFormState.editingProductId) {
                    // Старое видео будет удалено при сохранении, пока просто помечаем что оно заменено
                    console.log('[VIDEO] Replacing existing video:', oldVideo.mediaId);
                }
                
                // Сохраняем новое видео в правильном формате
                productFormState.video = {
                    file: file,
                    isExisting: false,
                    url: null // Будет установлен после загрузки
                };
                
                const videoElement = document.getElementById('videoElement');
                const videoPreview = document.getElementById('videoPreview');
                
                // Очищаем предыдущий blob URL, если он есть
                if (videoElement) {
                    if (videoElement.src && videoElement.src.startsWith('blob:')) {
                        try {
                            URL.revokeObjectURL(videoElement.src);
                        } catch (e) {
                            // Игнорируем ошибки при очистке
                        }
                    }
                    
                    // Очищаем сохраненный blob URL
                    if (videoElement.dataset.blobUrl) {
                        try {
                            URL.revokeObjectURL(videoElement.dataset.blobUrl);
                        } catch (e) {
                            // Игнорируем ошибки
                        }
                    }
                    
                    // Останавливаем воспроизведение перед заменой src
                    videoElement.pause();
                    videoElement.src = '';
                    
                    // Создаем новый blob URL
                    const blobUrl = URL.createObjectURL(file);
                    videoElement.src = blobUrl;
                    videoElement.dataset.blobUrl = blobUrl;
                    
                    // Сохраняем blob URL в состоянии для последующей очистки
                    productFormState.video.url = blobUrl;
                    
                    // Обработчик для очистки blob URL при ошибке загрузки
                    const handleError = () => {
                        if (videoElement.dataset.blobUrl === blobUrl) {
                            try {
                                URL.revokeObjectURL(blobUrl);
                                videoElement.dataset.blobUrl = '';
                            } catch (e) {
                                // Игнорируем ошибки
                            }
                        }
                    };
                    
                    videoElement.addEventListener('error', handleError, { once: true });
                }
                
                if (videoPreview) videoPreview.hidden = false;
                if (videoPlaceholder) videoPlaceholder.hidden = true;
            };
        }
        
        if (removeVideoBtn) {
            removeVideoBtn.onclick = async () => {
                const videoElement = document.getElementById('videoElement');
                const video = productFormState.video;
                
                // Если это существующее видео (при редактировании), удаляем его с сервера
                if (video && video.isExisting && video.mediaId && productFormState.editingProductId) {
                    try {
                        await api.request(`/products/${productFormState.editingProductId}/media/${video.mediaId}`, {
                            method: 'DELETE'
                        });
                    } catch (error) {
                        console.error('Error deleting video:', error);
                        // Продолжаем удаление из UI даже если ошибка
                    }
                }
                
                // Очищаем blob URL, если он есть
                if (videoElement) {
                    try {
                        // Останавливаем воспроизведение
                        videoElement.pause();
                        
                        // Очищаем blob URL
                        if (videoElement.src && videoElement.src.startsWith('blob:')) {
                            URL.revokeObjectURL(videoElement.src);
                        }
                        
                        // Очищаем сохраненный blob URL
                        if (videoElement.dataset.blobUrl) {
                            try {
                                URL.revokeObjectURL(videoElement.dataset.blobUrl);
                            } catch (e) {
                                // Игнорируем ошибки
                            }
                            videoElement.dataset.blobUrl = '';
                        }
                        
                        videoElement.src = '';
                        videoElement.load(); // Сбрасываем состояние элемента
                    } catch (e) {
                        console.warn('Error cleaning up video blob URL:', e);
                    }
                }
                
                productFormState.video = null;
                const videoPreview = document.getElementById('videoPreview');
                const videoPlaceholder = document.getElementById('videoPlaceholder');
                if (videoPreview) videoPreview.hidden = true;
                if (videoPlaceholder) videoPlaceholder.hidden = false;
            };
        }
        
        // Счётчик символов описания
        const descInput = document.getElementById('productDescInput');
        const descCharCount = document.getElementById('productDescCharCount');
        if (descInput && descCharCount) {
            descInput.oninput = () => {
                descCharCount.textContent = descInput.value.length;
            };
        }
        
        // Превью скидки
        const priceInput = document.getElementById('productPriceInput');
        const discountInput = document.getElementById('productDiscountInput');
        
        // Делаем функцию доступной глобально для использования в loadProductForEdit
        window.updateDiscountPreview = () => {
            const formatPrice = utils.formatPrice || window.formatPrice;
            const price = parseFloat(priceInput?.value) || 0;
            const discount = parseInt(discountInput?.value) || 0;
            const discountPreview = document.getElementById('discountPreview');
            
            if (price > 0 && discount > 0 && discountPreview) {
                const newPrice = price * (1 - discount / 100);
                const savings = price - newPrice;
                
                const oldPriceEl = document.getElementById('previewOldPrice');
                const newPriceEl = document.getElementById('previewNewPrice');
                const savingsEl = document.getElementById('previewSavings');
                
                if (oldPriceEl && formatPrice) oldPriceEl.textContent = formatPrice(price);
                if (newPriceEl && formatPrice) newPriceEl.textContent = formatPrice(newPrice);
                if (savingsEl && formatPrice) savingsEl.textContent = `-${formatPrice(savings)}`;
                
                discountPreview.hidden = false;
            } else if (discountPreview) {
                discountPreview.hidden = true;
            }
        };
        
        const updateDiscountPreview = window.updateDiscountPreview;
        
        if (priceInput) priceInput.oninput = updateDiscountPreview;
        if (discountInput) discountInput.oninput = updateDiscountPreview;
        
        // Кнопки +/- для количества
        const qtyInput = document.getElementById('productQuantityInput');
        const qtyDecBtn = document.getElementById('qtyDecBtn');
        const qtyIncBtn = document.getElementById('qtyIncBtn');
        
        if (qtyDecBtn && qtyInput) {
            qtyDecBtn.onclick = () => {
                const current = parseInt(qtyInput.value) || 0;
                qtyInput.value = Math.max(0, current - 1);
            };
        }
        
        if (qtyIncBtn && qtyInput) {
            qtyIncBtn.onclick = () => {
                const current = parseInt(qtyInput.value) || 0;
                qtyInput.value = current + 1;
            };
        }
        
        // Кнопка отмены
        const cancelBtn = document.getElementById('cancelAddProduct');
        if (cancelBtn) {
            cancelBtn.onclick = () => {
                if (elements.addProductModal) elements.addProductModal.hidden = true;
            };
        }
    }
    
    function renderPhotosPreviews() {
        const utils = getUtils();
        const grid = document.getElementById('photosGrid');
        if (!grid) return;
        
        // Очищаем всё кроме кнопки добавления
        grid.querySelectorAll('.photo-slot.preview').forEach(el => el.remove());
        
        // Добавляем превью
        productFormState.photos.forEach((photo, index) => {
            const slot = document.createElement('div');
            slot.className = 'photo-slot preview';
            // Используем правильный URL для превью (если есть url, используем его, иначе preview)
            const photoUrl = photo.url || photo.preview;
            const getMediaUrl = utils.getMediaUrl || window.getMediaUrl;
            const displayUrl = photoUrl.startsWith('blob:') || photoUrl.startsWith('http') 
                ? photoUrl 
                : (getMediaUrl ? getMediaUrl(photoUrl) : photoUrl);
            
            slot.innerHTML = `
                <img src="${displayUrl}" alt="Photo ${index + 1}" loading="lazy">
                <button type="button" class="remove-photo-btn" data-index="${index}">✕</button>
                ${index === 0 ? '<span class="primary-badge">Главное</span>' : ''}
            `;
            
            slot.querySelector('.remove-photo-btn').onclick = async (e) => {
                e.stopPropagation();
                const api = getApi();
                const photo = productFormState.photos[index];
                
                // Очищаем blob URL, если это blob URL
                if (photo.preview && photo.preview.startsWith('blob:')) {
                    try {
                        URL.revokeObjectURL(photo.preview);
                    } catch (e) {
                        // Игнорируем ошибки
                    }
                }
                
                // Если это существующее фото (при редактировании), удаляем его с сервера
                if (photo.isExisting && photo.mediaId && productFormState.editingProductId) {
                    try {
                        await api.request(`/products/${productFormState.editingProductId}/media/${photo.mediaId}`, {
                            method: 'DELETE'
                        });
                    } catch (error) {
                        console.error('Error deleting media:', error);
                        // Продолжаем удаление из UI даже если ошибка
                    }
                }
                
                productFormState.photos.splice(index, 1);
                renderPhotosPreviews();
            };
            
            // Вставляем перед кнопкой добавления
            const addBtn = document.getElementById('addPhotoBtn');
            grid.insertBefore(slot, addBtn);
        });
        
        // Скрываем кнопку если 5 фото
        const addBtn = document.getElementById('addPhotoBtn');
        if (addBtn) {
            addBtn.style.display = productFormState.photos.length >= 5 ? 'none' : '';
        }
    }
    
    async function handleAddProduct(e) {
        const state = getState();
        const api = getApi();
        const elements = getElements();
        const utils = getUtils();
        
        e.preventDefault();
        
        const name = document.getElementById('productNameInput').value.trim();
        const description = document.getElementById('productDescInput').value.trim();
        const categoryId = document.getElementById('productCategoryInput').value;
        const price = parseFloat(document.getElementById('productPriceInput').value);
        const discountPercent = parseInt(document.getElementById('productDiscountInput').value) || null;
        const quantity = parseInt(document.getElementById('productQuantityInput').value) || 0;
        const isTrending = document.getElementById('productTrendingInput').checked;
        
        // Валидация
        if (!name) {
            if (utils.showToast) utils.showToast('Введите название товара', 'error');
            return;
        }
        
        if (!categoryId) {
            if (utils.showToast) utils.showToast('Выберите категорию', 'error');
            return;
        }
        
        if (!price || price <= 0) {
            if (utils.showToast) utils.showToast('Укажите корректную цену', 'error');
            return;
        }
        
        const isEditing = !!productFormState.editingProductId;
        
        if (!isEditing && productFormState.photos.length === 0) {
            if (utils.showToast) utils.showToast('Добавьте хотя бы одно фото', 'error');
            return;
        }
        
        // При редактировании проверяем, что есть хотя бы одно фото (новое или существующее)
        if (isEditing && productFormState.photos.length === 0) {
            if (utils.showToast) utils.showToast('Добавьте хотя бы одно фото', 'error');
            return;
        }
        
        const discountPrice = discountPercent ? Math.round(price * (1 - discountPercent / 100)) : null;
        
        // Показываем загрузку
        const submitBtn = document.getElementById('submitProductBtn');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnLoader = submitBtn.querySelector('.btn-loader');
        
        submitBtn.disabled = true;
        if (btnText) btnText.hidden = true;
        if (btnLoader) btnLoader.hidden = false;
        
        try {
            let productId;
            
            if (isEditing) {
                // Обновляем существующий товар
                productId = productFormState.editingProductId;
                
                // Проверяем, что productId валидный
                if (!productId || isNaN(productId)) {
                    throw new Error('Неверный ID товара для редактирования');
                }
                
                console.log('[SAVE] Updating product:', productId);
                
                await api.request(`/products/${productId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({
                        name,
                        description,
                        category_id: parseInt(categoryId),
                        price,
                        discount_price: discountPrice,
                        discount_percent: discountPercent,
                        quantity,
                        is_trending: isTrending
                    })
                });
                
                // Удаляем существующие медиа, которые были удалены пользователем
                const existingMediaIds = productFormState.photos
                    .filter(p => p.isExisting && p.mediaId)
                    .map(p => p.mediaId);
                
                // Здесь нужно загрузить текущие медиа товара для сравнения
                // Для простоты удаляем только те, которые точно были удалены
                // (это можно улучшить, сохранив оригинальный список медиа)
            } else {
                // Создаём новый товар
                const productResponse = await api.request('/products/', {
                    method: 'POST',
                    body: JSON.stringify({
                        name,
                        description,
                        category_id: parseInt(categoryId),
                        price,
                        discount_price: discountPrice,
                        discount_percent: discountPercent,
                        quantity,
                        is_trending: isTrending,
                        media: [] // Сначала создаём без медиа
                    })
                });
                
                productId = productResponse.id;
            }
            
            // Загружаем только новые фото (не существующие)
            const newPhotos = productFormState.photos.filter(p => !p.isExisting && p.file);
            if (newPhotos.length > 0) {
                const photoFormData = new FormData();
                let isPrimary = true;
                
                newPhotos.forEach((photo) => {
                    photoFormData.append('files', photo.file);
                    if (isPrimary && photo === productFormState.photos[0]) {
                        // Первое фото делаем главным
                        isPrimary = false;
                    }
                });
                photoFormData.append('is_primary', productFormState.photos[0] === newPhotos[0] ? 'true' : 'false');
                
                const photoHeaders = {};
                if (api.telegramId) {
                    photoHeaders['X-Telegram-ID'] = String(api.telegramId);
                }
                
                await fetch(`${api.baseUrl}/api/products/${productId}/media`, {
                    method: 'POST',
                    headers: photoHeaders,
                    body: photoFormData
                });
            }
            
            // Загружаем видео если есть новое
            // Проверяем, является ли video файлом (старый формат) или объектом (новый формат)
            const videoToUpload = productFormState.video;
            
            if (videoToUpload) {
                let videoFile = null;
                
                // Если это просто файл (старый формат), используем его напрямую
                if (videoToUpload instanceof File) {
                    videoFile = videoToUpload;
                } 
                // Если это объект с file (новый формат)
                else if (!videoToUpload.isExisting && videoToUpload.file) {
                    videoFile = videoToUpload.file;
                }
                
                // Если при редактировании заменяется существующее видео, удаляем старое
                if (isEditing && videoFile) {
                    try {
                        const currentProduct = await api.getProduct(productId);
                        if (currentProduct.media) {
                            const oldVideo = currentProduct.media.find(m => 
                                (m.media_type === 'video' || m.type === 'video')
                            );
                            if (oldVideo && oldVideo.id) {
                                console.log('[VIDEO] Deleting old video:', oldVideo.id);
                                try {
                                    await api.request(`/products/${productId}/media/${oldVideo.id}`, {
                                        method: 'DELETE'
                                    });
                                    console.log('[VIDEO] Old video deleted');
                                } catch (error) {
                                    console.warn('[VIDEO] Could not delete old video:', error);
                                    // Продолжаем загрузку нового видео
                                }
                            }
                        }
                    } catch (error) {
                        console.warn('[VIDEO] Could not fetch product to delete old video:', error);
                        // Продолжаем загрузку нового видео
                    }
                }
                
                // Загружаем новое видео
                if (videoFile) {
                    console.log('[VIDEO] Uploading new video for product:', productId);
                    const videoFormData = new FormData();
                    videoFormData.append('files', videoFile);
                    
                    const videoHeaders = {};
                    if (api.telegramId) {
                        videoHeaders['X-Telegram-ID'] = String(api.telegramId);
                    }
                    
                    const videoResponse = await fetch(`${api.baseUrl}/api/products/${productId}/media`, {
                        method: 'POST',
                        headers: videoHeaders,
                        body: videoFormData
                    });
                    
                    if (!videoResponse.ok) {
                        const errorData = await videoResponse.json().catch(() => ({ detail: 'Ошибка загрузки видео' }));
                        throw new Error(errorData.detail || 'Ошибка загрузки видео');
                    }
                    
                    console.log('[VIDEO] Video uploaded successfully');
                }
            }
            
            if (utils.showToast) utils.showToast(isEditing ? '✅ Товар успешно обновлён!' : '🎉 Товар успешно добавлен!', 'success');
            
            // Обновляем список товаров после сохранения
            if (isEditing) {
                await loadMyProducts();
            }
            if (elements.addProductModal) elements.addProductModal.hidden = true;
            
            // Сбрасываем форму
            resetProductForm();
            
            // Обновляем данные магазина и список товаров
            await loadMyShop();
            if (isEditing) {
                await loadMyProducts();
            }
            
        } catch (error) {
            console.error('[SAVE] Error saving product:', error);
            const errorMessage = error.message || 'Ошибка сохранения товара';
            if (utils.showToast) utils.showToast(`Ошибка сохранения: ${errorMessage}`, 'error');
        } finally {
            submitBtn.disabled = false;
            if (btnText) btnText.hidden = false;
            if (btnLoader) btnLoader.hidden = true;
        }
    }
    
    // Экспортируем состояние формы товара как глобальную переменную
    window.productFormState = productFormState;
    
    // Экспортируем функции
    window.openAddProductModal = openAddProductModal;
    window.loadProductForEdit = loadProductForEdit;
    window.resetProductForm = resetProductForm;
    window.initProductFormHandlers = initProductFormHandlers;
    window.renderPhotosPreviews = renderPhotosPreviews;
    window.handleAddProduct = handleAddProduct;
    
    // Инициализируем обработчики при загрузке модуля
    if (typeof document !== 'undefined') {
        // Ждем загрузки DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                initShopBlockedHandlers();
            });
        } else {
            initShopBlockedHandlers();
        }
    }
    
    // Экспортируем в модуль
    if (!window.App) window.App = {};
    if (!window.App.myshop) window.App.myshop = {};
    window.App.myshop.openAddProductModal = openAddProductModal;
    window.App.myshop.loadProductForEdit = loadProductForEdit;
    window.App.myshop.resetProductForm = resetProductForm;
    window.App.myshop.initProductFormHandlers = initProductFormHandlers;
    window.App.myshop.renderPhotosPreviews = renderPhotosPreviews;
    window.App.myshop.handleAddProduct = handleAddProduct;
    
    console.log('[MYSHOP] My Shop module loaded with all functions (statistics, management, editing, products, reviews, subscription, product form).');
})();

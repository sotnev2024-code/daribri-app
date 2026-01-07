/**
 * Subscription Management Module
 * Управление подписками и тарифными планами
 */

// Глобальное состояние для модуля
let pendingPlanId = null;

/**
 * Инициализация модуля подписки
 * @param {Object} state - глобальное состояние приложения
 * @param {Object} elements - DOM элементы
 * @param {Object} api - API клиент
 * @param {Object} helpers - вспомогательные функции
 */
function initSubscriptionModule(appState, appElements, appApi, helpers) {
    // Сохраняем ссылки на глобальные объекты
    // Важно: сохраняем ссылку на весь объект api, а не только его свойства
    window.SubscriptionModule = {
        state: appState,
        elements: appElements,
        api: appApi, // Это должен быть полный экземпляр класса API
        formatPrice: helpers.formatPrice,
        formatDateObject: helpers.formatDateObject,
        pluralize: helpers.pluralize,
        showToast: helpers.showToast,
        navigateTo: helpers.navigateTo
    };
    console.log('[SUBSCRIPTION] Module initialized');
    console.log('[SUBSCRIPTION] API object:', appApi);
    console.log('[SUBSCRIPTION] API constructor:', appApi?.constructor?.name);
    console.log('[SUBSCRIPTION] API instanceof API:', appApi instanceof (typeof API !== 'undefined' ? API : Object));
    console.log('[SUBSCRIPTION] requestSubscriptionPayment in API:', 'requestSubscriptionPayment' in appApi);
    console.log('[SUBSCRIPTION] requestSubscriptionPayment type:', typeof appApi?.requestSubscriptionPayment);
    
    // Проверяем наличие метода в прототипе
    if (appApi?.constructor?.prototype) {
        console.log('[SUBSCRIPTION] requestSubscriptionPayment in prototype:', 'requestSubscriptionPayment' in appApi.constructor.prototype);
        console.log('[SUBSCRIPTION] prototype method type:', typeof appApi.constructor.prototype.requestSubscriptionPayment);
    }
}

// Экспортируем функцию инициализации
window.initSubscriptionModule = initSubscriptionModule;

/**
 * Загружает страницу с планами подписки
 */
async function loadSubscriptionPage() {
    try {
        console.log('[SUBSCRIPTION] Loading subscription page...');
        
        // Загружаем планы и текущую подписку
        const [plansResult, subscriptionResult] = await Promise.allSettled([
            window.SubscriptionModule.api.getSubscriptionPlans(),
            window.SubscriptionModule.api.getMySubscription().catch(() => null)
        ]);
        
        // Обрабатываем результат загрузки планов
        if (plansResult.status === 'fulfilled') {
            window.SubscriptionModule.state.subscriptionPlans = plansResult.value || [];
            console.log('[SUBSCRIPTION] Plans loaded:', window.SubscriptionModule.state.subscriptionPlans.length);
        } else {
            console.error('[SUBSCRIPTION] Error loading plans:', plansResult.reason);
            window.SubscriptionModule.state.subscriptionPlans = [];
            window.SubscriptionModule.showToast('Ошибка загрузки планов подписки', 'error');
        }
        
        // Обрабатываем результат загрузки текущей подписки
        if (subscriptionResult.status === 'fulfilled') {
            window.SubscriptionModule.state.mySubscription = subscriptionResult.value || null;
            console.log('[SUBSCRIPTION] Current subscription loaded:', window.SubscriptionModule.state.mySubscription);
        } else {
            console.error('[SUBSCRIPTION] Error loading subscription:', subscriptionResult.reason);
            window.SubscriptionModule.state.mySubscription = null;
        }
        
        // Рендерим планы и текущую подписку
        renderSubscriptionPlans();
        renderCurrentSubscriptionInfo();
        
        console.log('[SUBSCRIPTION] Subscription page loaded successfully');
    } catch (error) {
        console.error('[SUBSCRIPTION] Error loading subscription page:', error);
        window.SubscriptionModule.showToast('Ошибка загрузки данных: ' + (error.message || 'Неизвестная ошибка'), 'error');
    }
}

/**
 * Отображает текущую информацию о подписке
 */
function renderCurrentSubscriptionInfo() {
    const currentInfo = document.getElementById('subscriptionPageCurrentInfo');
    const currentPlanName = document.getElementById('subscriptionPageCurrentPlanName');
    const currentExpires = document.getElementById('subscriptionPageCurrentExpires');
    
    if (!currentInfo || !currentPlanName || !currentExpires) {
        console.warn('[SUBSCRIPTION] renderCurrentSubscriptionInfo: required DOM elements not found');
        return;
    }
    
    try {
        const subscription = window.SubscriptionModule.state.mySubscription;
        
        if (subscription && subscription.is_active) {
            currentInfo.hidden = false;
            currentPlanName.textContent = subscription.plan_name || 'Подписка';
            const days = subscription.days_remaining || 0;
            currentExpires.textContent = `Истекает через: ${days} ${window.SubscriptionModule.pluralize(days, 'день', 'дня', 'дней')}`;
        } else {
            currentInfo.hidden = true;
        }
    } catch (error) {
        console.error('[SUBSCRIPTION] Error in renderCurrentSubscriptionInfo:', error);
        currentInfo.hidden = true;
    }
}

/**
 * Отображает список планов подписки
 */
function renderSubscriptionPlans() {
    const plansList = document.getElementById('subscriptionPagePlansList');
    if (!plansList) {
        console.error('[SUBSCRIPTION] plansList element not found');
        return;
    }
    
    const plans = window.SubscriptionModule.state.subscriptionPlans || [];
    const currentSubscription = window.SubscriptionModule.state.mySubscription;
    const currentPlanId = currentSubscription?.plan_id;
    
    if (plans.length === 0) {
        plansList.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
                <div style="font-size: 3rem; margin-bottom: 16px;">💳</div>
                <p>Планы подписки отсутствуют</p>
                <p style="font-size: 0.875rem; margin-top: 8px;">Обратитесь к администратору</p>
            </div>
        `;
        return;
    }
    
    plansList.innerHTML = plans.map(plan => {
        const isCurrent = plan.id === currentPlanId && currentSubscription?.is_active;
        const features = typeof plan.features === 'string' ? JSON.parse(plan.features) : (plan.features || {});
        
        // Вычисляем цену за день
        const pricePerDay = plan.price / plan.duration_days;
        
        return `
            <div class="plan-card ${isCurrent ? 'current' : ''}" data-plan-id="${plan.id}">
                <div class="plan-header">
                    <h3>${plan.name}</h3>
                    <div class="plan-price">
                        <span class="amount">${window.SubscriptionModule.formatPrice(plan.price)}</span>
                        <span class="period">/ ${plan.duration_days} ${plan.duration_days === 1 ? 'день' : 'дней'}</span>
                        ${plan.duration_days > 30 ? `<div class="price-per-day">${window.SubscriptionModule.formatPrice(pricePerDay)}/день</div>` : ''}
                    </div>
                </div>
                ${plan.description ? `<p class="plan-description">${plan.description}</p>` : ''}
                <div class="plan-features">
                    <div class="plan-feature">
                        <span class="feature-icon">📦</span>
                        <span>До ${plan.max_products} товаров</span>
                    </div>
                    ${features.analytics ? `
                        <div class="plan-feature">
                            <span class="feature-icon">📊</span>
                            <span>Аналитика продаж</span>
                        </div>
                    ` : ''}
                    ${features.priority_support ? `
                        <div class="plan-feature">
                            <span class="feature-icon">⭐</span>
                            <span>Приоритетная поддержка</span>
                        </div>
                    ` : ''}
                    ${features.promotions ? `
                        <div class="plan-feature">
                            <span class="feature-icon">🎯</span>
                            <span>${features.promotions} промо-размещений</span>
                        </div>
                    ` : ''}
                    ${features.featured_placement ? `
                        <div class="plan-feature">
                            <span class="feature-icon">✨</span>
                            <span>Выделенное место в каталоге</span>
                        </div>
                    ` : ''}
                </div>
                <button class="select-plan-btn ${isCurrent ? 'current' : ''}" 
                        onclick="requestSubscribeToPlan(${plan.id})"
                        ${isCurrent ? 'disabled' : ''}>
                    ${isCurrent ? '✓ Текущий план' : 'Выбрать план'}
                </button>
            </div>
        `;
    }).join('');
}

/**
 * Запрашивает подписку на план
 * @param {number} planId - ID плана
 */
function requestSubscribeToPlan(planId) {
    const plan = window.SubscriptionModule.state.subscriptionPlans.find(p => p.id === planId);
    if (!plan) return;
    
    pendingPlanId = planId;
    
    // Показываем информацию о плане в подтверждении
    const confirmInfo = document.getElementById('subscriptionPageConfirmInfo');
    const confirmModal = document.getElementById('subscriptionPageConfirmModal');
    const features = typeof plan.features === 'string' ? JSON.parse(plan.features) : (plan.features || {});
    
    if (!confirmInfo || !confirmModal) {
        console.error('[SUBSCRIPTION] Confirm modal elements not found');
        return;
    }
    
    // Форматируем цену
    const formatPrice = window.SubscriptionModule?.formatPrice || ((price) => `${price} ₽`);
    const pluralize = window.SubscriptionModule?.pluralize || ((count, one, few, many) => {
        const mod10 = count % 10;
        const mod100 = count % 100;
        if (mod100 >= 11 && mod100 <= 19) return many;
        if (mod10 === 1) return one;
        if (mod10 >= 2 && mod10 <= 4) return few;
        return many;
    });
    
    confirmInfo.innerHTML = `
        <div style="background: var(--bg-secondary); border-radius: var(--border-radius); padding: 16px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 1.125rem;">${plan.name}</h3>
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px; color: var(--text-secondary); font-size: 0.875rem;">
                <div style="display: flex; justify-content: space-between;">
                    <span>Срок действия:</span>
                    <span style="font-weight: 600;">${plan.duration_days} ${pluralize(plan.duration_days, 'день', 'дня', 'дней')}</span>
                </div>
                <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 8px; margin-top: 8px;">
                    <span>Стоимость:</span>
                    <span style="font-weight: 600; color: var(--primary-color, #007bff); font-size: 1.25rem;">${formatPrice(plan.price)}</span>
                </div>
            </div>
        </div>
        
        <div style="background: var(--bg-secondary); border-radius: var(--border-radius); padding: 16px; margin-bottom: 16px;">
            <h4 style="margin: 0 0 12px 0; font-size: 1rem; font-weight: 600;">Включено в план:</h4>
            <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.875rem; color: var(--text-secondary);">
                <div>• До ${plan.max_products} товаров</div>
                ${features.analytics ? '<div>• Аналитика продаж</div>' : ''}
                ${features.priority_support ? '<div>• Приоритетная поддержка</div>' : ''}
                ${features.promotions ? `<div>• ${features.promotions} промо-размещений</div>` : ''}
                ${features.featured_placement ? '<div>• Выделенное место в каталоге</div>' : ''}
            </div>
        </div>
        
        <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: var(--border-radius); padding: 12px; font-size: 0.875rem; color: #0369a1;">
            <div style="display: flex; align-items: start; gap: 8px;">
                <span>ℹ️</span>
                <div>
                    <strong>Важно:</strong> После подтверждения ссылка на оплату будет отправлена в чат Telegram бота. 
                    После оплаты подписка будет автоматически активирована.
                </div>
            </div>
        </div>
    `;
    
    confirmModal.hidden = false;
}

/**
 * Отменяет подтверждение подписки
 */
function cancelSubscribeConfirm() {
    pendingPlanId = null;
    const confirmModal = document.getElementById('subscriptionPageConfirmModal');
    if (confirmModal) {
        confirmModal.hidden = true;
    }
}

/**
 * Подтверждает подписку и отправляет запрос на оплату
 */
async function confirmSubscribe() {
    if (!pendingPlanId) {
        console.error('[SUBSCRIPTION] No pending plan ID');
        return;
    }
    
    const confirmBtn = document.getElementById('subscriptionPageConfirmBtn');
    const originalText = confirmBtn ? confirmBtn.textContent : 'Подтвердить';
    
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Отправка ссылки...';
    }
    
    try {
        console.log('[SUBSCRIPTION] Requesting payment for plan:', pendingPlanId);
        
        // Используем глобальный api объект напрямую
        // Приоритет: window.api > глобальный api > модуль api
        let apiClient = null;
        
        if (typeof window !== 'undefined' && window.api) {
            apiClient = window.api;
            console.log('[SUBSCRIPTION] Using window.api');
        } else if (typeof api !== 'undefined') {
            apiClient = api;
            console.log('[SUBSCRIPTION] Using global api');
        } else if (window.SubscriptionModule && window.SubscriptionModule.api) {
            apiClient = window.SubscriptionModule.api;
            console.log('[SUBSCRIPTION] Using module api');
        }
        
        if (!apiClient) {
            throw new Error('API клиент не найден. Обновите страницу (Ctrl+Shift+R).');
        }
        
        console.log('[SUBSCRIPTION] API client type:', apiClient.constructor?.name);
        console.log('[SUBSCRIPTION] Attempting to call requestSubscriptionPayment...');
        
        // Вызываем метод напрямую - методы класса доступны через прототип
        // Если метод определен в классе, он будет доступен даже если typeof показывает undefined
        let result;
        try {
            // Пробуем вызвать напрямую
            result = await apiClient.requestSubscriptionPayment(pendingPlanId);
            console.log('[SUBSCRIPTION] Payment request successful');
        } catch (callError) {
            // Если прямой вызов не сработал, пробуем через прототип
            if (callError.message && callError.message.includes('is not a function')) {
                console.warn('[SUBSCRIPTION] Direct call failed, trying via prototype');
                if (apiClient.constructor && apiClient.constructor.prototype && apiClient.constructor.prototype.requestSubscriptionPayment) {
                    result = await apiClient.constructor.prototype.requestSubscriptionPayment.call(apiClient, pendingPlanId);
                } else {
                    throw new Error('Метод requestSubscriptionPayment не найден в API. Убедитесь, что api.js загружен и содержит этот метод. Обновите страницу (Ctrl+Shift+R).');
                }
            } else {
                throw callError; // Пробрасываем другие ошибки
            }
        }
        
        console.log('[SUBSCRIPTION] Payment request result:', result);
        
        console.log('[SUBSCRIPTION] Payment request result:', result);
        
        window.SubscriptionModule.showToast('✅ Ссылка на оплату отправлена в чат Telegram бота!', 'success');
        const confirmModal = document.getElementById('subscriptionPageConfirmModal');
        if (confirmModal) {
            confirmModal.hidden = true;
        }
        pendingPlanId = null;
    } catch (error) {
        console.error('[SUBSCRIPTION] Error requesting payment:', error);
        console.error('[SUBSCRIPTION] Error stack:', error.stack);
        
        // Улучшенная обработка ошибок
        let errorMessage = 'Ошибка отправки ссылки на оплату';
        if (error.message) {
            if (error.message.includes('shop')) {
                errorMessage = 'Сначала создайте магазин';
            } else if (error.message.includes('Not Found') || error.message.includes('404')) {
                errorMessage = 'Эндпоинт не найден. Убедитесь, что сервер перезапущен и эндпоинт /api/subscriptions/request-payment доступен.';
            } else if (error.message.includes('not found')) {
                errorMessage = 'План подписки не найден';
            } else if (error.message.includes('not configured')) {
                errorMessage = 'Платежная система не настроена';
            } else {
                errorMessage = error.message;
            }
        }
        
        window.SubscriptionModule.showToast(errorMessage, 'error');
    } finally {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = originalText;
        }
    }
}

// Функции продления подписки удалены - весь функционал отключен
/*
async function openExtendSubscriptionModal_DELETED() {
    try {
        console.log('[SUBSCRIPTION] Opening extend subscription modal...');
        
        // Загружаем текущую подписку
        const subscription = await window.SubscriptionModule.api.getMySubscription();
        
        if (!subscription) {
            window.SubscriptionModule.showToast('Подписка не найдена', 'error');
            return;
        }
        
        // Загружаем информацию о плане
        const plans = await window.SubscriptionModule.api.getSubscriptionPlans();
        const currentPlan = plans.find(p => p.id === subscription.plan_id);
        
        if (!currentPlan) {
            window.SubscriptionModule.showToast('План подписки не найден', 'error');
            return;
        }
        
        // Вычисляем новую дату окончания (продлеваем на срок текущего плана)
        const currentEndDate = new Date(subscription.end_date);
        const now = new Date();
        
        // Если подписка уже истекла, начинаем с текущей даты
        const startDate = currentEndDate > now ? currentEndDate : now;
        const newEndDate = new Date(startDate);
        newEndDate.setDate(newEndDate.getDate() + currentPlan.duration_days);
        
        // Отображаем информацию
        const content = document.getElementById('extendSubscriptionContent');
        const modal = document.getElementById('extendSubscriptionModal');
        
        if (!content || !modal) {
            console.error('[SUBSCRIPTION] Modal elements not found');
            return;
        }
        
        content.innerHTML = `
            <div style="padding: 16px;">
                <!-- Текущая подписка -->
                <div style="background: var(--bg-secondary); border-radius: var(--border-radius); padding: 16px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h3 style="margin: 0; font-size: 1.125rem;">${currentPlan.name}</h3>
                        <span style="padding: 4px 12px; background: var(--success-color, #10b981); color: white; border-radius: 12px; font-size: 0.875rem; font-weight: 600;">Активна</span>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px; color: var(--text-secondary); font-size: 0.875rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>Текущий период:</span>
                            <span>${window.SubscriptionModule.formatDateObject(new Date(subscription.start_date))} - ${window.SubscriptionModule.formatDateObject(currentEndDate)}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Осталось дней:</span>
                            <span style="font-weight: 600;">${subscription.days_remaining || 0} ${window.SubscriptionModule.pluralize(subscription.days_remaining || 0, 'день', 'дня', 'дней')}</span>
                        </div>
                    </div>
                </div>
                
                <!-- Продление -->
                <div style="background: var(--bg-secondary); border-radius: var(--border-radius); padding: 16px; margin-bottom: 16px; border: 2px solid var(--primary-color, #007bff);">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <span style="font-size: 1.5rem;">📅</span>
                        <h3 style="margin: 0; font-size: 1.125rem;">Продление подписки</h3>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px; color: var(--text-secondary); font-size: 0.875rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>Продлить на:</span>
                            <span style="font-weight: 600;">${currentPlan.duration_days} ${window.SubscriptionModule.pluralize(currentPlan.duration_days, 'день', 'дня', 'дней')}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 8px; margin-top: 8px;">
                            <span>Новая дата окончания:</span>
                            <span style="font-weight: 600; color: var(--primary-color, #007bff);">${window.SubscriptionModule.formatDateObject(newEndDate)}</span>
                        </div>
                    </div>
                </div>
                
                <!-- Стоимость -->
                <div style="background: var(--bg-secondary); border-radius: var(--border-radius); padding: 16px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1rem; font-weight: 600;">Стоимость продления:</span>
                        <span style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color, #007bff);">${window.SubscriptionModule.formatPrice(currentPlan.price)}</span>
                    </div>
                </div>
                
                <!-- Информационное сообщение -->
                <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: var(--border-radius); padding: 12px; font-size: 0.875rem; color: #0369a1;">
                    <div style="display: flex; align-items: start; gap: 8px;">
                        <span>ℹ️</span>
                        <div>
                            <strong>Важно:</strong> После подтверждения ссылка на оплату будет отправлена в чат Telegram бота. 
                            После оплаты подписка будет автоматически продлена.
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Сохраняем ID плана для продления
        window.extendSubscriptionPlanId = subscription.plan_id;
        window.extendSubscriptionNewEndDate = newEndDate;
        
        // Показываем модальное окно
        modal.hidden = false;
        
        // Устанавливаем обработчики
        const backBtn = document.getElementById('extendSubscriptionBackBtn');
        const confirmBtn = document.getElementById('extendSubscriptionConfirmBtn');
        const closeBtn = document.getElementById('closeExtendSubscriptionModal');
        
        if (backBtn) {
            backBtn.onclick = () => {
                modal.hidden = true;
            };
        }
        
        if (confirmBtn) {
            confirmBtn.onclick = async () => {
                await confirmExtendSubscription();
            };
        }
        
        if (closeBtn) {
            closeBtn.onclick = () => {
                modal.hidden = true;
            };
        }
        
        // Закрытие по клику на фон
        modal.onclick = (e) => {
            if (e.target.id === 'extendSubscriptionModal') {
                modal.hidden = true;
            }
        };
        
        console.log('[SUBSCRIPTION] Extend subscription modal opened');
    } catch (error) {
        console.error('[SUBSCRIPTION] Error opening extend subscription modal:', error);
        window.SubscriptionModule.showToast('Ошибка загрузки данных: ' + (error.message || 'Неизвестная ошибка'), 'error');
    }
}

/**
 * Подтверждает продление подписки и отправляет ссылку на оплату
 */
async function confirmExtendSubscription() {
    const planId = window.extendSubscriptionPlanId;
    const modal = document.getElementById('extendSubscriptionModal');
    const confirmBtn = document.getElementById('extendSubscriptionConfirmBtn');
    
    if (!planId) {
        const showToast = window.SubscriptionModule?.showToast || ((msg, type) => alert(msg));
        showToast('Ошибка: план подписки не найден', 'error');
        return;
    }
    
    const originalText = confirmBtn ? confirmBtn.textContent : 'Продлить';
    
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Отправка ссылки...';
    }
    
    try {
        console.log('[SUBSCRIPTION] Requesting payment for plan (extend):', planId);
        
        // Используем тот же подход, что и в confirmSubscribe
        let apiClient = null;
        
        if (typeof window !== 'undefined' && window.api) {
            apiClient = window.api;
            console.log('[SUBSCRIPTION] Using window.api (extend)');
        } else if (typeof api !== 'undefined') {
            apiClient = api;
            console.log('[SUBSCRIPTION] Using global api (extend)');
        } else if (window.SubscriptionModule && window.SubscriptionModule.api) {
            apiClient = window.SubscriptionModule.api;
            console.log('[SUBSCRIPTION] Using module api (extend)');
        }
        
        if (!apiClient) {
            throw new Error('API клиент не найден. Обновите страницу (Ctrl+Shift+R).');
        }
        
        console.log('[SUBSCRIPTION] Using API client (extend):', apiClient);
        
        // Вызываем метод напрямую
        let result;
        try {
            result = await apiClient.requestSubscriptionPayment(planId);
            console.log('[SUBSCRIPTION] Payment request successful (extend)');
        } catch (callError) {
            if (callError.message && callError.message.includes('is not a function')) {
                console.warn('[SUBSCRIPTION] Direct call failed, trying via prototype (extend)');
                if (apiClient.constructor && apiClient.constructor.prototype && apiClient.constructor.prototype.requestSubscriptionPayment) {
                    result = await apiClient.constructor.prototype.requestSubscriptionPayment.call(apiClient, planId);
                } else {
                    throw new Error('Метод requestSubscriptionPayment не найден в API. Убедитесь, что api.js загружен и содержит этот метод. Обновите страницу (Ctrl+Shift+R).');
                }
            } else {
                throw callError;
            }
        }
        
        const showToast = window.SubscriptionModule?.showToast || ((msg, type) => alert(msg));
        showToast('✅ Ссылка на оплату отправлена в чат Telegram бота!', 'success');
        
        if (modal) {
            modal.hidden = true;
        }
        
        // Очищаем сохраненные данные
        window.extendSubscriptionPlanId = null;
        window.extendSubscriptionNewEndDate = null;
        
    } catch (error) {
        console.error('[SUBSCRIPTION] Error requesting payment (extend):', error);
        console.error('[SUBSCRIPTION] Error stack:', error.stack);
        
        // Улучшенная обработка ошибок
        let errorMessage = 'Ошибка отправки ссылки на оплату';
        if (error.message) {
            if (error.message.includes('shop')) {
                errorMessage = 'Сначала создайте магазин';
            } else if (error.message.includes('Not Found') || error.message.includes('404')) {
                errorMessage = 'Эндпоинт не найден. Убедитесь, что сервер перезапущен и эндпоинт /api/subscriptions/request-payment доступен.';
            } else if (error.message.includes('not found')) {
                errorMessage = 'План подписки не найден';
            } else if (error.message.includes('not configured')) {
                errorMessage = 'Платежная система не настроена';
            } else {
                errorMessage = error.message;
            }
        }
        
        const showToast = window.SubscriptionModule?.showToast || ((msg, type) => alert(msg));
        showToast(errorMessage, 'error');
    } finally {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = originalText;
        }
    }
}

// Экспортируем функции в глобальную область видимости
window.loadSubscriptionPage = loadSubscriptionPage;
window.requestSubscribeToPlan = requestSubscribeToPlan;
window.cancelSubscribeConfirm = cancelSubscribeConfirm;
window.confirmSubscribe = confirmSubscribe;
// Функции продления подписки удалены


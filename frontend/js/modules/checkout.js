/**
 * Checkout Module - оформление заказа
 * 
 * Шаги:
 * 1. Запрос номера телефона
 * 2. Адрес доставки (Yandex Maps)
 * 3. Дата и время доставки
 * 4. Подтверждение заказа + промокод
 */

(function() {
    'use strict';
    
    console.log('[CHECKOUT] Module loading...');
    
    // ==================== Импорты зависимостей ====================
    const getState = () => window.state || window.App?.state;
    const getApi = () => window.api;
    const getTg = () => window.tg || window.Telegram?.WebApp || null;
    
    // Константа стоимости доставки
    const DELIVERY_FEE = 500;
    
    // ==================== Сохранение данных пользователя ====================
    const SAVED_USER_DATA_KEY = 'daribri_checkout_user_data';
    
    function getSavedUserData() {
        try {
            const saved = localStorage.getItem(SAVED_USER_DATA_KEY);
            if (saved) {
                return JSON.parse(saved);
            }
        } catch (e) {
            console.warn('[CHECKOUT] Error loading saved user data:', e);
        }
        return null;
    }
    
    function saveUserData(data) {
        try {
            const toSave = {
                phone: data.phone,
                recipientName: data.recipientName,
                address: data.address,
                deliveryComment: data.deliveryComment,
                latitude: data.latitude,
                longitude: data.longitude
            };
            localStorage.setItem(SAVED_USER_DATA_KEY, JSON.stringify(toSave));
            console.log('[CHECKOUT] User data saved');
        } catch (e) {
            console.warn('[CHECKOUT] Error saving user data:', e);
        }
    }
    
    // ==================== Состояние checkout ====================
    const getCheckoutState = () => {
        if (window.checkoutState) return window.checkoutState;
        
        // Загружаем сохранённые данные пользователя
        const savedData = getSavedUserData();
        
        window.checkoutState = {
            step: 1,
            phone: savedData?.phone || null,
            address: savedData?.address || null,
            addressIsValid: null,
            latitude: savedData?.latitude || null,
            longitude: savedData?.longitude || null,
            recipientName: savedData?.recipientName || '',
            deliveryComment: savedData?.deliveryComment || '',
            deliveryDate: null,  // Дата и время не сохраняем
            deliveryTime: null,  // Дата и время не сохраняем
            shopId: null,
            shopCity: null,
            shopAddress: null,  // Адрес магазина для самовывоза
            shopLatitude: null,  // Координаты магазина
            shopLongitude: null,
            deliveryType: 'delivery',  // 'delivery' или 'pickup'
            items: [],
            promoCode: null,
            promoDiscount: 0,
            promoType: null
        };
        return window.checkoutState;
    };
    
    // ==================== Вспомогательные функции ====================
    const showToast = (message, type = 'info') => {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            console.log(`[TOAST ${type}] ${message}`);
        }
    };
    
    const formatPrice = (price) => {
        if (window.formatPrice) return window.formatPrice(price);
        return new Intl.NumberFormat('ru-RU').format(price) + ' ₽';
    };
    
    const getMediaUrl = (url) => {
        if (window.getMediaUrl) return window.getMediaUrl(url);
        if (!url) return '';
        if (url.startsWith('http')) return url;
        return `/media/${url}`;
    };
    
    // Переменные для карты
    let deliveryMap = null;
    let deliveryMapPlacemark = null;
    
    // ==================== TELEGRAM BACK BUTTON ДЛЯ CHECKOUT ====================
    let checkoutBackButtonHandler = null;
    
    function setupCheckoutBackButton() {
        const tg = getTg();
        if (!tg || !tg.BackButton) return;
        
        // Удаляем старый обработчик если есть
        if (checkoutBackButtonHandler) {
            tg.BackButton.offClick(checkoutBackButtonHandler);
        }
        
        // Создаём новый обработчик для checkout
        checkoutBackButtonHandler = () => {
            const checkoutState = getCheckoutState();
            console.log('[CHECKOUT BackButton] Clicked, current step:', checkoutState.step);
            
            // Проверяем, что checkout modal действительно открыт
            const modal = document.getElementById('checkoutModal');
            if (!modal || modal.hidden) {
                console.log('[CHECKOUT BackButton] Modal is hidden, closing anyway');
                closeCheckoutModal();
                return;
            }
            
            if (checkoutState.step > 1) {
                // Возвращаемся на предыдущий шаг
                showCheckoutStep(checkoutState.step - 1);
            } else {
                // На первом шаге - закрываем checkout
                console.log('[CHECKOUT BackButton] First step, closing checkout');
                closeCheckoutModal();
            }
        };
        
        tg.BackButton.onClick(checkoutBackButtonHandler);
        tg.BackButton.show();
        console.log('[CHECKOUT] BackButton setup for checkout');
    }
    
    function restoreMainBackButton() {
        const tg = getTg();
        if (!tg || !tg.BackButton) return;
        
        console.log('[CHECKOUT] Restoring main back button...');
        
        // Удаляем обработчик checkout
        if (checkoutBackButtonHandler) {
            try {
                tg.BackButton.offClick(checkoutBackButtonHandler);
            } catch (e) {
                console.warn('[CHECKOUT] Error removing checkout back handler:', e);
            }
            checkoutBackButtonHandler = null;
        }
        
        // Скрываем кнопку временно
        tg.BackButton.hide();
        
        // Проверяем, нужна ли кнопка для текущей страницы после закрытия checkout
        // Даем время для обновления DOM и затем проверяем
        setTimeout(() => {
            // Проверяем, на какой странице мы находимся
            const cartPage = document.getElementById('cartPage');
            const favoritesPage = document.getElementById('favoritesPage');
            const profilePage = document.getElementById('profilePage');
            const productPage = document.getElementById('productPage');
            
            // Если открыта любая страница кроме каталога, показываем кнопку "Назад"
            const isOnMainPage = !cartPage?.hidden || !favoritesPage?.hidden || !profilePage?.hidden || !productPage?.hidden;
            const mainContent = document.querySelector('.main-content');
            const isOnCatalog = mainContent && mainContent.style.display !== 'none' && mainContent.hidden === false;
            
            // Проверяем историю навигации
            const shouldShowBackButton = (window.navigationHistory && window.navigationHistory.length > 1) || 
                                        (isOnMainPage && !isOnCatalog);
            
            if (shouldShowBackButton) {
                console.log('[CHECKOUT] Showing back button for current page');
                if (window.showBackButton && typeof window.showBackButton === 'function') {
                    window.showBackButton();
                }
            } else {
                console.log('[CHECKOUT] Hiding back button (on catalog or no history)');
            }
        }, 50);
        
        console.log('[CHECKOUT] BackButton restored to main handler');
    }
    
    // ==================== ОСНОВНАЯ ФУНКЦИЯ CHECKOUT ====================
    async function checkout() {
        console.log('[CHECKOUT] Starting checkout...');
        
        const state = getState();
        const api = getApi();
        const checkoutState = getCheckoutState();
        
        if (!state || !api) {
            console.error('[CHECKOUT] State or API not available');
            showToast('Ошибка инициализации', 'error');
            return;
        }
        
        // Проверяем, что корзина не пуста
        if (!state.cart || state.cart.length === 0) {
            showToast('Корзина пуста', 'warning');
            return;
        }
        
        // Проверяем наличие товаров
        const stockCheck = await checkStockAvailability(state.cart, api);
        if (!stockCheck.canProceed) {
            if (stockCheck.hasChanges) {
                // Перезагружаем корзину
                if (window.loadCart) await window.loadCart();
                if (window.renderCart) window.renderCart();
            }
            return;
        }
        
        // Определяем shop_id из первого товара
        const firstItem = state.cart[0];
        checkoutState.shopId = firstItem.shop_id || firstItem.shopId;
        checkoutState.items = state.cart.filter(item => 
            (item.shop_id || item.shopId) === checkoutState.shopId
        );
        
        // Получаем данные магазина (город и адрес)
        try {
            const shop = await api.getShop(checkoutState.shopId);
            checkoutState.shopCity = shop.city || shop.city_name || 'Екатеринбург';
            checkoutState.shopAddress = shop.address || null;
            checkoutState.shopLatitude = shop.latitude || null;
            checkoutState.shopLongitude = shop.longitude || null;
        } catch (error) {
            console.error('[CHECKOUT] Error loading shop:', error);
            checkoutState.shopCity = 'Екатеринбург';
            checkoutState.shopAddress = null;
            checkoutState.shopLatitude = null;
            checkoutState.shopLongitude = null;
        }
        
        // Открываем модальное окно
        const modal = document.getElementById('checkoutModal');
        if (modal) {
            modal.hidden = false;
            
            // Настраиваем кнопку "Назад" для checkout
            setupCheckoutBackButton();
            
            showCheckoutStep(1);
        } else {
            console.error('[CHECKOUT] Modal not found');
        }
    }
    
    // ==================== ПРОВЕРКА НАЛИЧИЯ ТОВАРОВ ====================
    async function checkStockAvailability(cartItems, api) {
        const changedItems = [];
        const removedItems = [];
        let hasChanges = false;
        
        try {
            for (const item of cartItems) {
                try {
                    const product = await api.getProduct(item.product_id);
                    const availableQty = product.quantity || 0;
                    
                    if (availableQty === 0) {
                        removedItems.push({
                            name: item.product_name || item.name || 'Товар',
                            requestedQty: item.quantity
                        });
                        await api.removeFromCart(item.id);
                        hasChanges = true;
                    } else if (availableQty < item.quantity) {
                        changedItems.push({
                            name: item.product_name || item.name || 'Товар',
                            requestedQty: item.quantity,
                            availableQty: availableQty
                        });
                        await api.updateCartItem(item.id, availableQty);
                        hasChanges = true;
                    }
                } catch (error) {
                    console.error('[CHECKOUT] Error checking product:', error);
                }
            }
            
            if (removedItems.length > 0 || changedItems.length > 0) {
                await showStockWarningModal(removedItems, changedItems);
                return { canProceed: false, hasChanges: true };
            }
            
            return { canProceed: true, hasChanges: false };
        } catch (error) {
            console.error('[CHECKOUT] Stock check error:', error);
            return { canProceed: true, hasChanges: false };
        }
    }
    
    // Модальное окно предупреждения о наличии
    function showStockWarningModal(removedItems, changedItems) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';
            
            let content = '';
            if (removedItems.length > 0) {
                content += '<div style="margin-bottom:15px;"><strong>Удалены (нет в наличии):</strong><ul style="margin:10px 0;padding-left:20px;">';
                removedItems.forEach(item => content += `<li>${item.name}</li>`);
                content += '</ul></div>';
            }
            if (changedItems.length > 0) {
                content += '<div><strong>Изменено количество:</strong><ul style="margin:10px 0;padding-left:20px;">';
                changedItems.forEach(item => content += `<li>${item.name}: ${item.requestedQty} → ${item.availableQty} шт.</li>`);
                content += '</ul></div>';
            }
            
            modal.innerHTML = `
                <div style="max-width:420px;width:90%;background:var(--bg-secondary,#fff);border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,0.3);">
                    <div style="padding:20px;text-align:center;">
                        <h2 style="margin:0 0 15px;font-size:18px;">⚠️ Изменения в наличии</h2>
                        <div style="text-align:left;font-size:14px;">${content}</div>
                        <p style="color:var(--text-secondary);font-size:13px;margin-top:15px;">Проверьте корзину</p>
                        <button style="margin-top:15px;padding:12px 30px;border-radius:12px;border:none;background:var(--primary,#007AFF);color:white;cursor:pointer;font-size:16px;">Понятно</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            modal.querySelector('button').onclick = () => { modal.remove(); resolve(); };
            modal.onclick = (e) => { if (e.target === modal) { modal.remove(); resolve(); } };
        });
    }
    
    // ==================== ПЕРЕКЛЮЧЕНИЕ ШАГОВ ====================
    function showCheckoutStep(step) {
        const checkoutState = getCheckoutState();
        checkoutState.step = step;
        
        console.log('[CHECKOUT] Showing step', step);
        
        // Скрываем все шаги
        for (let i = 1; i <= 4; i++) {
            const stepEl = document.getElementById(`checkoutStep${i}`);
            if (stepEl) stepEl.hidden = (i !== step);
        }
        
        // Обновляем прогресс
        const progressFill = document.querySelector('.checkout-progress .progress-fill');
        if (progressFill) {
            progressFill.style.width = `${(step / 4) * 100}%`;
        }
        
        // Обновляем текст шага
        const progressText = document.querySelector('.checkout-progress .progress-text');
        if (progressText) {
            progressText.textContent = `Шаг ${step} из 4`;
        }
        
        // Обновляем кнопку "Назад" для текущего шага
        setupCheckoutBackButton();
        
        // Инициализируем шаг
        switch(step) {
            case 1: initStep1Phone(); break;
            case 2: initStep2Address(); break;
            case 3: initStep3DateTime(); break;
            case 4: initStep4Confirm(); break;
        }
    }
    
    // ==================== ШАГ 1: НОМЕР ТЕЛЕФОНА ====================
    function initStep1Phone() {
        console.log('[CHECKOUT STEP 1] Initializing phone step...');
        
        const checkoutState = getCheckoutState();
        const tg = getTg();
        
        const requestPhoneBtn = document.getElementById('requestPhoneBtn');
        const phoneDisplay = document.getElementById('phoneDisplay');
        const phoneNumber = document.getElementById('phoneNumber');
        const changePhoneBtn = document.getElementById('changePhoneBtn');
        const nextBtn = document.getElementById('checkoutNext1');
        
        if (!requestPhoneBtn || !nextBtn) {
            console.error('[CHECKOUT STEP 1] Elements not found');
            return;
        }
        
        // Показать номер телефона
        function displayPhone(phone) {
            checkoutState.phone = phone;
            if (phoneDisplay && phoneNumber) {
                phoneNumber.textContent = phone;
                phoneDisplay.hidden = false;
                requestPhoneBtn.hidden = true;
            }
            nextBtn.disabled = false;
        }
        
        // Сбросить номер
        function resetPhone() {
            checkoutState.phone = null;
            if (phoneDisplay) phoneDisplay.hidden = true;
            if (requestPhoneBtn) requestPhoneBtn.hidden = false;
            // Удаляем ручной ввод если есть
            const manualInput = document.querySelector('.manual-phone-input');
            if (manualInput) manualInput.remove();
            nextBtn.disabled = true;
        }
        
        // Если номер уже есть
        if (checkoutState.phone) {
            displayPhone(checkoutState.phone);
        } else {
            resetPhone();
        }
        
        // Кнопка "Изменить"
        if (changePhoneBtn) {
            changePhoneBtn.onclick = resetPhone;
        }
        
        // Показать ручной ввод
        function showManualInput() {
            const section = requestPhoneBtn.parentElement;
            requestPhoneBtn.hidden = true;
            
            const manualDiv = document.createElement('div');
            manualDiv.className = 'manual-phone-input';
            manualDiv.innerHTML = `
                <input type="tel" id="manualPhoneInput" class="phone-input" 
                       placeholder="+7 (999) 123-45-67" inputmode="tel"
                       style="width:100%;padding:14px 16px;font-size:1rem;border:1px solid var(--border);border-radius:var(--border-radius);margin-bottom:12px;">
                <button type="button" id="confirmManualPhone" 
                        style="width:100%;padding:14px;background:var(--primary);color:white;border:none;border-radius:var(--border-radius);font-size:1rem;cursor:pointer;">
                    Подтвердить
                </button>
            `;
            section.appendChild(manualDiv);
            
            const input = document.getElementById('manualPhoneInput');
            const confirmBtn = document.getElementById('confirmManualPhone');
            
            if (input) input.focus();
            
            if (confirmBtn) {
                confirmBtn.onclick = () => {
                    const phone = input.value.replace(/[^\d+]/g, '');
                    if (phone.length >= 10) {
                        manualDiv.remove();
                        displayPhone(phone.startsWith('+') ? phone : '+' + phone);
                        showToast('Номер сохранён', 'success');
                    } else {
                        showToast('Введите корректный номер', 'error');
                    }
                };
            }
        }
        
        // Запрос номера через Telegram
        requestPhoneBtn.onclick = async () => {
            console.log('[CHECKOUT STEP 1] Requesting phone...');
            
            if (!tg || !tg.requestContact) {
                console.log('[CHECKOUT STEP 1] Telegram not available, showing manual input');
                showManualInput();
                return;
            }
            
            // Показываем загрузку
            requestPhoneBtn.disabled = true;
            const originalHTML = requestPhoneBtn.innerHTML;
            requestPhoneBtn.innerHTML = `
                <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" style="animation:spin 1s linear infinite;">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="30 60"/>
                </svg>
                Ожидание...
            `;
            
            try {
                tg.requestContact((success, data) => {
                    requestPhoneBtn.disabled = false;
                    requestPhoneBtn.innerHTML = originalHTML;
                    
                    if (success && data?.responseUnsafe?.contact?.phone_number) {
                        let phone = data.responseUnsafe.contact.phone_number;
                        if (!phone.startsWith('+')) phone = '+' + phone;
                        displayPhone(phone);
                        showToast('Номер получен', 'success');
                    } else {
                        console.log('[CHECKOUT STEP 1] User cancelled or no data');
                        showToast('Отменено', 'info');
                    }
                });
            } catch (error) {
                console.error('[CHECKOUT STEP 1] Error:', error);
                requestPhoneBtn.disabled = false;
                requestPhoneBtn.innerHTML = originalHTML;
                showManualInput();
            }
        };
        
        // Кнопка "Далее"
        nextBtn.onclick = () => {
            if (!checkoutState.phone || checkoutState.phone.length < 10) {
                showToast('Укажите номер телефона', 'error');
                return;
            }
            showCheckoutStep(2);
        };
    }
    
    // ==================== ШАГ 2: АДРЕС ДОСТАВКИ ====================
    function initStep2Address() {
        console.log('[CHECKOUT STEP 2] Initializing address step...');
        
        const checkoutState = getCheckoutState();
        
        const addressInput = document.getElementById('deliveryAddress');
        const recipientInput = document.getElementById('recipientName');
        const commentInput = document.getElementById('deliveryComment');
        const mapContainer = document.getElementById('deliveryMapContainer');
        const pickupMapContainer = document.getElementById('pickupMapContainer');
        const nextBtn = document.getElementById('checkoutNext2');
        const useLocationBtn = document.getElementById('useCurrentLocationBtn');
        const stepContent = document.querySelector('#checkoutStep2 .checkout-step-content');
        const deliverySection = document.getElementById('deliverySection');
        const pickupSection = document.getElementById('pickupSection');
        const shopAddressDisplay = document.getElementById('shopAddressDisplay');
        const shopAddressText = document.getElementById('shopAddressText');
        const deliveryTypeDelivery = document.getElementById('deliveryTypeDelivery');
        const deliveryTypePickup = document.getElementById('deliveryTypePickup');
        const deliveryCommentLabel = document.getElementById('deliveryCommentLabel');
        
        if (!addressInput || !recipientInput || !nextBtn) {
            console.error('[CHECKOUT STEP 2] Elements not found');
            return;
        }
        
        // Функция переключения типа получения заказа
        function switchDeliveryType(type) {
            checkoutState.deliveryType = type;
            
            if (type === 'pickup') {
                // Самовывоз
                if (deliverySection) deliverySection.hidden = true;
                if (pickupSection) pickupSection.hidden = false;
                if (deliveryTypeDelivery) {
                    deliveryTypeDelivery.classList.remove('active');
                    deliveryTypeDelivery.style.borderColor = 'var(--border)';
                }
                if (deliveryTypePickup) {
                    deliveryTypePickup.classList.add('active');
                    deliveryTypePickup.style.borderColor = 'var(--primary)';
                }
                // Скрываем поле комментария для самовывоза
                const commentLabel = document.getElementById('deliveryCommentLabel');
                const commentInput = document.getElementById('deliveryComment');
                if (commentLabel) {
                    // Скрываем label и textarea (они находятся в разных элементах)
                    commentLabel.style.display = 'none';
                }
                if (commentInput) {
                    commentInput.style.display = 'none';
                }
                
                // Устанавливаем адрес магазина
                if (checkoutState.shopAddress) {
                    const city = checkoutState.shopCity || '';
                    const fullAddress = checkoutState.shopAddress.toLowerCase().includes(city.toLowerCase()) 
                        ? checkoutState.shopAddress 
                        : `г. ${city}, ${checkoutState.shopAddress}`;
                    checkoutState.address = fullAddress;
                    if (shopAddressText) shopAddressText.textContent = fullAddress;
                    
                    // Загружаем карту с адресом магазина
                    if (pickupMapContainer) {
                        if (checkoutState.shopLatitude && checkoutState.shopLongitude) {
                            loadShopPickupMap(pickupMapContainer, checkoutState.shopLatitude, checkoutState.shopLongitude, fullAddress);
                        } else {
                            // Если координат нет, пытаемся геокодировать адрес
                            fetch(`/api/geocode/geocode?address=${encodeURIComponent(fullAddress)}&city=${encodeURIComponent(city)}`)
                                .then(res => res.json())
                                .then(data => {
                                    if (data.coordinates && data.coordinates.lat && data.coordinates.lng) {
                                        checkoutState.shopLatitude = data.coordinates.lat;
                                        checkoutState.shopLongitude = data.coordinates.lng;
                                        loadShopPickupMap(pickupMapContainer, data.coordinates.lat, data.coordinates.lng, fullAddress);
                                    }
                                })
                                .catch(err => console.error('[PICKUP MAP] Geocoding error:', err));
                        }
                    }
                }
                
                // Обновляем заголовок шага
                const step2Title = document.getElementById('checkoutStep2Title');
                if (step2Title) step2Title.textContent = 'Способ получения заказа';
            } else {
                // Доставка
                if (deliverySection) deliverySection.hidden = false;
                if (pickupSection) pickupSection.hidden = true;
                if (deliveryTypeDelivery) {
                    deliveryTypeDelivery.classList.add('active');
                    deliveryTypeDelivery.style.borderColor = 'var(--primary)';
                }
                if (deliveryTypePickup) {
                    deliveryTypePickup.classList.remove('active');
                    deliveryTypePickup.style.borderColor = 'var(--border)';
                }
                // Показываем поле комментария для доставки
                const commentLabel = document.getElementById('deliveryCommentLabel');
                const commentInput = document.getElementById('deliveryComment');
                if (commentLabel) {
                    commentLabel.textContent = 'Комментарий к адресу (опционально)';
                    commentLabel.style.display = '';
                }
                if (commentInput) {
                    commentInput.style.display = '';
                }
                
                // Загружаем карту доставки
                if (mapContainer) {
                    loadDeliveryMap(mapContainer, addressInput, validate);
                }
                
                // Обновляем заголовок шага
                const step2Title = document.getElementById('checkoutStep2Title');
                if (step2Title) step2Title.textContent = 'Адрес доставки';
            }
            
            validate();
        }
        
        // Обработчики кнопок выбора типа
        if (deliveryTypeDelivery) {
            deliveryTypeDelivery.onclick = () => {
                switchDeliveryType('delivery');
                validate(); // Вызываем валидацию после переключения
            };
        }
        if (deliveryTypePickup) {
            deliveryTypePickup.onclick = () => {
                switchDeliveryType('pickup');
                validate(); // Вызываем валидацию после переключения
            };
        }
        
        // Инициализируем тип по умолчанию
        switchDeliveryType(checkoutState.deliveryType || 'delivery');
        validate(); // Вызываем валидацию после инициализации
        
        // Показываем уведомление о зоне доставки
        const existingNotice = document.getElementById('deliveryZoneNotice');
        if (existingNotice) existingNotice.remove();
        
        if (checkoutState.shopCity && stepContent) {
            const notice = document.createElement('div');
            notice.id = 'deliveryZoneNotice';
            notice.className = 'delivery-zone-notice';
            notice.innerHTML = `
                <span style="font-size:1.2em;">📍</span>
                <span>Доставка возможна только в <strong>${checkoutState.shopCity}</strong></span>
            `;
            notice.style.cssText = 'display:flex;align-items:center;gap:10px;padding:12px 16px;background:linear-gradient(135deg, #FFF3CD 0%, #FFE69C 100%);border:1px solid #FFC107;border-radius:12px;margin-bottom:16px;font-size:14px;';
            stepContent.insertBefore(notice, stepContent.firstChild.nextSibling?.nextSibling || stepContent.firstChild);
        }
        
        // Заполняем сохранённые данные
        if (checkoutState.address) addressInput.value = checkoutState.address;
        if (checkoutState.recipientName) recipientInput.value = checkoutState.recipientName;
        if (checkoutState.deliveryComment && commentInput) commentInput.value = checkoutState.deliveryComment;
        
        // Валидация адреса на соответствие городу
        function validateAddress(address) {
            if (!address || !checkoutState.shopCity) return true;
            
            const shopCity = checkoutState.shopCity.toLowerCase();
            const addressLower = address.toLowerCase();
            
            // Варианты написания городов
            const cityVariants = {
                'санкт-петербург': ['санкт-петербург', 'спб', 'с.-петербург', 'с-петербург', 'петербург', 'питер', 'ленинград'],
                'москва': ['москва', 'мск', 'moscow'],
                'казань': ['казань', 'kazan'],
                'новосибирск': ['новосибирск'],
                'екатеринбург': ['екатеринбург', 'свердловск', 'ekaterinburg'],
                'нижний новгород': ['нижний новгород', 'н.новгород', 'н. новгород', 'нижний'],
                'краснодар': ['краснодар'],
                'сочи': ['сочи'],
                'ростов-на-дону': ['ростов-на-дону', 'ростов на дону', 'ростов'],
            };
            
            // Находим варианты для текущего города
            let allowedVariants = [shopCity];
            for (const [city, variants] of Object.entries(cityVariants)) {
                // Проверяем, соответствует ли shopCity этому городу
                if (shopCity === city || 
                    shopCity.includes(city) || 
                    city.includes(shopCity) || 
                    variants.some(v => shopCity === v || shopCity.includes(v) || v.includes(shopCity))) {
                    allowedVariants = [...allowedVariants, city, ...variants];
                    break;
                }
            }
            
            // Проверяем, содержит ли адрес допустимый город
            const isValid = allowedVariants.some(variant => addressLower.includes(variant));
            console.log('[CHECKOUT] Address validation (validateAddress):', {
                address: address,
                shopCity: shopCity,
                allowedVariants: allowedVariants,
                isValid: isValid
            });
            return isValid;
        }
        
        // Валидация формы
        function validate() {
            const hasRecipient = recipientInput.value.trim().length > 0;
            
            let isValid = false;
            let addressOk = true;
            const hasAddress = addressInput.value.trim().length > 0;
            
            if (checkoutState.deliveryType === 'pickup') {
                // Для самовывоза нужен только получатель и адрес магазина
                isValid = hasRecipient && checkoutState.shopAddress;
            } else {
                // Для доставки нужен адрес и получатель
                // Проверяем адрес на соответствие городу
                if (checkoutState.addressIsValid === false) {
                    addressOk = false;
                } else if (hasAddress && !validateAddress(addressInput.value)) {
                    // Текстовая проверка, если API не проверил
                    addressOk = false;
                    checkoutState.addressIsValid = false;
                }
                
                isValid = hasAddress && hasRecipient && addressOk;
            }
            
            nextBtn.disabled = !isValid;
            
            // Показываем предупреждение если адрес не в том городе (только для доставки)
            if (checkoutState.deliveryType === 'delivery') {
                const warningEl = document.getElementById('addressWarning');
                if (!addressOk && hasAddress) {
                    if (!warningEl) {
                        const warning = document.createElement('div');
                        warning.id = 'addressWarning';
                        warning.style.cssText = 'color:#dc3545;font-size:13px;margin-top:6px;display:flex;align-items:center;gap:6px;';
                        warning.innerHTML = `⚠️ Адрес должен быть в городе ${checkoutState.shopCity}`;
                        addressInput.parentElement.appendChild(warning);
                    }
                } else if (warningEl) {
                    warningEl.remove();
                }
            }
            
            return isValid;
        }
        
        validate();
        
        // Обработчики изменений
        addressInput.addEventListener('input', () => {
            checkoutState.address = addressInput.value;
            checkoutState.addressIsValid = null; // Сбрасываем валидацию при ручном вводе
            validate();
        });
        
        recipientInput.addEventListener('input', () => {
            checkoutState.recipientName = recipientInput.value;
            validate();
        });
        
        if (commentInput) {
            commentInput.addEventListener('input', () => {
                checkoutState.deliveryComment = commentInput.value;
            });
        }
        
        // Загружаем карту
        if (mapContainer) {
            loadDeliveryMap(mapContainer, addressInput, validate);
        }
        
        // Автодополнение адреса
        initAddressAutocomplete(addressInput, validate);
        
        // Использование геолокации
        if (useLocationBtn) {
            useLocationBtn.onclick = () => {
                if (!navigator.geolocation) {
                    showToast('Геолокация не поддерживается', 'error');
                    return;
                }
                
                useLocationBtn.disabled = true;
                useLocationBtn.textContent = 'Определение...';
                
                navigator.geolocation.getCurrentPosition(
                    async (position) => {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        checkoutState.latitude = lat;
                        checkoutState.longitude = lng;
                        
                        // Получаем адрес по координатам
                        await reverseGeocode(lat, lng, addressInput, validate);
                        
                        useLocationBtn.disabled = false;
                        useLocationBtn.innerHTML = `
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2v4m0 12v4M2 12h4m12 0h4"/><circle cx="12" cy="12" r="3"/>
                            </svg>
                            Использовать текущее местоположение
                        `;
                    },
                    (error) => {
                        showToast('Не удалось определить местоположение', 'error');
                        useLocationBtn.disabled = false;
                        useLocationBtn.innerHTML = `
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2v4m0 12v4M2 12h4m12 0h4"/><circle cx="12" cy="12" r="3"/>
                            </svg>
                            Использовать текущее местоположение
                        `;
                    }
                );
            };
        }
        
        // Кнопка "Далее"
        nextBtn.onclick = () => {
            checkoutState.recipientName = recipientInput.value.trim();
            if (commentInput) checkoutState.deliveryComment = commentInput.value;
            
            if (checkoutState.deliveryType === 'delivery') {
                checkoutState.address = addressInput.value.trim();
                
                if (!checkoutState.address || !checkoutState.recipientName) {
                    showToast('Заполните все обязательные поля', 'error');
                    return;
                }
                
                if (checkoutState.addressIsValid === false) {
                    showToast(`Доставка возможна только в ${checkoutState.shopCity}`, 'error');
                    return;
                }
            } else {
                // Самовывоз
                if (!checkoutState.recipientName) {
                    showToast('Укажите имя получателя', 'error');
                    return;
                }
                
                if (!checkoutState.shopAddress) {
                    showToast('Адрес магазина не указан', 'error');
                    return;
                }
            }
            
            showCheckoutStep(3);
        };
        
        // Кнопка назад
        const backBtn = document.querySelector('#checkoutStep2 .back-to-step');
        if (backBtn) {
            backBtn.onclick = () => showCheckoutStep(1);
        }
    }
    
    // Обратное геокодирование (координаты -> адрес)
    async function reverseGeocode(lat, lng, addressInput, validateFn) {
        const checkoutState = getCheckoutState();
        
        try {
            const url = `/api/geocode/reverse?lat=${lat}&lng=${lng}${checkoutState.shopCity ? `&city=${encodeURIComponent(checkoutState.shopCity)}` : ''}`;
            const response = await fetch(url);
            
            if (response.ok) {
                const data = await response.json();
                if (data.address) {
                    checkoutState.address = data.address;
                    
                    // Строгая проверка города
                    if (data.is_valid === false || data.is_valid === true) {
                        checkoutState.addressIsValid = data.is_valid;
                    } else {
                        // Если API не вернул флаг, проверяем сами
                        checkoutState.addressIsValid = checkAddressCity(data.address, checkoutState.shopCity);
                    }
                    
                    addressInput.value = data.address;
                    
                    if (!checkoutState.addressIsValid) {
                        showToast(`❌ Этот адрес вне зоны доставки. Выберите адрес в ${checkoutState.shopCity}`, 'error');
                        
                        // Визуально показываем ошибку
                        addressInput.style.borderColor = '#dc3545';
                        setTimeout(() => {
                            addressInput.style.borderColor = '';
                        }, 3000);
                    } else {
                        showToast('✅ Адрес выбран', 'success');
                    }
                    
                    if (validateFn) validateFn();
                }
            }
        } catch (error) {
            console.error('[GEOCODE] Reverse geocoding error:', error);
        }
    }
    
    // Проверка адреса на соответствие городу
    function checkAddressCity(address, shopCity) {
        if (!address || !shopCity) return true;
        
        const addressLower = address.toLowerCase();
        const cityLower = shopCity.toLowerCase();
        
        // Варианты написания городов
        const cityAliases = {
            'санкт-петербург': ['санкт-петербург', 'спб', 'с.-петербург', 'с-петербург', 'петербург', 'питер', 'ленинград'],
            'москва': ['москва', 'мск', 'moscow'],
            'казань': ['казань', 'kazan'],
            'новосибирск': ['новосибирск'],
            'екатеринбург': ['екатеринбург', 'свердловск', 'ekaterinburg'],
            'нижний новгород': ['нижний новгород', 'н.новгород', 'н. новгород', 'нижний'],
            'краснодар': ['краснодар'],
            'сочи': ['сочи'],
            'ростов-на-дону': ['ростов-на-дону', 'ростов на дону', 'ростов'],
        };
        
        // Находим все допустимые варианты названия города
        let variants = [cityLower];
        for (const [mainCity, aliases] of Object.entries(cityAliases)) {
            // Проверяем, соответствует ли shopCity этому городу
            if (cityLower === mainCity || 
                cityLower.includes(mainCity) || 
                mainCity.includes(cityLower) || 
                aliases.some(a => cityLower === a || cityLower.includes(a) || a.includes(cityLower))) {
                variants = [...variants, mainCity, ...aliases];
                break;
            }
        }
        
        // Проверяем, содержит ли адрес хотя бы один вариант
        const isValid = variants.some(v => addressLower.includes(v));
        console.log('[CHECKOUT] Address validation:', {
            address: address,
            shopCity: shopCity,
            variants: variants,
            isValid: isValid
        });
        return isValid;
    }
    
    // Загрузка карты Yandex
    async function loadDeliveryMap(container, addressInput, validateFn) {
        const checkoutState = getCheckoutState();
        
        // Определяем центр карты по городу магазина
        const cityCoords = {
            'санкт-петербург': [59.939095, 30.315868],
            'спб': [59.939095, 30.315868],
            'питер': [59.939095, 30.315868],
            'москва': [55.7558, 37.6173],
            'мск': [55.7558, 37.6173],
            'казань': [55.796127, 49.105177],
            'новосибирск': [55.0084, 82.9357],
            'екатеринбург': [56.8389, 60.6057],
            'нижний новгород': [56.2965, 43.9361],
            'челябинск': [55.1644, 61.4368],
            'самара': [53.1959, 50.1002],
            'омск': [54.9885, 73.3242],
            'ростов-на-дону': [47.2357, 39.7015],
            'уфа': [54.7388, 55.9721],
            'красноярск': [56.0153, 92.8932],
            'пермь': [58.0105, 56.2502],
            'воронеж': [51.6720, 39.1843],
            'волгоград': [48.7080, 44.5133],
            'краснодар': [45.0355, 38.9753],
            'саратов': [51.5336, 46.0343],
            'тюмень': [57.1522, 65.5272],
            'тольятти': [53.5078, 49.4204],
            'ижевск': [56.8527, 53.2114],
            'барнаул': [53.3548, 83.7698],
            'ульяновск': [54.3143, 48.4031],
            'иркутск': [52.2978, 104.2964],
            'хабаровск': [48.4827, 135.0838],
            'ярославль': [57.6299, 39.8737],
            'владивосток': [43.1155, 131.8855],
            'махачкала': [42.9849, 47.5047],
            'томск': [56.4846, 84.9476],
            'оренбург': [51.7681, 55.0968],
            'кемерово': [55.3333, 86.0833],
            'новокузнецк': [53.7596, 87.1216],
            'рязань': [54.6269, 39.6916],
            'астрахань': [46.3479, 48.0408],
            'набережные челны': [55.7388, 52.3959],
            'пенза': [53.2007, 45.0046],
            'липецк': [52.6031, 39.5708],
            'тула': [54.1930, 37.6173],
            'киров': [58.5966, 49.6601],
            'чебоксары': [56.1467, 47.2517],
            'калининград': [54.7104, 20.4522],
            'брянск': [53.2521, 34.3717],
            'курск': [51.7373, 36.1874],
            'иваново': [56.9975, 40.9715],
            'магнитогорск': [53.4078, 58.9790],
            'тверь': [56.8584, 35.9006],
            'ставрополь': [45.0449, 41.9692],
            'белгород': [50.5954, 36.5873],
            'сочи': [43.5855, 39.7231]
        };
        
        const shopCity = (checkoutState.shopCity || 'Екатеринбург').toLowerCase();
        let center = [56.8389, 60.6057]; // Екатеринбург по умолчанию
        
        // Ищем координаты города
        for (const [cityName, coords] of Object.entries(cityCoords)) {
            if (shopCity.includes(cityName) || cityName.includes(shopCity)) {
                center = coords;
                break;
            }
        }
        
        console.log('[MAP] Shop city:', checkoutState.shopCity, '-> Center:', center);
        
        // Создаём контейнер
        container.innerHTML = `
            <div id="deliveryMap" style="width:100%;height:300px;border-radius:12px;overflow:hidden;"></div>
            <p style="margin-top:8px;font-size:0.875rem;color:var(--text-secondary);">
                💡 Нажмите на карту, чтобы выбрать адрес
            </p>
        `;
        
        // Загружаем Yandex Maps API
        if (typeof ymaps === 'undefined') {
            try {
                const configResponse = await fetch('/api/config');
                let apiKey = '';
                if (configResponse.ok) {
                    const config = await configResponse.json();
                    apiKey = config.yandex_api_key || '';
                }
                
                let scriptUrl = 'https://api-maps.yandex.ru/2.1/?lang=ru_RU';
                if (apiKey) scriptUrl += `&apikey=${encodeURIComponent(apiKey)}`;
                
                const script = document.createElement('script');
                script.src = scriptUrl;
                script.onload = () => initYandexMap(center, addressInput, validateFn);
                script.onerror = () => {
                    document.getElementById('deliveryMap').innerHTML = `
                        <div style="display:flex;align-items:center;justify-content:center;height:100%;background:#f5f5f5;color:#666;text-align:center;padding:20px;">
                            Карта недоступна. Введите адрес вручную.
                        </div>
                    `;
                };
                document.head.appendChild(script);
            } catch (error) {
                console.error('[MAP] Error loading Yandex Maps:', error);
            }
        } else {
            initYandexMap(center, addressInput, validateFn);
        }
    }
    
    // Инициализация карты Yandex
    function initYandexMap(center, addressInput, validateFn) {
        if (typeof ymaps === 'undefined') return;
        
        ymaps.ready(() => {
            const checkoutState = getCheckoutState();
            
            // Уничтожаем старую карту
            if (deliveryMap) {
                try { deliveryMap.destroy(); } catch(e) {}
                deliveryMap = null;
                deliveryMapPlacemark = null;
            }
            
            const mapElement = document.getElementById('deliveryMap');
            if (!mapElement) return;
            
            // Создаём карту (Yandex Maps использует [lat, lng] - широта, долгота)
            console.log('[MAP] Creating map with center:', center);
            deliveryMap = new ymaps.Map('deliveryMap', {
                center: center, // [lat, lng]
                zoom: 12,
                controls: ['zoomControl', 'geolocationControl']
            });
            
            // Клик по карте (Yandex возвращает [lat, lng])
            deliveryMap.events.add('click', async (e) => {
                const coords = e.get('coords');
                const lat = coords[0];  // Широта
                const lng = coords[1];  // Долгота
                
                console.log('[MAP] Click at:', { lat, lng });
                
                checkoutState.latitude = lat;
                checkoutState.longitude = lng;
                
                // Ставим/перемещаем маркер
                if (deliveryMapPlacemark) {
                    deliveryMapPlacemark.geometry.setCoordinates(coords);
                } else {
                    deliveryMapPlacemark = new ymaps.Placemark(coords, {}, {
                        preset: 'islands#redDotIcon',
                        draggable: true
                    });
                    deliveryMap.geoObjects.add(deliveryMapPlacemark);
                    
                    // Обработчик перетаскивания (координаты [lat, lng])
                    deliveryMapPlacemark.events.add('dragend', async () => {
                        const newCoords = deliveryMapPlacemark.geometry.getCoordinates();
                        const lat = newCoords[0];  // Широта
                        const lng = newCoords[1];  // Долгота
                        console.log('[MAP] Marker dragged to:', { lat, lng });
                        checkoutState.latitude = lat;
                        checkoutState.longitude = lng;
                        await reverseGeocode(lat, lng, addressInput, validateFn);
                    });
                }
                
                // Получаем адрес
                await reverseGeocode(lat, lng, addressInput, validateFn);
            });
        });
    }
    
    // Автодополнение адреса
    function initAddressAutocomplete(input, validateFn) {
        const checkoutState = getCheckoutState();
        const suggestionsContainer = document.getElementById('addressSuggestions');
        if (!input || !suggestionsContainer) return;
        
        let timeoutId = null;
        const city = checkoutState.shopCity || 'Екатеринбург';
        
        // Добавляем placeholder с названием города
        input.placeholder = `Введите адрес в г. ${city}...`;
        
        input.addEventListener('input', () => {
            const query = input.value.trim();
            
            // Сбрасываем валидацию при ручном вводе
            checkoutState.addressIsValid = null;
            
            // Убираем предупреждение
            const warningEl = document.getElementById('addressWarning');
            if (warningEl) warningEl.remove();
            
            if (timeoutId) clearTimeout(timeoutId);
            
            if (query.length < 3) {
                suggestionsContainer.hidden = true;
                return;
            }
            
            timeoutId = setTimeout(async () => {
                try {
                    // Добавляем город к запросу если его нет
                    let searchQuery = query;
                    if (!query.toLowerCase().includes(city.toLowerCase())) {
                        searchQuery = `${city}, ${query}`;
                    }
                    
                    const url = `/api/geocode/autocomplete?query=${encodeURIComponent(searchQuery)}&city=${encodeURIComponent(city)}&limit=7`;
                    console.log('[AUTOCOMPLETE] Requesting:', url);
                    const response = await fetch(url);
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('[AUTOCOMPLETE] Response:', data);
                        let suggestions = data.suggestions || [];
                        
                        // Фильтруем только валидные адреса (в нужном городе)
                        // API возвращает {text, title, description}
                        suggestions = suggestions.filter(s => {
                            const address = s.text || s.title || '';
                            if (!address) return false;
                            return checkAddressCity(address, city);
                        });
                        
                        if (suggestions.length > 0) {
                            suggestionsContainer.innerHTML = suggestions.map(s => {
                                const address = s.text || s.title || '';
                                const description = s.description || '';
                                return `
                                    <div class="address-suggestion" data-address="${address}" data-valid="true"
                                         style="padding:12px 16px;cursor:pointer;border-bottom:1px solid var(--border);transition:background 0.2s;">
                                        <div style="font-size:14px;">${address}</div>
                                        ${description ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">${description}</div>` : ''}
                                    </div>
                                `;
                            }).join('');
                            suggestionsContainer.hidden = false;
                            
                            // Стили для контейнера
                            suggestionsContainer.style.cssText = 'position:absolute;top:100%;left:0;right:0;background:var(--bg-secondary,#fff);border:1px solid var(--border);border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);max-height:300px;overflow-y:auto;z-index:100;';
                            
                            // Обработчик выбора
                            suggestionsContainer.querySelectorAll('.address-suggestion').forEach(el => {
                                el.onmouseenter = () => el.style.background = 'var(--bg-tertiary, #f5f5f5)';
                                el.onmouseleave = () => el.style.background = '';
                                
                                el.onclick = async () => {
                                    const address = el.dataset.address;
                                    input.value = address;
                                    checkoutState.address = address;
                                    checkoutState.addressIsValid = true;
                                    suggestionsContainer.hidden = true;
                                    
                                    showToast('✅ Адрес выбран', 'success');
                                    
                                    // Получаем координаты адреса через геокодирование
                                    try {
                                        const geoUrl = `/api/geocode/geocode?address=${encodeURIComponent(address)}&city=${encodeURIComponent(city)}`;
                                        console.log('[AUTOCOMPLETE] Geocoding:', geoUrl);
                                        const geoResponse = await fetch(geoUrl);
                                        if (geoResponse.ok) {
                                            const geoData = await geoResponse.json();
                                            console.log('[AUTOCOMPLETE] Geocode result:', geoData);
                                            
                                            // API возвращает {coordinates: {lat, lng}, address, is_valid}
                                            if (geoData.coordinates && geoData.coordinates.lat && geoData.coordinates.lng) {
                                                checkoutState.latitude = geoData.coordinates.lat;
                                                checkoutState.longitude = geoData.coordinates.lng;
                                                
                                                // Обновляем маркер на карте (координаты [lat, lng])
                                                if (deliveryMap) {
                                                    const coords = [geoData.coordinates.lat, geoData.coordinates.lng];
                                                    console.log('[MAP] Setting marker at:', coords);
                                                    if (deliveryMapPlacemark) {
                                                        deliveryMapPlacemark.geometry.setCoordinates(coords);
                                                    } else {
                                                        deliveryMapPlacemark = new ymaps.Placemark(coords, {}, {
                                                            preset: 'islands#redDotIcon',
                                                            draggable: true
                                                        });
                                                        deliveryMap.geoObjects.add(deliveryMapPlacemark);
                                                    }
                                                    deliveryMap.setCenter(coords, 16);
                                                }
                                            }
                                        }
                                    } catch (geoErr) {
                                        console.warn('[AUTOCOMPLETE] Could not geocode address:', geoErr);
                                    }
                                    
                                    if (validateFn) validateFn();
                                };
                            });
                        } else {
                            // Показываем сообщение что адресов не найдено
                            suggestionsContainer.innerHTML = `
                                <div style="padding:16px;text-align:center;color:var(--text-secondary);font-size:14px;">
                                    Адреса не найдены в ${city}
                                </div>
                            `;
                            suggestionsContainer.hidden = false;
                        }
                    }
                } catch (error) {
                    console.error('[AUTOCOMPLETE] Error:', error);
                }
            }, 300);
        });
        
        // Скрываем при клике вне
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.hidden = true;
            }
        });
    }
    
    // Загрузка карты магазина для самовывоза
    async function loadShopPickupMap(container, lat, lng, address) {
        container.innerHTML = `
            <div id="pickupMap" style="width:100%;height:300px;border-radius:12px;overflow:hidden;"></div>
        `;
        
        // Загружаем Yandex Maps API
        if (typeof ymaps === 'undefined') {
            try {
                const configResponse = await fetch('/api/config');
                let apiKey = '';
                if (configResponse.ok) {
                    const config = await configResponse.json();
                    apiKey = config.yandex_api_key || '';
                }
                
                let scriptUrl = 'https://api-maps.yandex.ru/2.1/?lang=ru_RU';
                if (apiKey) scriptUrl += `&apikey=${encodeURIComponent(apiKey)}`;
                
                const script = document.createElement('script');
                script.src = scriptUrl;
                script.onload = () => initShopPickupMap([lat, lng], address);
                document.head.appendChild(script);
            } catch (error) {
                console.error('[MAP] Error loading Yandex Maps:', error);
            }
        } else {
            initShopPickupMap([lat, lng], address);
        }
    }
    
    // Инициализация карты магазина
    function initShopPickupMap(center, address) {
        if (typeof ymaps === 'undefined') return;
        
        ymaps.ready(() => {
            const mapElement = document.getElementById('pickupMap');
            if (!mapElement) return;
            
            const map = new ymaps.Map('pickupMap', {
                center: center,
                zoom: 15,
                controls: ['zoomControl']
            });
            
            const placemark = new ymaps.Placemark(center, {
                balloonContent: address
            }, {
                preset: 'islands#redShopIcon'
            });
            
            map.geoObjects.add(placemark);
            map.balloon.open(center, address);
        });
    }
    
    // ==================== ШАГ 3: ДАТА И ВРЕМЯ ====================
    function initStep3DateTime() {
        console.log('[CHECKOUT STEP 3] Initializing datetime step...');
        
        const checkoutState = getCheckoutState();
        
        const dateInput = document.getElementById('deliveryDate');
        const timeSelect = document.getElementById('deliveryTime');
        const nextBtn = document.getElementById('checkoutNext3');
        const titleEl = document.getElementById('deliveryTimeTitle');
        const subtitleEl = document.getElementById('deliveryTimeSubtitle');
        const descriptionEl = document.getElementById('deliveryTimeDescription');
        const dateLabelEl = document.getElementById('deliveryDateLabel');
        const timeLabelEl = document.getElementById('deliveryTimeLabel');
        
        if (!dateInput || !timeSelect || !nextBtn) {
            console.error('[CHECKOUT STEP 3] Elements not found');
            return;
        }
        
        // Обновляем текст в зависимости от типа получения
        if (checkoutState.deliveryType === 'pickup') {
            if (titleEl) titleEl.textContent = 'Дата и время забора заказа';
            if (subtitleEl) subtitleEl.textContent = 'Выберите дату и время забора заказа';
            if (descriptionEl) descriptionEl.textContent = 'Укажите удобную дату и время для забора заказа';
            if (dateLabelEl) dateLabelEl.textContent = 'Дата забора заказа';
            if (timeLabelEl) timeLabelEl.textContent = 'Время забора заказа';
        } else {
            if (titleEl) titleEl.textContent = 'Дата и время доставки';
            if (subtitleEl) subtitleEl.textContent = 'Выберите дату и время доставки';
            if (descriptionEl) descriptionEl.textContent = 'Укажите удобную дату и время для доставки заказа';
            if (dateLabelEl) dateLabelEl.textContent = 'Дата доставки';
            if (timeLabelEl) timeLabelEl.textContent = 'Время доставки';
        }
        
        // Доступные временные слоты
        const timeSlots = [
            { value: '09:00-12:00', start: 9, end: 12 },
            { value: '12:00-15:00', start: 12, end: 15 },
            { value: '15:00-18:00', start: 15, end: 18 },
            { value: '18:00-21:00', start: 18, end: 21 }
        ];
        
        // Устанавливаем минимальную дату (сегодня)
        const today = new Date();
        dateInput.min = today.toISOString().split('T')[0];
        
        // Восстанавливаем сохранённые значения
        if (checkoutState.deliveryDate) dateInput.value = checkoutState.deliveryDate;
        
        // Обновляем список времени
        function updateTimeSlots() {
            const selectedDate = dateInput.value;
            const isToday = selectedDate === today.toISOString().split('T')[0];
            const currentHour = new Date().getHours();
            
            timeSelect.innerHTML = '<option value="">Выберите время</option>';
            
            timeSlots.forEach(slot => {
                // Если сегодня, фильтруем прошедшие слоты
                if (isToday && slot.end <= currentHour) return;
                
                const option = document.createElement('option');
                option.value = slot.value;
                option.textContent = slot.value;
                timeSelect.appendChild(option);
            });
            
            // Восстанавливаем выбранное время
            if (checkoutState.deliveryTime) {
                const exists = Array.from(timeSelect.options).some(o => o.value === checkoutState.deliveryTime);
                if (exists) timeSelect.value = checkoutState.deliveryTime;
            }
            
            validate();
        }
        
        // Валидация
        function validate() {
            const hasDate = !!dateInput.value;
            const hasTime = !!timeSelect.value;
            
            // Проверяем, что дата не прошедшая
            let isDateValid = true;
            if (hasDate) {
                const selectedDate = new Date(dateInput.value + 'T00:00:00');
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                
                if (selectedDate < today) {
                    isDateValid = false;
                    // Очищаем выбранную дату, если она прошедшая
                    dateInput.value = '';
                    checkoutState.deliveryDate = null;
                    timeSelect.innerHTML = '<option value="">Выберите время</option>';
                    checkoutState.deliveryTime = null;
                    timeSelect.value = '';
                    
                    const message = checkoutState.deliveryType === 'pickup' 
                        ? 'Нельзя выбрать прошедшую дату для забора заказа' 
                        : 'Нельзя выбрать прошедшую дату для доставки';
                    showToast(message, 'error');
                }
            }
            
            const isValid = hasDate && hasTime && isDateValid;
            nextBtn.disabled = !isValid;
            return isValid;
        }
        
        // Обработчики
        dateInput.addEventListener('change', () => {
            const selectedDate = new Date(dateInput.value + 'T00:00:00');
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            
            // Проверяем, что выбранная дата не прошедшая
            if (selectedDate < today) {
                dateInput.value = '';
                checkoutState.deliveryDate = null;
                timeSelect.innerHTML = '<option value="">Выберите время</option>';
                checkoutState.deliveryTime = null;
                timeSelect.value = '';
                
                const message = checkoutState.deliveryType === 'pickup' 
                    ? 'Нельзя выбрать прошедшую дату для забора заказа' 
                    : 'Нельзя выбрать прошедшую дату для доставки';
                showToast(message, 'error');
            } else {
                checkoutState.deliveryDate = dateInput.value;
            }
            updateTimeSlots();
            validate();
        });
        
        timeSelect.addEventListener('change', () => {
            checkoutState.deliveryTime = timeSelect.value;
            validate();
        });
        
        // Инициализация
        updateTimeSlots();
        
        // Кнопка "Далее"
        nextBtn.onclick = () => {
            // Дополнительная проверка перед переходом
            if (dateInput.value) {
                const selectedDate = new Date(dateInput.value + 'T00:00:00');
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                
                if (selectedDate < today) {
                    const message = checkoutState.deliveryType === 'pickup' 
                        ? 'Нельзя выбрать прошедшую дату для забора заказа' 
                        : 'Нельзя выбрать прошедшую дату для доставки';
                    showToast(message, 'error');
                    dateInput.value = '';
                    checkoutState.deliveryDate = null;
                    timeSelect.innerHTML = '<option value="">Выберите время</option>';
                    checkoutState.deliveryTime = null;
                    timeSelect.value = '';
                    validate();
                    return;
                }
            }
            
            if (!validate()) {
                const message = checkoutState.deliveryType === 'pickup' 
                    ? 'Выберите дату и время забора заказа' 
                    : 'Выберите дату и время доставки';
                showToast(message, 'error');
                return;
            }
            checkoutState.deliveryDate = dateInput.value;
            checkoutState.deliveryTime = timeSelect.value;
            showCheckoutStep(4);
        };
        
        // Кнопка назад
        const backBtn = document.querySelector('#checkoutStep3 .back-to-step');
        if (backBtn) {
            backBtn.onclick = () => showCheckoutStep(2);
        }
    }
    
    // ==================== ШАГ 4: ПОДТВЕРЖДЕНИЕ ====================
    function initStep4Confirm() {
        console.log('[CHECKOUT STEP 4] Initializing confirmation step...');
        
        const checkoutState = getCheckoutState();
        const state = getState();
        const api = getApi();
        
        // Заполняем информацию
        const confirmPhone = document.getElementById('confirmPhone');
        const confirmRecipient = document.getElementById('confirmRecipient');
        const confirmAddress = document.getElementById('confirmAddress');
        const confirmComment = document.getElementById('confirmComment');
        const confirmCommentRow = document.getElementById('confirmCommentRow');
        const confirmDeliveryDate = document.getElementById('confirmDeliveryDate');
        const confirmDeliveryTime = document.getElementById('confirmDeliveryTime');
        const orderItemsSummary = document.getElementById('orderItemsSummary');
        const confirmItemsCount = document.getElementById('confirmItemsCount');
        const confirmSubtotal = document.getElementById('confirmSubtotal');
        const confirmDeliveryFee = document.getElementById('confirmDeliveryFee');
        const confirmTotal = document.getElementById('confirmTotal');
        
        // Контактная информация
        if (confirmPhone) confirmPhone.textContent = checkoutState.phone || 'Не указан';
        if (confirmRecipient) confirmRecipient.textContent = checkoutState.recipientName || 'Не указано';
        if (confirmAddress) confirmAddress.textContent = checkoutState.address || 'Не указан';
        
        if (checkoutState.deliveryComment) {
            if (confirmComment) confirmComment.textContent = checkoutState.deliveryComment;
            if (confirmCommentRow) confirmCommentRow.hidden = false;
        } else {
            if (confirmCommentRow) confirmCommentRow.hidden = true;
        }
        
        // Дата и время
        if (confirmDeliveryDate && checkoutState.deliveryDate) {
            const parts = checkoutState.deliveryDate.split('-');
            if (parts.length === 3) {
                const date = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                confirmDeliveryDate.textContent = date.toLocaleDateString('ru-RU', {
                    day: 'numeric', month: 'long', year: 'numeric'
                });
            }
        }
        if (confirmDeliveryTime) confirmDeliveryTime.textContent = checkoutState.deliveryTime || 'Не указано';
        
        // Товары
        const items = state.cart.filter(item => 
            (item.shop_id || item.shopId) === checkoutState.shopId
        );
        
        if (orderItemsSummary) {
            orderItemsSummary.innerHTML = items.map(item => {
                const price = item.product_discount_price || item.product_price;
                const imageUrl = getMediaUrl(item.product_image_url || '');
                return `
                    <div class="order-item-summary">
                        <div class="order-item-image">
                            ${item.product_image_url 
                                ? `<img src="${imageUrl}" alt="${item.product_name}">`
                                : '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;">🌸</div>'
                            }
                        </div>
                        <div class="order-item-details">
                            <div class="order-item-name">${item.product_name}</div>
                            <div class="order-item-meta">
                                <span>${item.quantity} шт.</span>
                                <span class="order-item-price">${formatPrice(price * item.quantity)}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Расчёт итогов
        const count = items.reduce((sum, item) => sum + item.quantity, 0);
        const itemsTotal = items.reduce((sum, item) => {
            const price = item.product_discount_price || item.product_price;
            return sum + (parseFloat(price) * item.quantity);
        }, 0);
        
        let deliveryFee = DELIVERY_FEE;
        let promoDiscount = checkoutState.promoDiscount || 0;
        
        if (checkoutState.promoType === 'free_delivery') {
            deliveryFee = 0;
        }
        
        const total = itemsTotal - promoDiscount + deliveryFee;
        
        if (confirmItemsCount) confirmItemsCount.textContent = count;
        if (confirmSubtotal) confirmSubtotal.textContent = formatPrice(itemsTotal);
        if (confirmDeliveryFee) confirmDeliveryFee.textContent = formatPrice(deliveryFee);
        if (confirmTotal) confirmTotal.textContent = formatPrice(total);
        
        // Промокод
        initPromoCode(itemsTotal, api);
        
        // Кнопка подтверждения
        const submitBtn = document.getElementById('submitOrderBtn');
        if (submitBtn) {
            submitBtn.onclick = submitOrder;
        }
        
        // Кнопка назад
        const backBtn = document.querySelector('#checkoutStep4 .back-to-step');
        if (backBtn) {
            backBtn.onclick = () => showCheckoutStep(3);
        }
    }
    
    // Обработка промокода
    function initPromoCode(itemsTotal, api) {
        const checkoutState = getCheckoutState();
        
        const promoInput = document.getElementById('promoCodeInput');
        const applyBtn = document.getElementById('applyPromoBtn');
        const promoMessage = document.getElementById('promoCodeMessage');
        const promoApplied = document.getElementById('promoCodeApplied');
        const promoText = document.getElementById('promoCodeText');
        const removeBtn = document.getElementById('removePromoBtn');
        
        if (!promoInput || !applyBtn) return;
        
        // Если промокод уже применён
        if (checkoutState.promoCode) {
            promoInput.value = checkoutState.promoCode;
            if (promoApplied) {
                promoApplied.hidden = false;
                if (promoText) promoText.textContent = checkoutState.promoCode;
            }
            if (promoMessage) promoMessage.hidden = true;
        }
        
        // Удаление промокода
        if (removeBtn) {
            removeBtn.onclick = () => {
                checkoutState.promoCode = null;
                checkoutState.promoDiscount = 0;
                checkoutState.promoType = null;
                initStep4Confirm(); // Перерисовываем
            };
        }
        
        // Применение промокода
        applyBtn.onclick = async () => {
            const code = promoInput.value.trim().toUpperCase();
            if (!code) {
                showToast('Введите промокод', 'warning');
                return;
            }
            
            applyBtn.disabled = true;
            applyBtn.textContent = 'Проверка...';
            
            try {
                const orders = await api.getOrders();
                const isFirstOrder = !orders || orders.length === 0;
                
                const result = await api.validatePromoCode(
                    code,
                    checkoutState.shopId,
                    itemsTotal,
                    isFirstOrder
                );
                
                if (result.valid) {
                    checkoutState.promoCode = code;
                    checkoutState.promoDiscount = parseFloat(result.discount_amount) || 0;
                    checkoutState.promoType = result.discount_type;
                    showToast(result.message || 'Промокод применён!', 'success');
                    initStep4Confirm(); // Перерисовываем
                } else {
                    if (promoMessage) {
                        promoMessage.textContent = result.message || 'Промокод недействителен';
                        promoMessage.className = 'promo-code-message error';
                        promoMessage.hidden = false;
                    }
                    showToast(result.message || 'Промокод недействителен', 'error');
                }
            } catch (error) {
                console.error('[PROMO] Error:', error);
                showToast('Ошибка проверки промокода', 'error');
            } finally {
                applyBtn.disabled = false;
                applyBtn.textContent = 'Применить';
            }
        };
        
        // Enter в поле промокода
        promoInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') applyBtn.click();
        });
    }
    
    // ==================== ОТПРАВКА ЗАКАЗА ====================
    async function submitOrder() {
        console.log('[CHECKOUT] Submitting order...');
        
        const checkoutState = getCheckoutState();
        const state = getState();
        const api = getApi();
        
        const submitBtn = document.getElementById('submitOrderBtn');
        const btnText = document.getElementById('submitOrderBtnText');
        const btnLoading = document.getElementById('submitOrderBtnLoading');
        
        if (!submitBtn || submitBtn.disabled) return;
        
        // Блокируем кнопку
        submitBtn.disabled = true;
        if (btnText) btnText.hidden = true;
        if (btnLoading) btnLoading.hidden = false;
        
        try {
            // Подготавливаем данные заказа
            const items = state.cart.filter(item => 
                (item.shop_id || item.shopId) === checkoutState.shopId
            );
            
            const itemsTotal = items.reduce((sum, item) => {
                const price = item.product_discount_price || item.product_price;
                return sum + (parseFloat(price) * item.quantity);
            }, 0);
            
            let deliveryFee = DELIVERY_FEE;
            if (checkoutState.promoType === 'free_delivery') {
                deliveryFee = 0;
            }
            
            const orderData = {
                shop_id: checkoutState.shopId,
                items: items.map(item => ({
                    product_id: item.product_id,
                    quantity: item.quantity,
                    price: item.product_discount_price || item.product_price
                })),
                recipient_phone: checkoutState.phone,
                recipient_name: checkoutState.recipientName,
                delivery_address: checkoutState.address,
                delivery_latitude: checkoutState.latitude,
                delivery_longitude: checkoutState.longitude,
                delivery_comment: checkoutState.deliveryComment || null,
                delivery_date: checkoutState.deliveryDate,
                delivery_time: checkoutState.deliveryTime,
                delivery_type: checkoutState.deliveryType || 'delivery',  // 'delivery' или 'pickup'
                delivery_fee: deliveryFee,
                promo_code: checkoutState.promoCode || null,
                promo_discount: checkoutState.promoDiscount || 0,
                subtotal: itemsTotal,
                total: itemsTotal - (checkoutState.promoDiscount || 0) + deliveryFee
            };
            
            console.log('[CHECKOUT] Order data:', orderData);
            
            // Отправляем заказ
            const result = await api.createOrder(orderData);
            
            console.log('[CHECKOUT] Order created:', result);
            
            // Сохраняем данные пользователя для следующих заказов
            saveUserData(checkoutState);
            
            // Корзина очищается на бэкенде при создании заказа
            // Просто обновляем UI
            if (window.loadCart) await window.loadCart();
            if (window.renderCart) window.renderCart();
            
            // Закрываем модальное окно оформления заказа
            closeCheckoutModal();
            
            // Показываем модальное окно подтверждения заказа
            showOrderSuccessModal(result, checkoutState, itemsTotal, deliveryFee);
            
        } catch (error) {
            console.error('[CHECKOUT] Error creating order:', error);
            showToast(error.message || 'Ошибка при создании заказа', 'error');
        } finally {
            submitBtn.disabled = false;
            if (btnText) btnText.hidden = false;
            if (btnLoading) btnLoading.hidden = true;
        }
    }
    
    // ==================== ЗАКРЫТИЕ МОДАЛЬНОГО ОКНА ====================
    function closeCheckoutModal() {
        console.log('[CHECKOUT] Closing checkout modal...');
        const modal = document.getElementById('checkoutModal');
        if (modal) {
            modal.hidden = true;
            console.log('[CHECKOUT] Modal hidden');
        }
        
        // Восстанавливаем основную кнопку "Назад" ПЕРЕД сбросом состояния
        restoreMainBackButton();
        
        // Очищаем карту
        if (deliveryMap) {
            try { 
                deliveryMap.destroy(); 
            } catch(e) {
                console.warn('[CHECKOUT] Error destroying map:', e);
            }
            deliveryMap = null;
            deliveryMapPlacemark = null;
        }
        
        // Загружаем сохранённые данные для следующего заказа
        const savedData = getSavedUserData();
        
        // Сбрасываем состояние, но сохраняем пользовательские данные
        const checkoutState = getCheckoutState();
        checkoutState.step = 1;
        // Сохраняем данные пользователя из localStorage
        checkoutState.phone = savedData?.phone || null;
        checkoutState.address = savedData?.address || null;
        checkoutState.recipientName = savedData?.recipientName || '';
        checkoutState.deliveryComment = savedData?.deliveryComment || '';
        checkoutState.latitude = savedData?.latitude || null;
        checkoutState.longitude = savedData?.longitude || null;
        // Сбрасываем остальное
        checkoutState.addressIsValid = null;
        checkoutState.deliveryDate = null;
        checkoutState.deliveryTime = null;
        checkoutState.shopId = null;
        checkoutState.shopCity = null;
        checkoutState.items = [];
        checkoutState.promoCode = null;
        checkoutState.promoDiscount = 0;
        checkoutState.promoType = null;
        
        console.log('[CHECKOUT] Checkout modal closed, state reset');
    }
    
    // ==================== МОДАЛЬНОЕ ОКНО ПОДТВЕРЖДЕНИЯ ЗАКАЗА ====================
    function showOrderSuccessModal(orderResult, checkoutState, itemsTotal, deliveryFee) {
        console.log('[CHECKOUT] Showing order success modal');
        
        const modal = document.getElementById('orderSuccessModal');
        if (!modal) {
            console.error('[CHECKOUT] Order success modal not found');
            showToast('Заказ успешно оформлен! 🎉', 'success');
            if (window.navigateTo) {
                setTimeout(() => window.navigateTo('catalog'), 500);
            }
            return;
        }
        
        // Форматируем дату создания заказа
        const now = new Date();
        const orderDate = now.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
        const orderTime = now.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // Заполняем данные
        const dateEl = document.getElementById('orderSuccessDate');
        if (dateEl) {
            dateEl.textContent = `${orderDate}, ${orderTime}`;
        }
        
        const totalEl = document.getElementById('orderSuccessTotal');
        if (totalEl) {
            const total = itemsTotal - (checkoutState.promoDiscount || 0) + deliveryFee;
            totalEl.textContent = formatPrice(total);
        }
        
        const recipientEl = document.getElementById('orderSuccessRecipient');
        if (recipientEl) {
            recipientEl.textContent = checkoutState.recipientName || 'Не указано';
        }
        
        const contactsEl = document.getElementById('orderSuccessContacts');
        if (contactsEl) {
            const phone = checkoutState.phone || '';
            const email = checkoutState.recipientEmail || '';
            contactsEl.textContent = phone + (email ? `, ${email}` : '');
        }
        
        const addressEl = document.getElementById('orderSuccessAddress');
        if (addressEl) {
            addressEl.textContent = checkoutState.address || 'Не указан';
        }
        
        // Кнопка "Продолжить покупки"
        const continueBtn = document.getElementById('orderSuccessContinueBtn');
        if (continueBtn) {
            continueBtn.onclick = () => {
                modal.hidden = true;
                if (window.navigateTo) {
                    window.navigateTo('catalog');
                }
            };
        }
        
        // Показываем модальное окно
        modal.hidden = false;
        
        // Скрываем кнопку "Назад" Telegram
        const tg = getTg();
        if (tg && tg.BackButton) {
            tg.BackButton.hide();
        }
    }
    
    // ==================== ЭКСПОРТ ====================
    window.checkout = checkout;
    window.showCheckoutStep = showCheckoutStep;
    window.submitOrder = submitOrder;
    window.closeCheckoutModal = closeCheckoutModal;
    window.DELIVERY_FEE = DELIVERY_FEE;
    
    // Для модульной системы
    window.App = window.App || {};
    window.App.checkout = {
        checkout,
        showCheckoutStep,
        submitOrder,
        closeCheckoutModal,
        DELIVERY_FEE,
        getCheckoutState
    };
    
    console.log('[CHECKOUT] Module loaded successfully ✅');
})();

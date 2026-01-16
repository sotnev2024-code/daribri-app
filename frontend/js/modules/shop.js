/**
 * Shop Module - страница магазина
 */

(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    const getApi = () => window.api;
    
    // Константа города (приложение работает только в Екатеринбурге)
    const APP_CITY = 'Екатеринбург';
    
    /**
     * Нормализует адрес для отображения
     * Убирает любые упоминания города из адреса и добавляет "г. Екатеринбург" в начало
     * @param {string} address - исходный адрес
     * @returns {string} - нормализованный адрес в формате "г. Екатеринбург, {адрес}"
     */
    function normalizeAddress(address) {
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
        // Это обработает случаи типа "г. Шаманский переулок 1, ..." или "г. Шаманский переулок 1 ..."
        // Сначала пробуем убрать с запятой
        cleanedAddress = cleanedAddress.replace(/^г\.?\s*[^,]+,\s*/i, '').trim();
        // Затем пробуем убрать без запятой (если после "г. " идет слово, за которым идет "г. " или "ул. " или "улица")
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
    
    // Открытие страницы магазина
    async function openShopPage(shopId) {
        const state = getState();
        if (!shopId || !state) return;
        
        state.currentShopId = shopId;
        
        if (window.navigateTo) {
            window.navigateTo('shop');
        }
        
        await loadShopData(shopId);
    }
    
    // Загрузка данных магазина
    async function loadShopData(shopId) {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        const api = getApi();
        if (!state || !elements || !api) return;
        
        console.log('[SHOP] loadShopData called with shopId:', shopId);
        
        try {
            const shop = await api.getShop(shopId);
            
            const shopPage = document.getElementById('shopPage');
            if (!shopPage) {
                console.error('[SHOP] shopPage element not found');
                return;
            }
            
            // Заполняем данные магазина
            const shopNameEl = document.getElementById('shopPageName');
            const shopAvatarEl = document.getElementById('shopPageAvatar');
            const shopAddressEl = document.getElementById('shopPageAddress');
            const shopRatingEl = document.getElementById('shopPageRating');
            const shopOrdersCountEl = document.getElementById('shopPageOrdersCount');
            const shopSinceDateEl = document.getElementById('shopPageSinceDate');
            const shopTitleEl = document.getElementById('shopPageTitle');
            const shopLocationSection = document.getElementById('shopLocationSection');
            
            console.log('[SHOP] Shop data loaded:', shop);
            
            if (shopNameEl) shopNameEl.textContent = shop.name || 'Магазин';
            if (shopTitleEl) shopTitleEl.textContent = shop.name || 'Магазин';
            
            const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
            
            if (shopAvatarEl) {
                if (shop.photo_url) {
                    const photoUrl = getMediaUrl(shop.photo_url);
                    shopAvatarEl.innerHTML = `<img src="${photoUrl}" alt="${shop.name}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
                } else {
                    shopAvatarEl.textContent = '🏪';
                }
            }
            
            // Показываем секцию локации, если есть адрес
            if (shopLocationSection) {
                if (shop.address) {
                    shopLocationSection.hidden = false;
                    // Нормализуем адрес: всегда используем "Екатеринбург" как город
                    const normalizedAddress = normalizeAddress(shop.address);
                    if (shopAddressEl) shopAddressEl.textContent = normalizedAddress;
                } else {
                    shopLocationSection.hidden = true;
                }
            }
            
            if (shopRatingEl) {
                const rating = shop.average_rating || 0;
                shopRatingEl.textContent = parseFloat(rating).toFixed(1);
            }
            
            if (shopOrdersCountEl) {
                shopOrdersCountEl.textContent = shop.orders_count || 0;
            }
            
            if (shopSinceDateEl && shop.created_at) {
                const createdDate = new Date(shop.created_at);
                shopSinceDateEl.textContent = `На Дарибри с ${createdDate.toLocaleDateString('ru-RU', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                })}`;
            }
            
            // Описание магазина
            const shopDescriptionSection = document.getElementById('shopDescriptionSection');
            const shopDescriptionEl = document.getElementById('shopPageDescription');
            if (shopDescriptionSection && shopDescriptionEl) {
                if (shop.description && shop.description.trim()) {
                    shopDescriptionEl.textContent = shop.description;
                    shopDescriptionSection.hidden = false;
                } else {
                    shopDescriptionSection.hidden = true;
                }
            }
            
            // Расписание работы
            const shopScheduleSection = document.getElementById('shopScheduleSection');
            const shopScheduleEl = document.getElementById('shopPageSchedule');
            if (shopScheduleSection && shopScheduleEl) {
                if (shop.working_hours || shop.schedule) {
                    const schedule = shop.working_hours || shop.schedule;
                    let scheduleText = '';
                    
                    // Если расписание - JSON строка, парсим его
                    try {
                        const scheduleData = typeof schedule === 'string' ? JSON.parse(schedule) : schedule;
                        if (typeof scheduleData === 'object' && !Array.isArray(scheduleData)) {
                            // Форматируем расписание из объекта
                            const daysOrder = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
                            const daysNames = {
                                'monday': 'Пн',
                                'tuesday': 'Вт',
                                'wednesday': 'Ср',
                                'thursday': 'Чт',
                                'friday': 'Пт',
                                'saturday': 'Сб',
                                'sunday': 'Вс'
                            };
                            
                            scheduleText = daysOrder
                                .map(day => {
                                    const hours = scheduleData[day] || scheduleData[daysNames[day]?.toLowerCase()];
                                    return hours ? `${daysNames[day]}: ${hours}` : null;
                                })
                                .filter(Boolean)
                                .join('<br>');
                        } else {
                            scheduleText = schedule;
                        }
                    } catch (e) {
                        // Если не JSON, используем как текст (с поддержкой переносов строк)
                        scheduleText = String(schedule).replace(/\n/g, '<br>');
                    }
                    
                    if (scheduleText && scheduleText.trim()) {
                        shopScheduleEl.innerHTML = scheduleText.trim();
                        shopScheduleSection.hidden = false;
                    } else {
                        shopScheduleSection.hidden = true;
                    }
                } else {
                    shopScheduleSection.hidden = true;
                }
            }
            
            // Загружаем карту
            const mapContainer = document.getElementById('shopMapContainer');
            if (mapContainer) {
                await loadShopMap(mapContainer, shop);
            }
            
            // Загружаем отзывы
            await loadShopReviews(shopId);
            
            // Загружаем товары
            await loadShopProducts(shopId);
            
        } catch (error) {
            console.error('[SHOP] Error loading shop data:', error);
            const utils = getUtils();
            if (utils.showToast) utils.showToast('Ошибка загрузки магазина', 'error');
        }
    }
    
    // Загрузка карты магазина
    async function loadShopMap(container, shop) {
        if (!shop.address) {
            container.innerHTML = '<p>Адрес не указан</p>';
            return;
        }
        
        const address = shop.address;
        const city = shop.city || 'Екатеринбург';
        
        // Если есть координаты, используем их
        // Yandex Maps Widget API параметр pt использует формат lon,lat (долгота, широта)
        if (shop.latitude && shop.longitude) {
            const lat = parseFloat(shop.latitude);
            const lon = parseFloat(shop.longitude);
            
            // Проверяем, что координаты валидны (для России: lat ~50-80, lon ~20-180)
            if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
                // Yandex Maps Widget API: pt=lon,lat (долгота, широта)
                const mapUrl = `https://yandex.ru/map-widget/v1/?z=15&pt=${lon},${lat}&l=map&lang=ru_RU`;
                
                container.innerHTML = `
                    <iframe 
                        src="${mapUrl}" 
                        width="100%" 
                        height="300" 
                        frameborder="0" 
                        style="border-radius: 12px;"
                        allowfullscreen="true">
                    </iframe>
                `;
                return;
            }
        }
        
        // Если координат нет или они невалидны, используем геокодирование адреса
        try {
            // Пытаемся получить координаты через API геокодирования
            const geocodeUrl = `/api/geocode/geocode?address=${encodeURIComponent(address)}${city ? `&city=${encodeURIComponent(city)}` : ''}`;
            const response = await fetch(geocodeUrl);
            
            if (response.ok) {
                const data = await response.json();
                if (data.coordinates && data.coordinates.lat && data.coordinates.lng) {
                    const lat = parseFloat(data.coordinates.lat);
                    const lon = parseFloat(data.coordinates.lng);
                    
                    // Yandex Maps Widget API: pt=lon,lat (долгота, широта)
                    const mapUrl = `https://yandex.ru/map-widget/v1/?z=15&pt=${lon},${lat}&l=map&lang=ru_RU`;
                    
                    container.innerHTML = `
                        <iframe 
                            src="${mapUrl}" 
                            width="100%" 
                            height="300" 
                            frameborder="0" 
                            style="border-radius: 12px;"
                            allowfullscreen="true">
                        </iframe>
                    `;
                    return;
                }
            }
        } catch (error) {
            console.error('[SHOP] Error geocoding address:', error);
        }
        
        // Fallback: используем поиск по адресу через Yandex Maps (параметр text)
        const encodedAddress = encodeURIComponent(address + (city ? ` ${city}` : ''));
        const mapUrl = `https://yandex.ru/map-widget/v1/?z=15&text=${encodedAddress}&l=map&lang=ru_RU`;
        
        container.innerHTML = `
            <iframe 
                src="${mapUrl}" 
                width="100%" 
                height="300" 
                frameborder="0" 
                style="border-radius: 12px;"
                allowfullscreen="true">
            </iframe>
        `;
    }
    
    // Загрузка отзывов магазина
    async function loadShopReviews(shopId) {
        const api = getApi();
        if (!api) return;
        
        try {
            const reviews = await api.getShopReviews(shopId);
            const reviewsList = document.getElementById('shopReviewsList');
            const reviewsEmpty = document.getElementById('shopReviewsEmpty');
            const reviewsCount = document.getElementById('shopReviewsCount');
            
            console.log('[SHOP] Reviews loaded:', reviews?.length || 0);
            
            const totalReviews = reviews?.length || 0;
            
            if (reviewsCount) {
                reviewsCount.textContent = `(${totalReviews})`;
            }
            
            if (!reviewsList) return;
            
            if (!reviews || reviews.length === 0) {
                reviewsList.hidden = true;
                if (reviewsEmpty) reviewsEmpty.hidden = false;
                return;
            }
            
            reviewsList.hidden = false;
            if (reviewsEmpty) reviewsEmpty.hidden = true;
            
            // Показываем только последние 3 отзыва
            const lastReviews = reviews.slice(0, 3);
            
            let html = lastReviews.map(review => {
                const reviewDate = new Date(review.created_at);
                return `
                    <div class="shop-review-card">
                        <div class="review-header">
                            <div class="review-author">${review.user_name || 'Покупатель'}</div>
                            <div class="review-date">${reviewDate.toLocaleDateString('ru-RU')}</div>
                        </div>
                        <div class="review-rating">
                            ${'⭐'.repeat(review.rating || 0)}
                        </div>
                        ${review.comment ? `<div class="review-text">${review.comment}</div>` : ''}
                    </div>
                `;
            }).join('');
            
            // Если отзывов больше 3, показываем кнопку "Показать все"
            if (totalReviews > 3) {
                html += `
                    <button class="show-all-reviews-btn" onclick="window.showAllReviews && window.showAllReviews(${shopId})">
                        Показать все отзывы (${totalReviews})
                    </button>
                `;
            }
            
            reviewsList.innerHTML = html;
            
        } catch (error) {
            console.error('[SHOP] Error loading reviews:', error);
        }
    }
    
    // Загрузка товаров магазина
    async function loadShopProducts(shopId) {
        const api = getApi();
        const utils = getUtils();
        if (!api) return;
        
        try {
            const products = await api.getShopProducts(shopId);
            const productsGrid = document.getElementById('shopProductsGrid');
            const productsEmpty = document.getElementById('shopProductsEmpty');
            
            console.log('[SHOP] Products loaded:', products?.length || 0);
            
            if (!productsGrid) return;
            
            if (!products || products.length === 0) {
                productsGrid.hidden = true;
                if (productsEmpty) productsEmpty.hidden = false;
                return;
            }
            
            productsGrid.hidden = false;
            if (productsEmpty) productsEmpty.hidden = true;
            
            const formatPrice = utils.formatPrice || window.formatPrice || ((p) => `${p} ₽`);
            const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
            const catalogModule = window.App?.catalog;
            
            productsGrid.innerHTML = '';
            
            products.forEach(product => {
                if (catalogModule?.createProductCard) {
                    const card = catalogModule.createProductCard(product);
                    if (card) productsGrid.appendChild(card);
                } else {
                    // Если модуль каталога не загружен, выводим предупреждение
                    console.error('[SHOP] createProductCard not available, cannot render product:', product.id);
                }
            });
            
        } catch (error) {
            console.error('[SHOP] Error loading products:', error);
        }
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.shop = {
        openShopPage,
        loadShopData,
        loadShopMap,
        loadShopReviews,
        loadShopProducts
    };
    
    // Показать все отзывы в модальном окне
    async function showAllReviews(shopId) {
        const api = getApi();
        if (!api) return;
        
        try {
            const reviews = await api.getShopReviews(shopId);
            
            if (!reviews || reviews.length === 0) return;
            
            // Создаём модальное окно
            const modal = document.createElement('div');
            modal.className = 'reviews-modal';
            modal.innerHTML = `
                <div class="reviews-modal-overlay"></div>
                <div class="reviews-modal-content">
                    <div class="reviews-modal-header">
                        <h2>Все отзывы (${reviews.length})</h2>
                        <button class="reviews-modal-close">&times;</button>
                    </div>
                    <div class="reviews-modal-body">
                        ${reviews.map(review => {
                            const reviewDate = new Date(review.created_at);
                            return `
                                <div class="shop-review-card">
                                    <div class="review-header">
                                        <div class="review-author">${review.user_name || 'Покупатель'}</div>
                                        <div class="review-date">${reviewDate.toLocaleDateString('ru-RU')}</div>
                                    </div>
                                    <div class="review-rating">
                                        ${'⭐'.repeat(review.rating || 0)}
                                    </div>
                                    ${review.comment ? `<div class="review-text">${review.comment}</div>` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Закрытие модального окна
            const closeModal = () => {
                modal.remove();
            };
            
            modal.querySelector('.reviews-modal-overlay').onclick = closeModal;
            modal.querySelector('.reviews-modal-close').onclick = closeModal;
            
        } catch (error) {
            console.error('[SHOP] Error showing all reviews:', error);
        }
    }
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.openShopPage = openShopPage;
    window.loadShopData = loadShopData;
    window.loadShopMap = loadShopMap;
    window.loadShopReviews = loadShopReviews;
    window.loadShopProducts = loadShopProducts;
    window.showAllReviews = showAllReviews;
})();



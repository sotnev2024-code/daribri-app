/**
 * Catalog Module - каталог, категории, продукты, фильтры
 */

(function() {
    'use strict';
    
    // Получаем ссылки на общие ресурсы
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    const getApi = () => window.api;
    
    // Демо-данные (временные, можно удалить позже)
    function getDemoCategories() {
        return [
            { id: 1, name: 'Цветы', icon: '💐', children: [
                { id: 8, name: 'Монобукеты', icon: '🌷' },
                { id: 9, name: 'Авторские букеты', icon: '💮' },
                { id: 10, name: 'Букеты гиганты', icon: '🌸' },
            ]},
            { id: 2, name: 'Комнатные растения', icon: '🪴', children: [] },
            { id: 3, name: 'Кондитерские', icon: '🍰', children: [] },
            { id: 4, name: 'Съедобные букеты', icon: '🍓', children: [] },
            { id: 5, name: 'Вкусные наборы', icon: '🎁', children: [] },
            { id: 6, name: 'Чай и кофе', icon: '☕', children: [] },
        ];
    }
    
    function getDemoProducts() {
        return [
            { id: 1, name: 'Букет "Весенняя нежность"', price: 3500, discount_price: 2800, shop_name: 'FlowerLove', is_trending: true },
            { id: 2, name: 'Красные розы 51 шт', price: 8900, discount_price: null, shop_name: 'RoseGarden', is_trending: true },
            { id: 3, name: 'Монстера Deliciosa', price: 2200, discount_price: null, shop_name: 'GreenHome', is_trending: false },
            { id: 4, name: 'Торт "Красный бархат"', price: 2800, discount_price: 2100, shop_name: 'SweetDreams', is_trending: false },
            { id: 5, name: 'Орхидея Фаленопсис', price: 3500, discount_price: 2450, shop_name: 'OrchidWorld', is_trending: true },
            { id: 6, name: 'Набор макарун 12 шт', price: 1200, discount_price: null, shop_name: 'MacaronParis', is_trending: false },
        ];
    }
    
    // Маппинг slug категорий на русские названия файлов иконок
    function getCategoryIconFileName(category) {
        const iconMap = {
            'flowers': 'Цветы.PNG',
            'houseplants': 'Комнатные растения.png',
            'bakery': 'Кондитерски и пекарни.png',
            'edible-bouquets': 'Съедобные букеты.png',
            'tasty-sets': 'Вкусные наборы.PNG',
            'tea-coffee-sets': 'Наборы чая и кофе.png',
            'misc': 'Разное.PNG',
            'balloons': 'Шары.png',
            'masterclasses': 'Мастер классы.png',
            'master-classes': 'Мастер классы.png',
            'exotic-fruits': 'Экзотические фрукты и ягоды.png',
            'all': 'Все товары.png'
        };
        
        if (iconMap[category.slug]) {
            return iconMap[category.slug];
        }
        
        return category.name + '.png';
    }
    
    // Загрузка категорий
    async function loadCategories() {
        const state = getState();
        const elements = getElements();
        const api = getApi();
        
        console.log('[LOAD] loadCategories called, checking dependencies:', {
            hasState: !!state,
            hasElements: !!elements,
            hasApi: !!api
        });
        
        if (!state || !elements || !api) {
            console.error('[LOAD] loadCategories - Missing dependencies:', { state: !!state, elements: !!elements, api: !!api });
            return;
        }
        
        try {
            const categories = await api.getCategories();
            
            if (Array.isArray(categories)) {
                state.categories = categories;
            } else if (categories && Array.isArray(categories.items)) {
                state.categories = categories.items;
            } else if (categories && Array.isArray(categories.data)) {
                state.categories = categories.data;
            } else {
                console.warn('[LOAD] Неожиданный формат категорий:', categories);
                state.categories = [];
            }
            
            console.log('[LOAD] Categories loaded:', state.categories.length);
            renderCategories();
        } catch (error) {
            console.error('[LOAD] Error loading categories:', error);
            state.categories = getDemoCategories();
            renderCategories();
        }
    }
    
    // Загрузка продуктов
    async function loadProducts(options = {}) {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        const api = getApi();
        
        console.log('[LOAD] loadProducts called, checking dependencies:', {
            hasState: !!state,
            hasElements: !!elements,
            hasApi: !!api,
            hasProductsGrid: !!elements?.productsGrid
        });
        
        if (!state || !elements || !api) {
            console.error('[LOAD] Missing dependencies:', { state: !!state, elements: !!elements, api: !!api });
            return;
        }
        
        console.log('[LOAD] Loading products...', { category: state.currentCategory, options, filters: state.filters });
        state.loading = true;
        if (utils.showLoading) utils.showLoading(true);
        
        try {
            const filterOptions = {
                ...options,
                minPrice: state.filters.minPrice,
                maxPrice: state.filters.maxPrice,
                discounted: state.filters.discounted,
                trending: state.filters.trending,
            };
            
            let products;
            if (state.currentCategory !== 'all') {
                products = await api.getCategoryProducts(state.currentCategory, filterOptions);
            } else {
                products = await api.getProducts(filterOptions);
            }
            
            // Проверяем формат ответа
            if (Array.isArray(products)) {
                state.products = products;
            } else if (products && Array.isArray(products.items)) {
                state.products = products.items;
            } else if (products && Array.isArray(products.data)) {
                state.products = products.data;
            } else if (products && Array.isArray(products.products)) {
                state.products = products.products;
            } else {
                console.warn('[LOAD] Неожиданный формат товаров:', products);
                state.products = [];
            }
            
            // Нормализуем данные товаров - убеждаемся, что у всех есть media
            state.products = state.products.map(product => {
                // Если нет media, но есть primary_image, создаем media массив
                if (!product.media || !Array.isArray(product.media) || product.media.length === 0) {
                    if (product.primary_image) {
                        product.media = [{ url: product.primary_image, media_type: 'photo' }];
                    }
                }
                return product;
            });
            
            console.log('[LOAD] Products loaded:', state.products.length, 'category:', state.currentCategory);
            if (state.products.length > 0) {
                console.log('[LOAD] Sample product structure:', {
                    id: state.products[0].id,
                    name: state.products[0].name,
                    hasMedia: !!state.products[0].media,
                    mediaLength: state.products[0].media?.length || 0,
                    hasPrimaryImage: !!state.products[0].primary_image
                });
            }
            
            renderProducts();
        } catch (error) {
            console.error('[LOAD] Error loading products:', error);
            state.products = getDemoProducts();
            renderProducts();
        } finally {
            state.loading = false;
            if (utils.showLoading) utils.showLoading(false);
        }
    }
    
    // Применение фильтров на клиенте
    function applyClientFilters(products) {
        const state = getState();
        if (!state) return products;
        
        return products.filter(product => {
            const price = parseFloat(product.discount_price || product.price);
            if (state.filters.minPrice !== null && price < state.filters.minPrice) {
                return false;
            }
            if (state.filters.maxPrice !== null && price > state.filters.maxPrice) {
                return false;
            }
            
            if (state.filters.discounted && !product.discount_price) {
                return false;
            }
            
            if (state.filters.trending && !product.is_trending) {
                return false;
            }
            
            return true;
        });
    }
    
    // Фильтры
    function openFilterModal() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements?.filterModal) return;
        
        if (elements.filterMinPrice) {
            elements.filterMinPrice.value = state.filters.minPrice || '';
        }
        if (elements.filterMaxPrice) {
            elements.filterMaxPrice.value = state.filters.maxPrice || '';
        }
        if (elements.filterDiscounted) {
            elements.filterDiscounted.checked = state.filters.discounted || false;
        }
        if (elements.filterTrending) {
            elements.filterTrending.checked = state.filters.trending || false;
        }
        
        elements.filterModal.hidden = false;
    }
    
    function closeFilterModal() {
        const elements = getElements();
        if (elements?.filterModal) {
            elements.filterModal.hidden = true;
        }
    }
    
    function applyFilters() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements) return;
        
        state.filters.minPrice = elements.filterMinPrice?.value ? parseFloat(elements.filterMinPrice.value) : null;
        state.filters.maxPrice = elements.filterMaxPrice?.value ? parseFloat(elements.filterMaxPrice.value) : null;
        state.filters.discounted = elements.filterDiscounted?.checked || false;
        state.filters.trending = elements.filterTrending?.checked || false;
        
        console.log('[FILTERS] Applied filters:', state.filters);
        
        closeFilterModal();
        loadProducts();
    }
    
    function resetFilters() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements) return;
        
        state.filters = {
            minPrice: null,
            maxPrice: null,
            discounted: false,
            trending: false,
        };
        
        if (elements.filterMinPrice) elements.filterMinPrice.value = '';
        if (elements.filterMaxPrice) elements.filterMaxPrice.value = '';
        if (elements.filterDiscounted) elements.filterDiscounted.checked = false;
        if (elements.filterTrending) elements.filterTrending.checked = false;
        
        console.log('[FILTERS] Filters reset');
        
        closeFilterModal();
        loadProducts();
    }
    
    // Рендеринг категорий
    function renderCategories() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements?.categoriesSlider) return;
        
        const slider = elements.categoriesSlider;
        const staticButtons = slider.querySelectorAll('.category-chip');
        staticButtons.forEach((btn, i) => {
            if (i > 0) btn.remove(); // Оставляем только кнопку "Все"
        });
        
        state.categories.forEach(cat => {
            const btn = document.createElement('button');
            btn.className = 'category-chip';
            btn.dataset.category = cat.id;
            
            const getIconHTML = (category) => {
                const iconFileName = getCategoryIconFileName(category);
                const iconPath = `images/icons/${iconFileName}?v=3`;
                const emoji = category.icon || '📦';
                return `
                    <img src="${iconPath}" alt="${category.name}" class="category-icon-img" 
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-block';"
                         loading="lazy" style="display:block;">
                    <span class="category-icon-emoji" style="display:none; font-size: 1.1rem;">${emoji}</span>
                `;
            };
            
            btn.innerHTML = `
                <span class="chip-icon">
                    ${getIconHTML(cat)}
                </span>
                <span>${cat.name}</span>
            `;
            slider.appendChild(btn);
        });
    }
    
    // Рендеринг подкатегорий
    function renderSubcategories(category) {
        const state = getState();
        const elements = getElements();
        if (!state || !elements?.subcategoriesSection) return;
        
        if (!category.children || category.children.length === 0) {
            elements.subcategoriesSection.hidden = true;
            return;
        }
        
        elements.subcategoriesSection.hidden = false;
        elements.subcategoriesGrid.innerHTML = '';
        
        category.children.forEach(sub => {
            const card = document.createElement('button');
            card.className = 'subcategory-card';
            card.dataset.category = sub.id;
            
            card.innerHTML = `<span class="subcategory-name">${sub.name}</span>`;
            card.addEventListener('click', () => selectCategory(sub.id));
            elements.subcategoriesGrid.appendChild(card);
        });
    }
    
    // Поиск категории
    function findCategory(id) {
        const state = getState();
        if (!state) return null;
        
        for (const cat of state.categories) {
            if (cat.id == id) return cat;
            if (cat.children) {
                const found = cat.children.find(c => c.id == id);
                if (found) return found;
            }
        }
        return null;
    }
    
    // Выбор категории
    function selectCategory(categoryId) {
        const state = getState();
        const elements = getElements();
        if (!state || !elements) return;
        
        state.currentCategory = categoryId;
        
        elements.categoriesSlider.querySelectorAll('.category-chip').forEach(chip => {
            chip.classList.toggle('active', chip.dataset.category == categoryId);
        });
        
        if (categoryId === 'all') {
            if (elements.productsTitle) elements.productsTitle.textContent = 'Все товары';
            if (elements.subcategoriesSection) elements.subcategoriesSection.hidden = true;
            if (elements.bannerSection) elements.bannerSection.hidden = false;
        } else {
            const category = findCategory(categoryId);
            if (category) {
                if (elements.productsTitle) elements.productsTitle.textContent = category.name;
                renderSubcategories(category);
                if (elements.bannerSection) elements.bannerSection.hidden = true;
            }
        }
        
        loadProducts();
    }
    
    // Создание карточки товара
    function createProductCard(product) {
        const state = getState();
        const utils = getUtils();
        
        if (!product || !product.id) {
            console.error('[PRODUCT CARD] Invalid product data:', product);
            return null;
        }
        
        // Используем глобальные функции для избранного
        const isFavorite = window.isProductFavorite ? window.isProductFavorite(product.id) : false;
        
        // Проверяем наличие скидки
        const price = parseFloat(product.price) || 0;
        let discountPrice = null;
        if (product.discount_price !== null && product.discount_price !== undefined && product.discount_price !== '') {
            const parsed = parseFloat(product.discount_price);
            if (!isNaN(parsed) && parsed > 0) {
                discountPrice = parsed;
            }
        }
        const hasDiscount = discountPrice !== null && discountPrice < price;
        
        // Медиа контент - включаем все медиа (фото и видео)
        let media = [];
        if (product.media && Array.isArray(product.media) && product.media.length > 0) {
            media = product.media; // Включаем все медиа, включая видео
        } else if (product.primary_image) {
            media = [{ url: product.primary_image, media_type: 'photo' }];
        }
        
        // Слайдер показываем если есть больше одного медиа (фото или видео)
        const hasMultipleImages = media.length > 1;
        const card = document.createElement('div');
        card.className = 'product-card fade-in';
        card.dataset.productId = product.id;
        
        const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
        const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
        
        // Генерируем HTML для изображения
        let imageHTML = '';
        if (media.length > 0) {
            if (hasMultipleImages) {
                imageHTML = `
                    <div class="product-image-slider" data-product-id="${product.id}">
                        <div class="product-slider-track">
                            ${media.map((m, i) => {
                                const mediaUrl = getMediaUrl(m.url);
                                return `
                                <div class="product-slider-slide" data-index="${i}">
                                    ${m.media_type === 'video' 
                                        ? `<video src="${mediaUrl}" preload="metadata" muted playsinline loop style="width:100%;height:100%;object-fit:cover;"></video>` 
                                        : `<img src="${mediaUrl}" alt="${product.name}" loading="lazy">`
                                    }
                                </div>
                            `;
                            }).join('')}
                        </div>
                        <div class="product-slider-dots">
                            ${media.map((_, i) => `<span class="slider-dot ${i === 0 ? 'active' : ''}" data-index="${i}"></span>`).join('')}
                        </div>
                    </div>
                `;
            } else {
                const mediaUrl = getMediaUrl(media[0].url);
                imageHTML = `
                    <div class="product-single-image">
                        ${media[0].media_type === 'video'
                            ? `<video src="${mediaUrl}" preload="metadata" muted playsinline loop style="width:100%;height:100%;object-fit:cover;"></video>`
                            : `<img src="${mediaUrl}" alt="${product.name}" loading="lazy">`
                        }
                    </div>
                `;
            }
        } else {
            imageHTML = '<div class="product-image-placeholder">🌸</div>';
        }
        
        // Рейтинг и отзывы магазина
        // Отладка: проверяем, что данные приходят
        console.log('[PRODUCT CARD] Product data:', {
            id: product.id,
            name: product.name,
            shop_name: product.shop_name,
            shop_rating: product.shop_rating,
            shop_reviews_count: product.shop_reviews_count,
            shop_rating_type: typeof product.shop_rating,
            shop_reviews_count_type: typeof product.shop_reviews_count
        });
        
        // Пробуем разные варианты получения данных
        const shopRatingRaw = product.shop_rating || product.average_rating || 0;
        const shopReviewsCountRaw = product.shop_reviews_count || product.total_reviews || product.reviews_count || 0;
        
        const shopRating = typeof shopRatingRaw === 'string' 
            ? parseFloat(shopRatingRaw) 
            : typeof shopRatingRaw === 'number' 
                ? shopRatingRaw 
                : 0;
        const shopReviewsCount = typeof shopReviewsCountRaw === 'string' 
            ? parseInt(shopReviewsCountRaw) 
            : typeof shopReviewsCountRaw === 'number' 
                ? shopReviewsCountRaw 
                : 0;
        
        const hasRating = shopRating > 0 && !isNaN(shopRating);
        const ratingText = hasRating ? shopRating.toFixed(1) : '';
        const reviewsText = shopReviewsCount > 0 
            ? `(${shopReviewsCount} ${shopReviewsCount === 1 ? 'отзыв' : shopReviewsCount < 5 ? 'отзыва' : 'отзывов'})` 
            : '';
        const ratingDisplay = hasRating 
            ? `⭐ ${ratingText} ${reviewsText}` 
            : 'Нет оценки';
        
        console.log('[PRODUCT CARD] Parsed rating data:', {
            shopRatingRaw,
            shopRating,
            shopReviewsCountRaw,
            shopReviewsCount,
            hasRating,
            ratingDisplay
        });
        
        card.innerHTML = `
            <div class="product-image">
                ${imageHTML}
                <div class="product-badges">
                    ${product.is_trending ? '<span class="product-badge trending">🔥 Тренд</span>' : ''}
                    ${hasDiscount ? `<span class="product-badge discount">-${product.discount_percent || Math.round((1 - discountPrice / price) * 100)}%</span>` : ''}
                </div>
                <button class="product-favorite-btn ${isFavorite ? 'active' : ''}" data-product-id="${product.id}">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                    </svg>
                </button>
            </div>
            <div class="product-content">
                <div class="product-name">${product.name}</div>
                <div class="product-shop-price-section">
                    <div class="product-shop-info">
                        <span class="product-shop-name">${product.shop_name || 'Магазин'}</span>
                        <span class="product-shop-rating">${ratingDisplay}</span>
                    </div>
                    <div class="product-price-row">
                        <span class="product-current-price">${formatPrice(hasDiscount ? discountPrice : price)}</span>
                        ${hasDiscount ? `<span class="product-original-price">${formatPrice(price)}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
        
        // Инициализация слайдера
        if (media.length > 0) {
            if (hasMultipleImages) {
                initProductCardSlider(card, product.id, media.length);
            } else if (media[0]?.media_type === 'video') {
                // Для одного видео тоже инициализируем слайдер для управления воспроизведением
                initProductCardSlider(card, product.id, 1);
            }
        }
        
        // Обработчик клика на карточку
        card.addEventListener('click', (e) => {
            if (e.target.closest('.product-favorite-btn') || 
                e.target.closest('.product-slider-dots') || 
                e.target.closest('.slider-dot')) return;
            if (window.openProductPage) window.openProductPage(product.id);
        });
        
        // Обработчик избранного
        const favBtn = card.querySelector('.product-favorite-btn');
        if (favBtn) {
            favBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (window.toggleFavorite) window.toggleFavorite(product.id);
            });
        }
        
        return card;
    }
    
    // Инициализация слайдера для карточки товара
    function initProductCardSlider(card, productId, imageCount) {
        const slider = card.querySelector('.product-image-slider');
        if (!slider) {
            // Если слайдера нет, но есть одно видео, создаем слайдер
            const singleImage = card.querySelector('.product-single-image');
            if (singleImage && singleImage.querySelector('video')) {
                // Преобразуем single-image в slider для видео
                const video = singleImage.querySelector('video');
                const videoUrl = video.src;
                singleImage.outerHTML = `
                    <div class="product-image-slider" data-product-id="${productId}">
                        <div class="product-slider-track">
                            <div class="product-slider-slide" data-index="0">
                                <video src="${videoUrl}" preload="metadata" muted playsinline loop style="width:100%;height:100%;object-fit:cover;"></video>
                            </div>
                        </div>
                    </div>
                `;
                // Теперь находим новый слайдер и инициализируем
                const newSlider = card.querySelector('.product-image-slider');
                if (newSlider) {
                    initProductCardSlider(card, productId, 1);
                    return;
                }
            }
            return;
        }
        // Если только одно медиа и это не видео, не инициализируем слайдер
        if (imageCount <= 1) {
            const hasVideo = slider.querySelector('video');
            if (!hasVideo) {
                // Для одного изображения без видео не нужен слайдер
                return;
            }
        }
        
        const track = slider.querySelector('.product-slider-track');
        const slides = slider.querySelectorAll('.product-slider-slide');
        const dots = slider.querySelectorAll('.slider-dot');
        let currentIndex = 0;
        let startX = 0;
        let currentX = 0;
        let isDragging = false;
        let autoSlideInterval = null;
        
        function manageVideos(activeIndex) {
            slides.forEach((slide, index) => {
                const video = slide.querySelector('video');
                if (video) {
                    if (index === activeIndex) {
                        if (video.readyState >= 2) {
                            video.play().catch(err => {
                                if (err.name !== 'NotAllowedError' && err.name !== 'AbortError') {
                                    console.log('[VIDEO] Play error:', err);
                                }
                            });
                        } else {
                            const playWhenReady = () => {
                                video.play().catch(err => {
                                    if (err.name !== 'NotAllowedError' && err.name !== 'AbortError') {
                                        console.log('[VIDEO] Play error:', err);
                                    }
                                });
                                video.removeEventListener('loadeddata', playWhenReady);
                            };
                            video.addEventListener('loadeddata', playWhenReady);
                            video.load();
                        }
                    } else {
                        video.pause();
                        video.currentTime = 0;
                    }
                }
            });
        }
        
        function updatePosition(index) {
            if (index < 0) {
                currentIndex = imageCount - 1;
            } else if (index >= imageCount) {
                currentIndex = 0;
            } else {
                currentIndex = index;
            }
            
            track.style.transform = `translateX(-${currentIndex * 100}%)`;
            dots.forEach((dot, i) => dot.classList.toggle('active', i === currentIndex));
            manageVideos(currentIndex);
        }
        
        let startY = 0;
        let isHorizontalSwipe = null;
        
        slider.addEventListener('touchstart', (e) => {
            isDragging = true;
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isHorizontalSwipe = null;
            if (autoSlideInterval) clearInterval(autoSlideInterval);
        }, { passive: true });
        
        slider.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            
            const deltaX = e.touches[0].clientX - startX;
            const deltaY = e.touches[0].clientY - startY;
            
            // Определяем направление свайпа при первом движении
            if (isHorizontalSwipe === null && (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5)) {
                isHorizontalSwipe = Math.abs(deltaX) > Math.abs(deltaY);
            }
            
            // Только горизонтальный свайп обрабатываем каруселью
            if (isHorizontalSwipe) {
                e.preventDefault();
                currentX = deltaX;
                const offset = -currentIndex * 100 + (currentX / slider.offsetWidth) * 100;
                track.style.transform = `translateX(${offset}%)`;
                track.style.transition = 'none';
            }
        }, { passive: false });
        
        slider.addEventListener('touchend', () => {
            if (!isDragging) return;
            isDragging = false;
            track.style.transition = '';
            
            // Обрабатываем только если был горизонтальный свайп
            if (isHorizontalSwipe) {
                const threshold = slider.offsetWidth * 0.2;
                if (Math.abs(currentX) > threshold) {
                    if (currentX > 0) {
                        updatePosition(currentIndex - 1);
                    } else {
                        updatePosition(currentIndex + 1);
                    }
                } else {
                    updatePosition(currentIndex);
                }
            }
            
            currentX = 0;
            isHorizontalSwipe = null;
            startAutoSlide();
        });
        
        dots.forEach((dot, index) => {
            dot.addEventListener('click', (e) => {
                e.stopPropagation();
                updatePosition(index);
                startAutoSlide();
            });
        });
        
        function startAutoSlide() {
            if (autoSlideInterval) clearInterval(autoSlideInterval);
            autoSlideInterval = setInterval(() => {
                updatePosition(currentIndex + 1);
            }, 4000);
        }
        
        startAutoSlide();
        manageVideos(0);
        
        slider.addEventListener('mouseenter', () => {
            if (autoSlideInterval) clearInterval(autoSlideInterval);
        });
        
        slider.addEventListener('mouseleave', () => {
            startAutoSlide();
        });
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) {
                    slides.forEach(slide => {
                        const video = slide.querySelector('video');
                        if (video) video.pause();
                    });
                }
            });
        }, { threshold: 0.1 });
        
        observer.observe(slider);
    }
    
    // Инициализация делегирования событий для кнопок избранного
    function initFavoriteButtonsDelegation() {
        const elements = getElements();
        if (!elements) return;
        
        // Делегирование для основной сетки товаров
        if (elements.productsGrid) {
            elements.productsGrid.addEventListener('click', (e) => {
                const favBtn = e.target.closest('.product-favorite-btn');
                if (favBtn) {
                    e.stopPropagation();
                    const productId = favBtn.dataset.productId;
                    if (productId && window.toggleFavorite) {
                        window.toggleFavorite(parseInt(productId));
                    }
                }
            });
        }
        
        // Делегирование для сетки избранного
        if (elements.favoritesGrid) {
            elements.favoritesGrid.addEventListener('click', (e) => {
                const favBtn = e.target.closest('.product-favorite-btn');
                if (favBtn) {
                    e.stopPropagation();
                    const productId = favBtn.dataset.productId;
                    if (productId && window.toggleFavorite) {
                        window.toggleFavorite(parseInt(productId));
                    }
                }
            });
        }
        
        // Делегирование для товаров продавца
        const sellerProductsGrid = document.getElementById('sellerProductsGrid');
        if (sellerProductsGrid) {
            sellerProductsGrid.addEventListener('click', (e) => {
                const favBtn = e.target.closest('.product-favorite-btn');
                if (favBtn) {
                    e.stopPropagation();
                    const productId = favBtn.dataset.productId;
                    if (productId && window.toggleFavorite) {
                        window.toggleFavorite(parseInt(productId));
                    }
                }
            });
        }
        
        // Делегирование для товаров магазина
        const shopProductsGrid = document.getElementById('shopProductsGrid');
        if (shopProductsGrid) {
            shopProductsGrid.addEventListener('click', (e) => {
                const favBtn = e.target.closest('.product-favorite-btn');
                if (favBtn) {
                    e.stopPropagation();
                    const productId = favBtn.dataset.productId;
                    if (productId && window.toggleFavorite) {
                        window.toggleFavorite(parseInt(productId));
                    }
                }
            });
        }
    }
    
    // Рендеринг продуктов
    function renderProducts() {
        const state = getState();
        const elements = getElements();
        if (!state || !elements?.productsGrid) return;
        
        console.log('[RENDER] Rendering products...', { count: state.products.length });
        const grid = elements.productsGrid;
        grid.innerHTML = '';
        
        if (state.products.length === 0) {
            if (elements.emptyState) elements.emptyState.hidden = false;
            return;
        }
        
        if (elements.emptyState) elements.emptyState.hidden = true;
        
        state.products.forEach((product, index) => {
            // Убеждаемся, что используем правильную функцию создания карточки
            if (index === 0) {
                console.log('[RENDER] First product data for card:', {
                    id: product.id,
                    name: product.name,
                    shop_name: product.shop_name,
                    shop_rating: product.shop_rating,
                    shop_reviews_count: product.shop_reviews_count,
                    price: product.price,
                    discount_price: product.discount_price,
                    hasMedia: !!product.media,
                    mediaLength: product.media?.length || 0
                });
            }
            const card = createProductCard(product);
            if (card) {
                grid.appendChild(card);
            } else {
                console.error('[RENDER] Failed to create card for product:', product.id, product.name);
            }
        });
        
        if (window.App?.favorites?.updateFavoriteButtons) {
            window.App.favorites.updateFavoriteButtons();
        }
        
        // Убеждаемся, что все слайдеры инициализированы после рендеринга
        // Небольшая задержка для того, чтобы DOM обновился
        setTimeout(() => {
            const allSliders = grid.querySelectorAll('.product-image-slider');
            allSliders.forEach(slider => {
                const productId = slider.dataset.productId;
                if (productId) {
                    const card = slider.closest('.product-card');
                    if (card) {
                        const slides = slider.querySelectorAll('.product-slider-slide');
                        if (slides.length > 0 && !slider.dataset.initialized) {
                            // Инициализируем слайдер, если он еще не инициализирован
                            initProductCardSlider(card, parseInt(productId), slides.length);
                            slider.dataset.initialized = 'true';
                        }
                    }
                }
            });
        }, 100);
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.catalog = {
        loadCategories,
        loadProducts,
        renderCategories,
        renderProducts,
        renderSubcategories,
        selectCategory,
        findCategory,
        applyClientFilters,
        openFilterModal,
        closeFilterModal,
        applyFilters,
        resetFilters,
        getCategoryIconFileName,
        createProductCard,
        initProductCardSlider
    };
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.loadCategories = loadCategories;
    window.loadProducts = loadProducts;
    window.renderCategories = renderCategories;
    window.renderProducts = renderProducts;
    window.selectCategory = selectCategory;
    window.findCategory = findCategory;
    window.applyClientFilters = applyClientFilters;
    window.openFilterModal = openFilterModal;
    window.closeFilterModal = closeFilterModal;
    window.applyFilters = applyFilters;
    window.resetFilters = resetFilters;
    window.createProductCard = createProductCard;
    window.initFavoriteButtonsDelegation = initFavoriteButtonsDelegation;
    
    // Экспорт для модуля
    if (window.App) {
        window.App.catalog = window.App.catalog || {};
        window.App.catalog.initFavoriteButtonsDelegation = initFavoriteButtonsDelegation;
    }
})();


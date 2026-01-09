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
        if (!state || !elements || !api) return;
        
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
        if (!state || !elements || !api) return;
        
        console.log('[LOAD] Loading products...', { category: state.currentCategory, options, filters: state.filters });
        state.loading = true;
        if (utils.showLoading) utils.showLoading(true);
        
        try {
            const filterOptions = {
                ...options,
                minPrice: state.filters.minPrice,
                maxPrice: state.filters.maxPrice,
                inStock: state.filters.inStock !== false,
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
            
            console.log('[LOAD] Products loaded:', state.products.length);
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
            if (state.filters.inStock && (!product.quantity || product.quantity <= 0)) {
                return false;
            }
            
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
        if (elements.filterInStock) {
            elements.filterInStock.checked = state.filters.inStock !== false;
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
        state.filters.inStock = elements.filterInStock?.checked !== false;
        
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
            inStock: true,
        };
        
        if (elements.filterMinPrice) elements.filterMinPrice.value = '';
        if (elements.filterMaxPrice) elements.filterMaxPrice.value = '';
        if (elements.filterInStock) elements.filterInStock.checked = true;
        
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
        try {
            const state = getState();
            const utils = getUtils();
            if (!product || !product.id) {
                console.error('[PRODUCT CARD] Invalid product data:', product);
                return null;
            }
            
            // Используем глобальные функции для избранного (будут вынесены позже)
            const isFavorite = window.isProductFavorite ? window.isProductFavorite(product.id) : false;
        
        // Проверяем наличие скидки (приводим к числам для корректного сравнения)
        const price = parseFloat(product.price) || 0;
        // Обрабатываем discount_price: может быть null, 0, строкой "0", или числом
        let discountPrice = null;
        if (product.discount_price !== null && product.discount_price !== undefined && product.discount_price !== '') {
            const parsed = parseFloat(product.discount_price);
            if (!isNaN(parsed) && parsed > 0) {
                discountPrice = parsed;
            }
        }
        const hasDiscount = discountPrice !== null && discountPrice < price;
        
        // Временное логирование для отладки (удалить после проверки)
        if (product.discount_price !== null && product.discount_price !== undefined) {
            console.log('[PRODUCT CARD] Discount check:', {
                productId: product.id,
                productName: product.name,
                price,
                discount_price_raw: product.discount_price,
                discountPrice,
                hasDiscount
            });
        }
        
        let media = [];
        if (product.media && Array.isArray(product.media) && product.media.length > 0) {
            media = product.media;
        } else if (product.primary_image) {
            media = [{ url: product.primary_image, media_type: 'photo' }];
        }
        
        if (media.length === 0 && product.id) {
            console.warn('[PRODUCT CARD] No media found for product:', product.id, product.name);
        }
        
        const hasMultipleImages = media.length > 1;
        const card = document.createElement('div');
        card.className = 'product-card fade-in';
        card.dataset.productId = product.id;
        
        const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
        const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
        
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
                                        ? `<video src="${mediaUrl}" preload="metadata" muted playsinline controls loop style="width:100%;height:100%;object-fit:cover;"></video>` 
                                        : `<img src="${mediaUrl}" alt="${product.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling && (this.nextElementSibling.style.display='flex');">`
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
                            ? `<video src="${mediaUrl}" preload="metadata" muted playsinline controls loop style="width:100%;height:100%;object-fit:cover;"></video>`
                            : `<img src="${mediaUrl}" alt="${product.name}" loading="lazy">`
                        }
                    </div>
                `;
            }
        } else {
            imageHTML = '<div class="product-image-placeholder">🌸</div>';
        }
        
        // Проверяем, есть ли товар в корзине
        const state = getState();
        const cart = state?.cart || [];
        const cartItem = cart.find(item => item.product_id === product.id);
        const isInCart = !!cartItem;
        const cartQuantity = cartItem?.quantity || 0;
        const isOutOfStock = !product.quantity || product.quantity <= 0;
        
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
                <div class="product-shop-name">${product.shop_name || 'Магазин'}</div>
                <div class="product-price-row">
                    <span class="product-current-price">${formatPrice(hasDiscount ? discountPrice : price)}</span>
                    ${hasDiscount ? `<span class="product-original-price">${formatPrice(price)}</span>` : ''}
                </div>
                <div class="product-card-actions">
                    ${isOutOfStock 
                        ? `<button class="product-card-btn out-of-stock" disabled>Нет в наличии</button>`
                        : isInCart 
                            ? `<div class="product-card-quantity">
                                <button class="qty-btn minus" data-product-id="${product.id}">−</button>
                                <span class="qty-value">${cartQuantity}</span>
                                <button class="qty-btn plus" data-product-id="${product.id}">+</button>
                               </div>`
                            : `<button class="product-card-btn add-to-cart" data-product-id="${product.id}">В корзину</button>`
                    }
                </div>
            </div>
        `;
        
        if (hasMultipleImages) {
            initProductCardSlider(card, product.id, media.length);
        } else if (media.length === 1 && media[0].media_type === 'video') {
            const cardVideo = card.querySelector('video');
            if (cardVideo) {
                const playVideo = () => {
                    if (cardVideo.readyState >= 2) {
                        cardVideo.play().catch(err => {
                            if (err.name !== 'NotAllowedError' && err.name !== 'AbortError') {
                                console.log('[VIDEO] Autoplay prevented for single video:', err);
                            }
                        });
                    } else {
                        cardVideo.addEventListener('loadeddata', playVideo, { once: true });
                        cardVideo.load();
                    }
                };
                if (cardVideo.readyState >= 2) {
                    setTimeout(playVideo, 100);
                } else {
                    cardVideo.addEventListener('loadeddata', playVideo, { once: true });
                    cardVideo.load();
                }
            }
        }
        
        card.addEventListener('click', (e) => {
            if (e.target.closest('.product-favorite-btn') || 
                e.target.closest('.product-slider-dots') || 
                e.target.closest('.slider-dot') ||
                e.target.closest('.product-card-actions')) return;
            if (window.openProductPage) window.openProductPage(product.id);
        });
        
        const favBtn = card.querySelector('.product-favorite-btn');
        if (favBtn) {
            favBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (window.toggleFavorite) window.toggleFavorite(product.id);
            });
        }
        
        // Обработчик кнопки "В корзину"
        const addToCartBtn = card.querySelector('.product-card-btn.add-to-cart');
        if (addToCartBtn) {
            addToCartBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (window.addToCart) {
                    await window.addToCart(product.id);
                    // Перерендериваем карточку после добавления
                    renderProducts();
                }
            });
        }
        
        // Обработчики кнопок количества
        const minusBtn = card.querySelector('.qty-btn.minus');
        const plusBtn = card.querySelector('.qty-btn.plus');
        
        if (minusBtn) {
            minusBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const currentState = getState();
                const currentCart = currentState?.cart || [];
                const item = currentCart.find(i => i.product_id === product.id);
                if (item) {
                    if (item.quantity <= 1) {
                        // Удаляем из корзины
                        if (window.removeFromCart) {
                            await window.removeFromCart(item.id);
                            renderProducts();
                        }
                    } else {
                        // Уменьшаем количество
                        if (window.updateCartQuantity) {
                            await window.updateCartQuantity(item.id, item.quantity - 1);
                            renderProducts();
                        }
                    }
                }
            });
        }
        
        if (plusBtn) {
            plusBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const currentState = getState();
                const currentCart = currentState?.cart || [];
                const item = currentCart.find(i => i.product_id === product.id);
                if (item && item.quantity < product.quantity) {
                    if (window.updateCartQuantity) {
                        await window.updateCartQuantity(item.id, item.quantity + 1);
                        renderProducts();
                    }
                }
            });
        }
        
        return card;
        } catch (error) {
            console.error('[PRODUCT CARD] Error creating card for product:', product?.id, error);
            return null;
        }
    }
    
    // Инициализация слайдера для карточки товара
    function initProductCardSlider(card, productId, imageCount) {
        const slider = card.querySelector('.product-image-slider');
        if (!slider || imageCount <= 1) return;
        
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
        
        state.products.forEach((product) => {
            const card = createProductCard(product);
            if (card) grid.appendChild(card);
        });
        
        if (window.App?.favorites?.updateFavoriteButtons) {
            window.App.favorites.updateFavoriteButtons();
        }
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
})();


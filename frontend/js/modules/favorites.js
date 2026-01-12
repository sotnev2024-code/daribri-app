/**
 * Favorites Module - избранное
 */

(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    const getApi = () => window.api;
    
    // Загрузка избранного
    async function loadFavorites() {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        try {
            console.log('[FAVORITES] Loading favorites from server...');
            const favoritesData = await api.getFavorites();
            
            state.favorites = (favoritesData || []).map(fav => {
                if ((!fav.media || !Array.isArray(fav.media) || fav.media.length === 0) && fav.primary_image) {
                    return {
                        ...fav,
                        media: [{ url: fav.primary_image, media_type: 'photo' }]
                    };
                }
                return fav;
            });
            
            console.log('[FAVORITES] ✅ Loaded favorites from server:', state.favorites.length, 'items');
            if (utils.updateFavoritesBadge) utils.updateFavoritesBadge();
            updateFavoriteButtons();
        } catch (error) {
            console.error('[FAVORITES] ❌ Error loading favorites:', error);
            state.favorites = [];
        }
    }
    
    // Проверка, находится ли товар в избранном
    function isProductFavorite(productId) {
        const state = getState();
        if (!state || !state.favorites || state.favorites.length === 0) return false;
        
        const productIdNum = typeof productId === 'string' ? parseInt(productId) : productId;
        const found = state.favorites.some(f => {
            const favId = f.product_id || f.id;
            const favIdNum = typeof favId === 'string' ? parseInt(favId) : favId;
            return favIdNum === productIdNum;
        });
        return found;
    }
    
    // Обновление кнопок избранного в отрендеренных карточках
    function updateFavoriteButtons() {
        const state = getState();
        if (!state) return;
        
        document.querySelectorAll('.product-favorite-btn[data-product-id]').forEach(btn => {
            const productId = parseInt(btn.dataset.productId);
            if (!isNaN(productId)) {
                const isFavorite = isProductFavorite(productId);
                btn.classList.toggle('active', isFavorite);
            }
        });
    }
    
    // Переключение избранного
    async function toggleFavorite(productId) {
        const state = getState();
        const utils = getUtils();
        const api = getApi();
        if (!state || !api) return;
        
        try {
            const isFavorite = isProductFavorite(productId);
            
            if (isFavorite) {
                // Удаляем из избранного
                await api.removeFromFavorites(productId);
                state.favorites = state.favorites.filter(f => {
                    const favId = f.product_id || f.id;
                    const favIdNum = typeof favId === 'string' ? parseInt(favId) : favId;
                    const productIdNum = typeof productId === 'string' ? parseInt(productId) : productId;
                    return favIdNum !== productIdNum;
                });
                // Уведомление убрано по запросу пользователя
            } else {
                // Добавляем в избранное
                // Сначала загружаем полные данные товара
                try {
                    const product = await api.getProduct(productId);
                    const favoriteProduct = {
                        id: product.id,
                        product_id: product.id,
                        name: product.name,
                        price: product.price,
                        discount_price: product.discount_price,
                        discount_percent: product.discount_percent,
                        shop_name: product.shop_name,
                        shop_id: product.shop_id,
                        primary_image: product.media && product.media.length > 0 
                            ? product.media[0].url 
                            : null,
                        media: product.media || [],
                        is_trending: product.is_trending || false,
                        category_name: product.category_name,
                        ...product
                    };
                    await api.addToFavorites(productId);
                    state.favorites.push(favoriteProduct);
                    // Уведомление убрано по запросу пользователя
                } catch (error) {
                    console.error('[FAVORITES] Error adding to favorites:', error);
                    if (utils.showToast) utils.showToast('Ошибка добавления в избранное', 'error');
                    return;
                }
            }
            
            if (utils.updateFavoritesBadge) utils.updateFavoritesBadge();
            updateFavoriteButtons();
            
            // Обновляем кнопку избранного на странице товара
            const productFavoriteBtn = document.getElementById('productFavoriteBtn');
            if (productFavoriteBtn) {
                productFavoriteBtn.classList.toggle('active', !isFavorite);
            }
        } catch (error) {
            console.error('[FAVORITES] Error toggling favorite:', error);
            if (utils.showToast) utils.showToast('Ошибка', 'error');
        }
    }
    
    // Рендеринг избранного
    async function renderFavorites() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        const api = getApi();
        if (!state || !elements) return;
        
        console.log('[FAVORITES] renderFavorites called, favorites count:', state.favorites.length);
        
        if (!state.favorites || state.favorites.length === 0) {
            elements.favoritesGrid.innerHTML = '';
            elements.favoritesEmpty.hidden = false;
            return;
        }
        
        elements.favoritesEmpty.hidden = true;
        elements.favoritesGrid.innerHTML = '';
        
        const validFavorites = [];
        const needToLoad = [];
        
        state.favorites.forEach((fav, index) => {
            if (fav && fav.id && fav.name && fav.price !== undefined && fav.price !== null) {
                validFavorites.push(fav);
            } else {
                const productId = fav.id || fav.product_id;
                if (productId) {
                    needToLoad.push({ productId, index, fav });
                } else {
                    console.warn('[FAVORITES] Invalid favorite item (no ID):', fav);
                }
            }
        });
        
        if (needToLoad.length > 0) {
            console.log('[FAVORITES] Loading', needToLoad.length, 'incomplete favorite products');
            
            const loadPromises = needToLoad.map(async ({ productId, index, fav }) => {
                try {
                    console.log(`[FAVORITES] Loading product ${productId}...`);
                    const product = await api.getProduct(productId);
                    
                    const favoriteProduct = {
                        id: product.id,
                        product_id: product.id,
                        name: product.name,
                        price: product.price,
                        discount_price: product.discount_price,
                        discount_percent: product.discount_percent,
                        shop_name: product.shop_name,
                        shop_id: product.shop_id,
                        primary_image: product.media && product.media.length > 0 
                            ? product.media[0].url 
                            : null,
                        media: product.media || [],
                        is_trending: product.is_trending || false,
                        category_name: product.category_name,
                        favorite_id: fav.favorite_id,
                        added_at: fav.added_at,
                        ...product
                    };
                    
                    state.favorites[index] = favoriteProduct;
                    validFavorites.push(favoriteProduct);
                    
                    console.log(`[FAVORITES] ✅ Loaded product ${productId}:`, favoriteProduct.name);
                    return favoriteProduct;
                } catch (error) {
                    console.error(`[FAVORITES] ❌ Error loading product ${productId}:`, error);
                    return null;
                }
            });
            
            await Promise.all(loadPromises);
            console.log('[FAVORITES] Finished loading products, valid count:', validFavorites.length);
        }
        
        if (validFavorites.length > 0) {
            const catalogModule = window.App?.catalog;
            if (catalogModule?.createProductCard) {
                validFavorites.forEach(fav => {
                    try {
                        // Нормализуем данные - убеждаемся, что у всех есть media
                        if (!fav.media || !Array.isArray(fav.media) || fav.media.length === 0) {
                            if (fav.primary_image) {
                                fav.media = [{ url: fav.primary_image, media_type: 'photo' }];
                            }
                        }
                        
                        const card = catalogModule.createProductCard(fav);
                        if (card) {
                            elements.favoritesGrid.appendChild(card);
                        } else {
                            console.warn('[FAVORITES] createProductCard returned null for:', fav);
                        }
                    } catch (error) {
                        console.error('[FAVORITES] Error creating product card:', error, fav);
                    }
                });
                
                // Убеждаемся, что все слайдеры инициализированы после рендеринга
                setTimeout(() => {
                    const allSliders = elements.favoritesGrid.querySelectorAll('.product-image-slider');
                    const initProductCardSlider = catalogModule?.initProductCardSlider || window.initProductCardSlider;
                    
                    if (initProductCardSlider) {
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
                    }
                }, 100);
            }
        }
        
        if (validFavorites.length === 0) {
            elements.favoritesEmpty.hidden = false;
            elements.favoritesGrid.innerHTML = '';
        }
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.favorites = {
        loadFavorites,
        renderFavorites,
        toggleFavorite,
        isProductFavorite,
        updateFavoriteButtons
    };
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.loadFavorites = loadFavorites;
    window.renderFavorites = renderFavorites;
    window.toggleFavorite = toggleFavorite;
    window.isProductFavorite = isProductFavorite;
    window.updateFavoriteButtons = updateFavoriteButtons;
})();

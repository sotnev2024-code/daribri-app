/**
 * Navigation Module - навигация и поиск
 */

(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    
    // Навигация по страницам
    async function navigateTo(page) {
        const state = getState();
        const elements = getElements();
        if (!state || !elements) return;
        
        console.log('[NAV] Navigating to:', page);
        
        // Список всех страниц
        const allPages = [
            elements.productPage,
            elements.cartPage,
            elements.favoritesPage,
            elements.profilePage,
            elements.myShopPage,
            elements.settingsPage,
            elements.helpPage,
            elements.myOrdersPage,
            elements.shopOrdersPage,
            elements.shopReviewsPage,
            elements.shopStatisticsPage,
            document.getElementById('shopPage'),
            document.getElementById('shopStatisticsPage'),
            document.getElementById('myProductsPage'),
            document.getElementById('subscriptionManagementPage')
        ].filter(p => p);
        
        // Скрываем все страницы
        allPages.forEach(p => {
            p.setAttribute('hidden', '');
            p.style.display = 'none';
        });
        
        // Показываем нужную страницу
        switch (page) {
            case 'catalog':
                // Главная страница всегда видна
                break;
                
            case 'product':
                if (elements.productPage) {
                    elements.productPage.removeAttribute('hidden');
                    elements.productPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.productPage.scrollTop = 0;
                    }, 0);
                }
                break;
                
            case 'cart':
                if (elements.cartPage) {
                    elements.cartPage.removeAttribute('hidden');
                    elements.cartPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.cartPage.scrollTop = 0;
                    }, 0);
                    
                    // Загружаем корзину при переходе
                    const cartModule = window.App?.cart;
                    if (cartModule?.loadCart) {
                        await cartModule.loadCart();
                    }
                    if (cartModule?.renderCart) {
                        cartModule.renderCart();
                    }
                }
                break;
                
            case 'favorites':
                if (elements.favoritesPage) {
                    elements.favoritesPage.removeAttribute('hidden');
                    elements.favoritesPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.favoritesPage.scrollTop = 0;
                    }, 0);
                    
                    // Загружаем избранное при переходе
                    const favoritesModule = window.App?.favorites;
                    if (favoritesModule?.loadFavorites) {
                        await favoritesModule.loadFavorites();
                    }
                    if (favoritesModule?.renderFavorites) {
                        await favoritesModule.renderFavorites();
                    }
                }
                break;
                
            case 'profile':
                if (elements.profilePage) {
                    elements.profilePage.removeAttribute('hidden');
                    elements.profilePage.style.display = 'flex';
                    setTimeout(() => {
                        elements.profilePage.scrollTop = 0;
                    }, 0);
                    
                    // Загружаем профиль
                    if (state.user) {
                        elements.profileName.textContent = state.user.first_name || 'Пользователь';
                        if (elements.profileUsername) {
                            elements.profileUsername.textContent = state.user.username || '';
                        }
                    }
                }
                break;
                
            case 'myshop':
                if (elements.myShopPage) {
                    elements.myShopPage.removeAttribute('hidden');
                    elements.myShopPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.myShopPage.scrollTop = 0;
                    }, 0);
                    
                    // Загружаем данные магазина
                    if (window.loadMyShop) {
                        await window.loadMyShop();
                    }
                }
                break;
                
            case 'settings':
                if (elements.settingsPage) {
                    elements.settingsPage.removeAttribute('hidden');
                    elements.settingsPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.settingsPage.scrollTop = 0;
                    }, 0);
                    
                    if (window.loadSettings) {
                        window.loadSettings();
                    }
                }
                break;
                
            case 'help':
                if (elements.helpPage) {
                    elements.helpPage.removeAttribute('hidden');
                    elements.helpPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.helpPage.scrollTop = 0;
                    }, 0);
                }
                break;
                
            case 'myorders':
                if (elements.myOrdersPage) {
                    elements.myOrdersPage.removeAttribute('hidden');
                    elements.myOrdersPage.style.display = 'flex';
                    setTimeout(() => {
                        elements.myOrdersPage.scrollTop = 0;
                    }, 0);
                    
                    if (window.loadUserOrders) {
                        await window.loadUserOrders();
                    }
                }
                break;
                
            case 'shoporders':
            case 'shopreviews':
            case 'shopstatistics':
            case 'myproducts':
            case 'subscription-management':
                // Эти страницы загружаются через другие функции
                const pageMap = {
                    'shoporders': 'shopOrdersPage',
                    'shopreviews': 'shopReviewsPage',
                    'shopstatistics': 'shopStatisticsPage',
                    'myproducts': 'myProductsPage',
                    'subscription-management': 'subscriptionManagementPage'
                };
                
                const pageElement = elements[pageMap[page]];
                if (pageElement) {
                    pageElement.removeAttribute('hidden');
                    pageElement.style.display = 'flex';
                    setTimeout(() => {
                        pageElement.scrollTop = 0;
                    }, 0);
                }
                break;
        }
        
        // Обновляем активное состояние в навигации
        if (elements.bottomNav) {
            elements.bottomNav.querySelectorAll('.nav-item').forEach(item => {
                item.classList.toggle('active', item.dataset.page === page);
            });
        }
        
        // Скрываем модальные окна при навигации
        if (elements.searchModal) elements.searchModal.hidden = true;
        if (elements.filterModal) elements.filterModal.hidden = true;
    }
    
    // Открытие поиска
    function openSearch() {
        const elements = getElements();
        if (!elements?.searchModal) return;
        
        elements.searchModal.hidden = false;
        if (elements.searchInput) {
            elements.searchInput.focus();
        }
    }
    
    // Закрытие поиска
    function closeSearch() {
        const elements = getElements();
        if (!elements?.searchModal) return;
        
        elements.searchModal.hidden = true;
        if (elements.searchInput) {
            elements.searchInput.value = '';
        }
        if (elements.searchResults) {
            elements.searchResults.innerHTML = '';
        }
    }
    
    // Обработка поиска
    async function handleSearch() {
        const elements = getElements();
        const utils = getUtils();
        const api = window.api;
        if (!elements || !api) return;
        
        const query = elements.searchInput.value.trim();
        
        if (query.length < 2) {
            elements.searchResults.innerHTML = '';
            return;
        }
        
        try {
            const products = await api.getProducts({ search: query, limit: 10 });
            
            // Обрабатываем формат ответа
            let productsList = [];
            if (Array.isArray(products)) {
                productsList = products;
            } else if (products && Array.isArray(products.items)) {
                productsList = products.items;
            } else if (products && Array.isArray(products.data)) {
                productsList = products.data;
            } else if (products && Array.isArray(products.products)) {
                productsList = products.products;
            }
            
            if (productsList.length === 0) {
                elements.searchResults.innerHTML = '<div class="empty-state"><p>Ничего не найдено</p></div>';
                return;
            }
            
            const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
            const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
            
            elements.searchResults.innerHTML = productsList.map(p => {
                // Получаем изображение товара
                let imageUrl = null;
                if (p.media && Array.isArray(p.media) && p.media.length > 0) {
                    // Используем первое медиа из массива
                    imageUrl = getMediaUrl(p.media[0].url || p.media[0]);
                } else if (p.primary_image) {
                    imageUrl = getMediaUrl(p.primary_image);
                }
                
                const imageHTML = imageUrl 
                    ? `<img src="${imageUrl}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover;" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` 
                    : '';
                const placeholderHTML = '<div style="display:flex;align-items:center;justify-content:center;width:100%;height:100%;font-size:24px;">🌸</div>';
                
                return `
                    <div class="search-result-item" onclick="window.openProductPage(${p.id}); window.closeSearch();">
                        <div style="width:64px;height:64px;background:var(--bg-tertiary);border-radius:8px;overflow:hidden;flex-shrink:0;">
                            ${imageHTML}
                            ${placeholderHTML}
                        </div>
                        <div style="flex:1;min-width:0;margin-left:12px;">
                            <div style="font-weight:500;font-size:0.9375rem;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${p.name}</div>
                            <div style="color:var(--text-muted);font-size:0.875rem;">
                                ${p.shop_name ? `<span style="display:block;margin-bottom:4px;">${p.shop_name}</span>` : ''}
                                <span style="font-weight:600;color:var(--primary);">${formatPrice(p.discount_price || p.price)}</span>
                                ${p.discount_price && p.price ? `<span style="text-decoration:line-through;margin-left:8px;color:var(--text-muted);font-size:0.8125rem;">${formatPrice(p.price)}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (error) {
            console.error('[SEARCH] Search error:', error);
            elements.searchResults.innerHTML = '<div class="empty-state"><p>Ошибка поиска. Попробуйте еще раз.</p></div>';
        }
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.navigation = {
        navigateTo,
        openSearch,
        closeSearch,
        handleSearch
    };
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.navigateTo = navigateTo;
    window.openSearch = openSearch;
    window.closeSearch = closeSearch;
    window.handleSearch = handleSearch;
})();

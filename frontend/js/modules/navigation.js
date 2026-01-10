/**
 * Navigation Module - навигация и умный поиск
 */

(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    
    // ==================== Smart Search ====================
    const SEARCH_HISTORY_KEY = 'daribri_search_history';
    const MAX_HISTORY_ITEMS = 10;
    let searchDebounceTimer = null;
    
    // Получение истории поиска
    function getSearchHistory() {
        try {
            return JSON.parse(localStorage.getItem(SEARCH_HISTORY_KEY)) || [];
        } catch {
            return [];
        }
    }
    
    // Сохранение в историю поиска
    function saveToSearchHistory(query) {
        if (!query || query.length < 2) return;
        
        let history = getSearchHistory();
        // Удаляем дубликаты
        history = history.filter(item => item.toLowerCase() !== query.toLowerCase());
        // Добавляем в начало
        history.unshift(query);
        // Ограничиваем размер
        history = history.slice(0, MAX_HISTORY_ITEMS);
        
        localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history));
    }
    
    // Удаление из истории
    function removeFromSearchHistory(query) {
        let history = getSearchHistory();
        history = history.filter(item => item !== query);
        localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(history));
        showSearchSuggestions();
    }
    
    // Очистка всей истории
    function clearSearchHistory() {
        localStorage.removeItem(SEARCH_HISTORY_KEY);
        showSearchSuggestions();
    }
    
    // Подсветка найденного текста
    function highlightText(text, query) {
        if (!query || !text) return text;
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    // Показ подсказок (история + популярные категории)
    function showSearchSuggestions() {
        const elements = getElements();
        const state = getState();
        if (!elements?.searchResults) return;
        
        const history = getSearchHistory();
        const categories = state?.categories || [];
        
        let html = '';
        
        // История поиска
        if (history.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section-header">
                        <span>🕒 Недавние запросы</span>
                        <button class="clear-history-btn" onclick="window.clearSearchHistory(); event.stopPropagation();">Очистить</button>
                    </div>
                    <div class="search-history-list">
                        ${history.map(item => `
                            <div class="search-history-item" onclick="window.searchFromHistory('${item.replace(/'/g, "\\'")}')">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="10"/>
                                    <polyline points="12,6 12,12 16,14"/>
                                </svg>
                                <span>${item}</span>
                                <button class="remove-history-btn" onclick="window.removeFromSearchHistory('${item.replace(/'/g, "\\'")}'); event.stopPropagation();">✕</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        // Популярные категории
        if (categories.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section-header">
                        <span>📂 Категории</span>
                    </div>
                    <div class="search-categories-grid">
                        ${categories.slice(0, 8).map(cat => `
                            <button class="search-category-chip" onclick="window.searchByCategory(${cat.id}, '${cat.name.replace(/'/g, "\\'")}')">
                                ${cat.icon ? `<img src="${cat.icon}" alt="" style="width:20px;height:20px;border-radius:4px;">` : ''}
                                <span>${cat.name}</span>
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        // Популярные запросы
        html += `
            <div class="search-section">
                <div class="search-section-header">
                    <span>🔥 Популярные запросы</span>
                </div>
                <div class="search-tags">
                    <button class="search-tag" onclick="window.searchFromHistory('цветы')">цветы</button>
                    <button class="search-tag" onclick="window.searchFromHistory('букет')">букет</button>
                    <button class="search-tag" onclick="window.searchFromHistory('розы')">розы</button>
                    <button class="search-tag" onclick="window.searchFromHistory('торт')">торт</button>
                    <button class="search-tag" onclick="window.searchFromHistory('подарок')">подарок</button>
                </div>
            </div>
        `;
        
        elements.searchResults.innerHTML = html;
    }
    
    // Поиск из истории
    function searchFromHistory(query) {
        const elements = getElements();
        if (!elements?.searchInput) return;
        
        elements.searchInput.value = query;
        handleSearch();
    }
    
    // Поиск по категории
    function searchByCategory(categoryId, categoryName) {
        closeSearch();
        // Выбираем категорию
        if (window.selectCategory) {
            window.selectCategory(categoryId);
        }
    }
    
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
            elements.searchInput.value = '';
            elements.searchInput.focus();
        }
        // Показываем подсказки при открытии
        showSearchSuggestions();
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
        // Сбрасываем таймер
        if (searchDebounceTimer) {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = null;
        }
    }
    
    // Живой поиск с debounce
    function handleSearchInput() {
        const elements = getElements();
        if (!elements?.searchInput) return;
        
        const query = elements.searchInput.value.trim();
        
        // Очищаем предыдущий таймер
        if (searchDebounceTimer) {
            clearTimeout(searchDebounceTimer);
        }
        
        // Если пустой запрос - показываем подсказки
        if (query.length === 0) {
            showSearchSuggestions();
            return;
        }
        
        // Если меньше 2 символов - ничего не делаем
        if (query.length < 2) {
            return;
        }
        
        // Показываем индикатор загрузки
        elements.searchResults.innerHTML = `
            <div class="search-loading">
                <div class="spinner"></div>
                <span>Поиск...</span>
            </div>
        `;
        
        // Debounce - ждём 300мс после последнего ввода
        searchDebounceTimer = setTimeout(() => {
            handleSearch();
        }, 300);
    }
    
    // Обработка поиска
    async function handleSearch() {
        const elements = getElements();
        const utils = getUtils();
        const api = window.api;
        if (!elements || !api) return;
        
        const query = elements.searchInput.value.trim();
        
        if (query.length < 2) {
            showSearchSuggestions();
            return;
        }
        
        try {
            const products = await api.getProducts({ search: query, limit: 15 });
            
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
            
            // Сохраняем запрос в историю (только если нашли результаты)
            if (productsList.length > 0) {
                saveToSearchHistory(query);
            }
            
            if (productsList.length === 0) {
                elements.searchResults.innerHTML = `
                    <div class="search-empty">
                        <div class="search-empty-icon">🔍</div>
                        <div class="search-empty-title">Ничего не найдено</div>
                        <div class="search-empty-text">Попробуйте изменить запрос или посмотрите популярные товары</div>
                    </div>
                `;
                return;
            }
            
            const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
            const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
            
            let html = `
                <div class="search-results-header">
                    <span>Найдено: ${productsList.length} ${getProductWord(productsList.length)}</span>
                </div>
            `;
            
            html += productsList.map(p => {
                // Получаем изображение товара
                let imageUrl = null;
                if (p.media && Array.isArray(p.media) && p.media.length > 0) {
                    imageUrl = getMediaUrl(p.media[0].url || p.media[0]);
                } else if (p.primary_image) {
                    imageUrl = getMediaUrl(p.primary_image);
                }
                
                const imageHTML = imageUrl 
                    ? `<img src="${imageUrl}" alt="${p.name}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` 
                    : '';
                const placeholderHTML = '<div class="search-result-placeholder">🌸</div>';
                
                // Подсветка найденного текста
                const highlightedName = highlightText(p.name, query);
                const highlightedShop = p.shop_name ? highlightText(p.shop_name, query) : '';
                
                return `
                    <div class="search-result-item" onclick="window.openProductPage(${p.id}); window.closeSearch();">
                        <div class="search-result-image">
                            ${imageHTML}
                            ${placeholderHTML}
                        </div>
                        <div class="search-result-info">
                            <div class="search-result-name">${highlightedName}</div>
                            ${highlightedShop ? `<div class="search-result-shop">${highlightedShop}</div>` : ''}
                            <div class="search-result-price">
                                <span class="current-price">${formatPrice(p.discount_price || p.price)}</span>
                                ${p.discount_price && p.price ? `<span class="old-price">${formatPrice(p.price)}</span>` : ''}
                            </div>
                        </div>
                        <svg class="search-result-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9,18 15,12 9,6"/>
                        </svg>
                    </div>
                `;
            }).join('');
            
            elements.searchResults.innerHTML = html;
        } catch (error) {
            console.error('[SEARCH] Search error:', error);
            elements.searchResults.innerHTML = `
                <div class="search-empty">
                    <div class="search-empty-icon">⚠️</div>
                    <div class="search-empty-title">Ошибка поиска</div>
                    <div class="search-empty-text">Попробуйте еще раз</div>
                </div>
            `;
        }
    }
    
    // Склонение слова "товар"
    function getProductWord(count) {
        const lastDigit = count % 10;
        const lastTwoDigits = count % 100;
        
        if (lastTwoDigits >= 11 && lastTwoDigits <= 19) return 'товаров';
        if (lastDigit === 1) return 'товар';
        if (lastDigit >= 2 && lastDigit <= 4) return 'товара';
        return 'товаров';
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.navigation = {
        navigateTo,
        openSearch,
        closeSearch,
        handleSearch,
        handleSearchInput,
        searchFromHistory,
        searchByCategory,
        clearSearchHistory,
        removeFromSearchHistory
    };
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.navigateTo = navigateTo;
    window.openSearch = openSearch;
    window.closeSearch = closeSearch;
    window.handleSearch = handleSearch;
    window.handleSearchInput = handleSearchInput;
    window.searchFromHistory = searchFromHistory;
    window.searchByCategory = searchByCategory;
    window.clearSearchHistory = clearSearchHistory;
    window.removeFromSearchHistory = removeFromSearchHistory;
})();

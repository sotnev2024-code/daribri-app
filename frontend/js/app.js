/**
 * Telegram Mini App - Main Application
 */

// Telegram WebApp
const tg = window.Telegram?.WebApp || null;

// Состояние приложения
const state = {
    user: null,
    categories: [],
    products: [],
    cart: [],
    favorites: [],
    currentCategory: 'all',
    currentProduct: null,
    loading: false,
    myShop: null,
    mySubscription: null,
    myProducts: [],
    subscriptionPlans: [],
    filters: {
        minPrice: null,
        maxPrice: null,
        discounted: false,
        inStock: true,
        trending: false,
    },
};

// DOM элементы (будут инициализированы после загрузки DOM)
let elements = {};

// Инициализируем window.App для модулей
window.App = window.App || {};
window.App.state = state;
window.App.elements = elements;

// ==================== Utility Functions ====================

function getMediaUrl(url) {
    if (!url) return '';
    
    // Если это уже полный URL (blob, http, https, data), возвращаем как есть
    if (url.startsWith('blob:') || url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
        return url;
    }
    
    if (!api) {
        console.warn('[MEDIA] API not available, returning original URL:', url);
        return url;
    }
    
    // Если URL уже начинается с /media/, просто добавляем baseUrl
    if (url.startsWith('/media/')) {
        return api.baseUrl + url;
    }
    
    // Если URL начинается с /, добавляем baseUrl
    if (url.startsWith('/')) {
        return api.baseUrl + url;
    }
    
    // Если URL не начинается с /, добавляем /media/
    // Медиа файлы доступны по пути /media/...
    return api.baseUrl + '/media/' + url;
}

function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0,
    }).format(price);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
    });
}

// Функция formatDateObject для форматирования Date объектов (отличается от formatDate, которая принимает строку)
function formatDateObject(date) {
    if (!date) return '';
    return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(date);
}

function formatOrderDate(dateString) {
    if (!dateString) return 'Не указана';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

function formatDeliveryDate(dateString) {
    if (!dateString) return 'Не указана';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
}

function getOrderStatusText(status) {
    const statuses = {
        pending: 'Ожидает',
        confirmed: 'Подтверждён',
        processing: 'В обработке',
        shipped: 'Доставляется',
        delivered: 'Доставлен',
        cancelled: 'Отменён',
    };
    return statuses[status] || status;
}

function updateCartBadge() {
    if (!elements?.cartBadge) return;
    const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    elements.cartBadge.textContent = count;
    elements.cartBadge.hidden = count === 0;
    if (elements.cartNavBadge) {
        elements.cartNavBadge.textContent = count;
        elements.cartNavBadge.hidden = count === 0;
    }
}

function updateFavoritesBadge() {
    if (!elements?.favoritesBadge) return;
    const count = state.favorites.length;
    elements.favoritesBadge.textContent = count;
    elements.favoritesBadge.hidden = count === 0;
}

function showLoading(show) {
    if (elements.loadingIndicator) {
        elements.loadingIndicator.hidden = !show;
    }
    if (elements.productsGrid) {
        elements.productsGrid.style.display = show ? 'none' : '';
    }
}

// Поделиться товаром в Telegram
function shareProduct(product) {
    if (!product) return;
    
    const botUsername = 'Daribri_bot';
    const productName = product.name || 'Товар';
    const price = product.discount_price || product.price;
    const formattedPrice = new Intl.NumberFormat('ru-RU').format(price);
    
    // Формируем текст для шаринга
    const shareText = `🎁 Смотри, что я нашёл!\n\n${productName}\n💰 ${formattedPrice} ₽\n\nОткрой в приложении 👇`;
    
    // Ссылка на бота с параметром товара
    const shareUrl = `https://t.me/${botUsername}?start=product_${product.id}`;
    
    // Используем Telegram WebApp API если доступен
    if (window.Telegram?.WebApp) {
        const tg = window.Telegram.WebApp;
        
        // Открываем диалог шаринга через Telegram
        const telegramShareUrl = `https://t.me/share/url?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(shareText)}`;
        tg.openTelegramLink(telegramShareUrl);
    } else {
        // Fallback - копируем ссылку в буфер обмена
        const fullText = `${shareText}\n${shareUrl}`;
        navigator.clipboard.writeText(fullText).then(() => {
            showToast('Ссылка скопирована!', 'success');
        }).catch(() => {
            showToast('Не удалось скопировать ссылку', 'error');
        });
    }
}

function showToast(message, type = 'info') {
    if (!elements?.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function pluralize(count, one, few, many) {
    const mod10 = count % 10;
    const mod100 = count % 100;
    if (mod100 >= 11 && mod100 <= 19) return many;
    if (mod10 === 1) return one;
    if (mod10 >= 2 && mod10 <= 4) return few;
    return many;
}

// Экспортируем в window для глобального доступа
window.state = state;
window.elements = elements;
window.tg = tg;

// Инициализация элементов
function initElements() {
    elements = {
        // Header
        headerSearchInput: document.getElementById('headerSearchInput'),
    
    // Search
    searchModal: document.getElementById('searchModal'),
    searchInput: document.getElementById('searchInput'),
    closeSearch: document.getElementById('closeSearch'),
    searchResults: document.getElementById('searchResults'),
    
    // Filters
    filterBtn: document.getElementById('filterBtn'),
    filterModal: document.getElementById('filterModal'),
    closeFilterModal: document.getElementById('closeFilterModal'),
    filterMinPrice: document.getElementById('filterMinPrice'),
    filterMaxPrice: document.getElementById('filterMaxPrice'),
    filterInStock: document.getElementById('filterInStock'),
    resetFilters: document.getElementById('resetFilters'),
    applyFilters: document.getElementById('applyFilters'),
    
    // Categories
    categoriesSlider: document.getElementById('categoriesSlider'),
    subcategoriesSection: document.getElementById('subcategoriesSection'),
    subcategoriesGrid: document.getElementById('subcategoriesGrid'),
    
    // Products
    productsTitle: document.getElementById('productsTitle'),
    productsGrid: document.getElementById('productsGrid'),
    loadingIndicator: document.getElementById('loadingIndicator'),
    emptyState: document.getElementById('emptyState'),
    
    // Product Page
    productPage: document.getElementById('productPage'),
    productBackBtn: document.getElementById('productBackBtn'),
    productPageTitle: document.getElementById('productPageTitle'),
    productGallery: document.getElementById('productGallery'),
    productName: document.getElementById('productName'),
    productShop: document.getElementById('productShop'),
    productPrice: document.getElementById('productPrice'),
    productOldPrice: document.getElementById('productOldPrice'),
    productDiscount: document.getElementById('productDiscount'),
    productDescription: document.getElementById('productDescription'),
    productFavoriteBtn: document.getElementById('productFavoriteBtn'),
    shareProductBtn: document.getElementById('shareProductBtn'),
    qtyMinus: document.getElementById('qtyMinus'),
    qtyPlus: document.getElementById('qtyPlus'),
    qtyValue: document.getElementById('qtyValue'),
    addToCartBtn: document.getElementById('addToCartBtn'),
    inCartControls: document.getElementById('inCartControls'),
    cartQtyMinus: document.getElementById('cartQtyMinus'),
    cartQtyPlus: document.getElementById('cartQtyPlus'),
    cartQtyValue: document.getElementById('cartQtyValue'),
    goToCartBtn: document.getElementById('goToCartBtn'),
    
    // Pages
    productPage: document.getElementById('productPage'),
    cartPage: document.getElementById('cartPage'),
    favoritesPage: document.getElementById('favoritesPage'),
    profilePage: document.getElementById('profilePage'),
    settingsPage: document.getElementById('settingsPage'),
    helpPage: document.getElementById('helpPage'),
    
    // Cart
    cartItems: document.getElementById('cartItems'),
    cartEmpty: document.getElementById('cartEmpty'),
    cartSummary: document.getElementById('cartSummary'),
    clearCartBtn: document.getElementById('clearCartBtn'),
    summaryCount: document.getElementById('summaryCount'),
    summarySubtotal: document.getElementById('summarySubtotal'),
    summaryDiscountRow: document.getElementById('summaryDiscountRow'),
    summaryDiscount: document.getElementById('summaryDiscount'),
    summaryTotal: document.getElementById('summaryTotal'),
    checkoutBtn: document.getElementById('checkoutBtn'),
    cartNavBadge: document.getElementById('cartNavBadge'),
    
    // Favorites
    favoritesGrid: document.getElementById('favoritesGrid'),
    favoritesEmpty: document.getElementById('favoritesEmpty'),
    
    // Orders
    
    // Profile
    profileName: document.getElementById('profileName'),
    profileUsername: document.getElementById('profileUsername'),
    myOrdersBtn: document.getElementById('myOrdersBtn'),
    myShopBtn: document.getElementById('myShopBtn'),
    settingsBtn: document.getElementById('settingsBtn'),
    helpBtn: document.getElementById('helpBtn'),
    
    // My Orders
    myOrdersPage: document.getElementById('myOrdersPage'),
    userOrdersList: document.getElementById('userOrdersList'),
    userOrdersEmpty: document.getElementById('userOrdersEmpty'),
    
    // Settings
    appVersion: document.getElementById('appVersion'),
    clearCacheBtn: document.getElementById('clearCacheBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    addToHomeBtn: document.getElementById('addToHomeBtn'),
    addToHomeProfileBtn: document.getElementById('addToHomeProfileBtn'),
    
    // My Shop
    myShopPage: document.getElementById('myShopPage'),
    shopCreateSection: document.getElementById('shopCreateSection'),
    shopDashboard: document.getElementById('shopDashboard'),
    shopCreateForm: document.getElementById('shopCreateForm'),
    shopName: document.getElementById('shopName'),
    shopDescription: document.getElementById('shopDescription'),
    shopAddress: document.getElementById('shopAddress'),
    shopPhone: document.getElementById('shopPhone'),
    shopEmail: document.getElementById('shopEmail'),
    shopPhotoUpload: document.getElementById('shopPhotoUpload'),
    shopPhoto: document.getElementById('shopPhoto'),
    shopPhotoPreview: document.getElementById('shopPhotoPreview'),
    descCharCount: document.getElementById('descCharCount'),
    
    // Shop Dashboard
    dashboardShopPhoto: document.getElementById('dashboardShopPhoto'),
    dashboardShopName: document.getElementById('dashboardShopName'),
    dashboardShopRating: document.getElementById('dashboardShopRating'),
    dashboardReviewsCount: document.getElementById('dashboardReviewsCount'),
    dashboardProductsCount: document.getElementById('dashboardProductsCount'),
    dashboardOrdersCount: document.getElementById('dashboardOrdersCount'),
    dashboardRedemptionRate: document.getElementById('dashboardRedemptionRate'),
    editShopBtn: document.getElementById('editShopBtn'),
    addProductBtn: document.getElementById('addProductBtn'),
    myProductsBtn: document.getElementById('myProductsBtn'),
    
    // Subscription
    subscriptionCard: document.getElementById('subscriptionCard'),
    subscriptionStatus: document.getElementById('subscriptionStatus'),
    subscriptionInfo: document.getElementById('subscriptionInfo'),
    noSubscription: document.getElementById('noSubscription'),
    currentPlanName: document.getElementById('currentPlanName'),
    daysRemaining: document.getElementById('daysRemaining'),
    manageSubscriptionBtn: document.getElementById('manageSubscriptionBtn'),
    
    // Modals
    editShopModal: document.getElementById('editShopModal'),
    closeEditShopModal: document.getElementById('closeEditShopModal'),
    shopEditForm: document.getElementById('shopEditForm'),
    subscriptionModal: document.getElementById('subscriptionModal'),
    closeSubscriptionModal: document.getElementById('closeSubscriptionModal'),
    plansList: document.getElementById('plansList'),
    addProductModal: document.getElementById('addProductModal'),
    closeAddProductModal: document.getElementById('closeAddProductModal'),
    addProductForm: document.getElementById('addProductForm'),
    productCategoryInput: document.getElementById('productCategoryInput'),
    
    // My Products
    myProductsPage: document.getElementById('myProductsPage'),
    myProductsList: document.getElementById('myProductsList'),
    myProductsEmpty: document.getElementById('myProductsEmpty'),
    addProductFromListBtn: document.getElementById('addProductFromListBtn'),
    addFirstProductBtn: document.getElementById('addFirstProductBtn'),
    
    // Subscription Management
    subscriptionManagementPage: document.getElementById('subscriptionManagementPage'),
    subscriptionPage: document.getElementById('subscriptionPage'),
    shopPage: document.getElementById('shopPage'),
    subscriptionStatusBadge: document.getElementById('subscriptionStatusBadge'),
    managementPlanName: document.getElementById('managementPlanName'),
    subscriptionStartDate: document.getElementById('subscriptionStartDate'),
    subscriptionEndDate: document.getElementById('subscriptionEndDate'),
    subscriptionDaysRemaining: document.getElementById('subscriptionDaysRemaining'),
    subscriptionProgressFill: document.getElementById('subscriptionProgressFill'),
    subscriptionLimitsCard: document.getElementById('subscriptionLimitsCard'),
    productsUsage: document.getElementById('productsUsage'),
    productsLimitFill: document.getElementById('productsLimitFill'),
    promotionsUsage: document.getElementById('promotionsUsage'),
    promotionsLimitFill: document.getElementById('promotionsLimitFill'),
    subscriptionHistoryList: document.getElementById('subscriptionHistoryList'),
    subscriptionHistoryEmpty: document.getElementById('subscriptionHistoryEmpty'),
    showAllHistoryBtn: document.getElementById('showAllHistoryBtn'),
    
    // Navigation
    bottomNav: document.querySelector('.bottom-nav'),
    
    // Toast
    toastContainer: document.getElementById('toastContainer'),
        // Shop Reviews
        shopReviewsPage: document.getElementById('shopReviewsPage'),
        shopOrdersList: document.getElementById('shopOrdersList'),
        ordersFilterTabs: document.querySelector('.orders-filter-tabs'),
    };
    
    // Обновляем глобальные ссылки
    window.elements = elements;
    window.state = state;
    window.tg = tg;
    
    // Проверяем, что основные элементы найдены
    const requiredElements = ['categoriesSlider', 'productsGrid', 'bottomNav'];
    const missing = requiredElements.filter(id => !elements[id]);
    if (missing.length > 0) {
        console.warn('Missing required elements:', missing);
    }
}

// ==================== Catalog Functions ====================

// Демо-данные (временные)
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

// ==================== Catalog Functions ====================
// Функции каталога перенесены в modules/catalog.js
// Используем функции из модуля для обратной совместимости
const loadCategories = window.loadCategories || window.App?.catalog?.loadCategories || (async () => {
    console.warn('[CATALOG] loadCategories not loaded from module');
});
const loadProducts = window.loadProducts || window.App?.catalog?.loadProducts || (async (options = {}) => {
    console.warn('[CATALOG] loadProducts not loaded from module');
});
const renderCategories = window.renderCategories || window.App?.catalog?.renderCategories || (() => {
    console.warn('[CATALOG] renderCategories not loaded from module');
});
const renderProducts = window.renderProducts || window.App?.catalog?.renderProducts || (() => {
    console.warn('[CATALOG] renderProducts not loaded from module');
});
const selectCategory = window.selectCategory || window.App?.catalog?.selectCategory || ((categoryId) => {
    console.warn('[CATALOG] selectCategory not loaded from module');
});
const findCategory = window.findCategory || window.App?.catalog?.findCategory || ((id) => {
    console.warn('[CATALOG] findCategory not loaded from module');
    return null;
});
const applyClientFilters = window.applyClientFilters || window.App?.catalog?.applyClientFilters || ((products) => {
    console.warn('[CATALOG] applyClientFilters not loaded from module');
    return products;
});
const createProductCard = window.createProductCard || window.App?.catalog?.createProductCard || ((product) => {
    console.warn('[CATALOG] createProductCard not loaded from module');
    return null;
});

// Экспортируем для глобального доступа
window.loadCategories = loadCategories;
window.loadProducts = loadProducts;
window.renderCategories = renderCategories;
window.renderProducts = renderProducts;
window.selectCategory = selectCategory;
window.findCategory = findCategory;
window.applyClientFilters = applyClientFilters;
window.createProductCard = createProductCard;
// openFilterModal, closeFilterModal, applyFilters, resetFilters экспортируются позже (строка ~2397)

// ==================== Product Functions ====================
// Функции товара перенесены в modules/product.js
// Используем функции из модуля для обратной совместимости
const openProductPage = window.openProductPage || window.App?.product?.openProductPage || (async (productId) => {
    console.warn('[PRODUCT] openProductPage not loaded from module');
});
const closeProductPage = window.closeProductPage || window.App?.product?.closeProductPage || (() => {
    console.warn('[PRODUCT] closeProductPage not loaded from module');
});
const initGalleryNavigation = window.initGalleryNavigation || window.App?.product?.initGalleryNavigation || ((mediaCount) => {
    console.warn('[PRODUCT] initGalleryNavigation not loaded from module');
});
const changeGallerySlide = window.changeGallerySlide || window.App?.product?.changeGallerySlide || ((direction) => {
    console.warn('[PRODUCT] changeGallerySlide not loaded from module');
});
const goToGallerySlide = window.goToGallerySlide || window.App?.product?.goToGallerySlide || ((index) => {
    console.warn('[PRODUCT] goToGallerySlide not loaded from module');
});
const loadSellerProducts = window.loadSellerProducts || window.App?.product?.loadSellerProducts || (async (shopId, excludeProductId = null) => {
    console.warn('[PRODUCT] loadSellerProducts not loaded from module');
});

// Экспортируем для глобального доступа
window.openProductPage = openProductPage;
window.closeProductPage = closeProductPage;
window.initGalleryNavigation = initGalleryNavigation;
window.changeGallerySlide = changeGallerySlide;
window.goToGallerySlide = goToGallerySlide;
window.loadSellerProducts = loadSellerProducts;

// ==================== Shop Functions ====================
// Функции магазина перенесены в modules/shop.js
// Используем функции из модуля для обратной совместимости
const openShopPage = window.openShopPage || window.App?.shop?.openShopPage || (async (shopId) => {
    console.warn('[SHOP] openShopPage not loaded from module');
});
const loadShopData = window.loadShopData || window.App?.shop?.loadShopData || (async (shopId) => {
    console.warn('[SHOP] loadShopData not loaded from module');
});
const loadShopMap = window.loadShopMap || window.App?.shop?.loadShopMap || (async (container, shop) => {
    console.warn('[SHOP] loadShopMap not loaded from module');
});
const loadShopProducts = window.loadShopProducts || window.App?.shop?.loadShopProducts || (async (shopId) => {
    console.warn('[SHOP] loadShopProducts not loaded from module');
});
const loadShopReviews = window.loadShopReviews || window.App?.shop?.loadShopReviews || (async (shopId) => {
    console.warn('[SHOP] loadShopReviews not loaded from module');
});

// Экспортируем для глобального доступа
window.openShopPage = openShopPage;
window.loadShopData = loadShopData;
window.loadShopMap = loadShopMap;
window.loadShopProducts = loadShopProducts;
window.loadShopReviews = loadShopReviews;

// ==================== Cart Functions ====================
// Функции корзины перенесены в modules/cart.js
// Используем функции из модуля для обратной совместимости
const updateQuantity = window.updateQuantity || window.App?.cart?.updateQuantity || ((delta) => {
    console.warn('[CART] updateQuantity not loaded from module');
});
const addToCart = window.addToCart || window.App?.cart?.addToCart || (async () => {
    console.warn('[CART] addToCart not loaded from module');
});
const loadCart = window.loadCart || window.App?.cart?.loadCart || (async () => {
    console.warn('[CART] loadCart not loaded from module');
});
const renderCart = window.renderCart || window.App?.cart?.renderCart || (() => {
    console.warn('[CART] renderCart not loaded from module');
});
const updateCartSummary = window.updateCartSummary || window.App?.cart?.updateCartSummary || (() => {
    console.warn('[CART] updateCartSummary not loaded from module');
});
const updateCartQuantity = window.updateCartQuantity || window.App?.cart?.updateCartQuantity || (async (itemId, quantity) => {
    console.warn('[CART] updateCartQuantity not loaded from module');
});
const removeFromCart = window.removeFromCart || window.App?.cart?.removeFromCart || (async (itemId) => {
    console.warn('[CART] removeFromCart not loaded from module');
});
const clearCart = window.clearCart || window.App?.cart?.clearCart || (async () => {
    console.warn('[CART] clearCart not loaded from module');
});

// Экспортируем для глобального доступа
window.updateQuantity = updateQuantity;
window.addToCart = addToCart;
window.loadCart = loadCart;
window.renderCart = renderCart;
window.updateCartSummary = updateCartSummary;
window.updateCartQuantity = updateCartQuantity;
window.removeFromCart = removeFromCart;
window.clearCart = clearCart;

// Новые функции для UI корзины на странице товара
const updateProductPageCartUI = window.updateProductPageCartUI || window.App?.cart?.updateProductPageCartUI || ((productId) => {
    console.warn('[CART] updateProductPageCartUI not loaded from module');
});
const updateProductCartQuantity = window.updateProductCartQuantity || window.App?.cart?.updateProductCartQuantity || (async (delta) => {
    console.warn('[CART] updateProductCartQuantity not loaded from module');
});
window.updateProductPageCartUI = updateProductPageCartUI;
window.updateProductCartQuantity = updateProductCartQuantity;

// ==================== Favorites Functions ====================
// Функции избранного перенесены в modules/favorites.js
// Используем функции из модуля для обратной совместимости
const loadFavorites = window.loadFavorites || window.App?.favorites?.loadFavorites || (async () => {
    console.warn('[FAVORITES] loadFavorites not loaded from module');
});
const isProductFavorite = window.isProductFavorite || window.App?.favorites?.isProductFavorite || ((productId) => {
    console.warn('[FAVORITES] isProductFavorite not loaded from module');
    return false;
});
const updateFavoriteButtons = window.updateFavoriteButtons || window.App?.favorites?.updateFavoriteButtons || (() => {
    console.warn('[FAVORITES] updateFavoriteButtons not loaded from module');
});
const toggleFavorite = window.toggleFavorite || window.App?.favorites?.toggleFavorite || (async (productId) => {
    console.warn('[FAVORITES] toggleFavorite not loaded from module');
});
const renderFavorites = window.renderFavorites || window.App?.favorites?.renderFavorites || (async () => {
    console.warn('[FAVORITES] renderFavorites not loaded from module');
});

// Экспортируем для глобального доступа
window.loadFavorites = loadFavorites;
window.isProductFavorite = isProductFavorite;
window.updateFavoriteButtons = updateFavoriteButtons;
window.toggleFavorite = toggleFavorite;
window.renderFavorites = renderFavorites;

// ==================== Navigation Functions ====================
// Функции навигации и поиска перенесены в modules/navigation.js
// Используем функции из модуля для обратной совместимости
const openSearch = window.openSearch || window.App?.navigation?.openSearch || (() => {
    console.warn('[NAV] openSearch not loaded from module');
});
const closeSearch = window.closeSearch || window.App?.navigation?.closeSearch || (() => {
    console.warn('[NAV] closeSearch not loaded from module');
});
const handleSearch = window.handleSearch || window.App?.navigation?.handleSearch || (async () => {
    console.warn('[NAV] handleSearch not loaded from module');
});

// Экспортируем для глобального доступа
window.openSearch = openSearch;
window.closeSearch = closeSearch;
window.handleSearch = handleSearch;

// Поиск через header
async function handleHeaderSearch() {
    const query = elements.headerSearchInput?.value?.trim() || '';
    
    if (query.length === 0) {
        // Сбрасываем поиск - показываем все товары
        state.searchQuery = '';
        loadProducts();
        return;
    }
    
    if (query.length < 2) {
        return; // Минимум 2 символа
    }
    
    state.searchQuery = query;
    
    try {
        const products = await api.getProducts({ search: query });
        state.products = Array.isArray(products) ? products : (products?.items || products?.data || []);
        renderProducts();
    } catch (error) {
        console.error('[SEARCH] Error:', error);
    }
}

window.handleHeaderSearch = handleHeaderSearch;

// ==================== iOS Optimizations ====================

function initIOSOptimizations() {
    // Определяем iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || 
                  (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    
    if (isIOS) {
        document.documentElement.classList.add('ios');
        console.log('[iOS] iOS device detected');
    }
    
    // Устанавливаем правильную высоту viewport для iOS
    function setAppHeight() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
        document.documentElement.style.setProperty('--app-height', `${window.innerHeight}px`);
    }
    
    setAppHeight();
    window.addEventListener('resize', setAppHeight);
    window.addEventListener('orientationchange', () => {
        setTimeout(setAppHeight, 100);
    });
    
    // Предотвращаем bounce эффект на iOS
    document.body.addEventListener('touchmove', function(e) {
        if (e.target.closest('.page, .modal-content, .reviews-modal-body, .checkout-steps')) {
            return; // Разрешаем скролл внутри скроллируемых контейнеров
        }
        // Не блокируем если есть overflow scroll
        const target = e.target;
        if (target.scrollHeight > target.clientHeight || target.scrollWidth > target.clientWidth) {
            return;
        }
    }, { passive: true });
    
    // Предотвращаем двойной тап для зума на iOS
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function(e) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            e.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
    
    console.log('[iOS] iOS optimizations applied');
}

// ==================== Initialization ====================

async function init() {
    console.log('[INIT] Starting initialization...');
    
    // Применяем iOS оптимизации
    initIOSOptimizations();
    
    try {
        // Проверяем, что api загружен
        if (typeof api === 'undefined') {
            console.error('[INIT] API клиент не загружен! Проверьте, что api.js загружается первым.');
            alert('ОШИБКА: API клиент не загружен. Проверьте консоль (F12)');
            return;
        }
        
        // Инициализируем DOM элементы
        initElements();
        // Обновляем ссылку на elements в window.App для модулей
        window.App.elements = elements;
        console.log('[INIT] Elements initialized');
        
        // Проверяем, что основные элементы найдены (делаем проверку мягче)
        if (!elements.categoriesSlider) {
            console.error('[INIT] categoriesSlider не найден!');
        }
        if (!elements.productsGrid) {
            console.error('[INIT] productsGrid не найден!');
        }
        if (!elements.bottomNav) {
            console.warn('[INIT] bottomNav не найден, но продолжаем');
        }
        
        // Критичные элементы для загрузки данных
        if (!elements.productsGrid) {
            console.error('[INIT] Не могу продолжить без productsGrid');
            alert('ОШИБКА: Не найден элемент productsGrid. Проверьте консоль (F12).');
            return;
        }
        
        // Инициализация Telegram WebApp
        if (tg && tg.initDataUnsafe?.user) {
            tg.ready();
            
            // Предотвращаем случайное закрытие при прокрутке
            // Отслеживаем состояние прокрутки
            let isScrolling = false;
            let scrollTimeout = null;
            
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                mainContent.addEventListener('scroll', () => {
                    isScrolling = true;
                    
                    // Очищаем предыдущий таймер
                    if (scrollTimeout) {
                        clearTimeout(scrollTimeout);
                    }
                    
                    // Через 150ms после окончания прокрутки снимаем флаг
                    scrollTimeout = setTimeout(() => {
                        isScrolling = false;
                    }, 150);
                }, { passive: true });
                
                // Предотвращаем закрытие при активной прокрутке
                mainContent.addEventListener('touchmove', (e) => {
                    // Если прокрутка активна, предотвращаем закрытие
                    if (isScrolling) {
                        e.stopPropagation();
                    }
                }, { passive: true });
            }
            
            // Применяем тему Telegram
            applyTelegramTheme();
            
            // Получаем данные пользователя
            const user = tg.initDataUnsafe.user;
            api.setTelegramId(user.id);
            state.user = user;
            
            // Обновляем профиль
            if (elements.profileName) elements.profileName.textContent = user.first_name || 'Пользователь';
            if (elements.profileUsername) elements.profileUsername.textContent = user.username ? `@${user.username}` : '';
            
            // Загружаем фото профиля из Telegram
            if (user.photo_url) {
                const avatarImg = document.getElementById('profileAvatarImg');
                const avatarEmoji = document.getElementById('profileAvatarEmoji');
                if (avatarImg && avatarEmoji) {
                    avatarImg.src = user.photo_url;
                    avatarImg.onload = () => {
                        avatarImg.style.display = 'block';
                        avatarEmoji.style.display = 'none';
                    };
                    avatarImg.onerror = () => {
                        avatarImg.style.display = 'none';
                        avatarEmoji.style.display = 'block';
                    };
                }
            }
            
        // Регистрируем пользователя
        try {
            await api.createOrUpdateUser({
                telegram_id: user.id,
                username: user.username,
                first_name: user.first_name,
                last_name: user.last_name,
                language_code: user.language_code,
                is_premium: user.is_premium || false,
            });
        } catch (error) {
            console.error('Error registering user:', error);
        }
        
        // Проверяем параметр phone в URL (если вернулись из бота)
        const urlParams = new URLSearchParams(window.location.search);
        const phoneFromUrl = urlParams.get('phone');
        if (phoneFromUrl) {
            console.log('[INIT] Phone from URL:', phoneFromUrl);
            // Сохраняем номер телефона в state
            if (!state.user.phone) {
                state.user.phone = decodeURIComponent(phoneFromUrl);
            }
            // Очищаем URL от параметра
            window.history.replaceState({}, document.title, window.location.pathname);
        }
        } else {
            // Доступ только через Telegram
            console.error('Access denied: Telegram WebApp not detected');
            document.body.innerHTML = `
                <div style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: center;
                    padding: 20px;
                ">
                    <div style="font-size: 64px; margin-bottom: 20px;">🔒</div>
                    <h1 style="margin: 0 0 10px 0; font-size: 24px;">Доступ ограничен</h1>
                    <p style="margin: 0 0 30px 0; opacity: 0.8; font-size: 16px;">
                        Это приложение доступно только через Telegram
                    </p>
                    <a href="https://t.me/Daribri_bot" style="
                        background: #dbff00;
                        color: #000;
                        padding: 14px 32px;
                        border-radius: 12px;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 16px;
                    ">Открыть в Telegram</a>
                </div>
            `;
            return;
        }
        
        // Загружаем данные (для всех пользователей)
        console.log('[INIT] Loading categories and products...');
        console.log('[INIT] API baseUrl:', api.baseUrl);
        console.log('[INIT] Current location:', window.location.href);
        
        try {
            // Загружаем по очереди для лучшей диагностики
            await loadCategories();
            
            // Сначала загружаем избранное (если есть пользователь), чтобы карточки сразу рендерились с правильными сердечками
            if (state.user) {
                try {
                    await loadFavorites();
                    console.log('[INIT] Favorites loaded, count:', state.favorites.length);
                } catch (error) {
                    console.error('Error loading favorites:', error);
                    state.favorites = [];
                }
            } else {
                state.favorites = [];
            }
            
            // Теперь загружаем товары - они будут рендериться с правильными сердечками
            await loadProducts();
            
            // Инициализируем pull-to-refresh
            initPullToRefresh();
            
            console.log('[INIT] ✅ Данные загружены успешно');
            
            // Проверяем deep link параметр для открытия товара
            const urlParams = new URLSearchParams(window.location.search);
            const productIdParam = urlParams.get('product');
            if (productIdParam) {
                const productId = parseInt(productIdParam);
                if (productId && window.openProductPage) {
                    console.log('[INIT] Opening product from deep link:', productId);
                    setTimeout(() => {
                        window.openProductPage(productId);
                    }, 300);
                }
            }
        } catch (error) {
            console.error('[INIT] ❌ Failed to load initial data:', error);
            console.error('[INIT] Error stack:', error.stack);
            
            // Показываем сообщение пользователю
            if (elements.productsGrid) {
                elements.productsGrid.innerHTML = `
                    <div style="padding: 40px 20px; text-align: center; max-width: 400px; margin: 0 auto;">
                        <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                        <h3 style="margin-bottom: 8px; color: #333;">Не удалось загрузить данные</h3>
                        <p style="color: #666; margin-bottom: 12px; font-size: 14px;">
                            Проверьте:
                        </p>
                        <ul style="text-align: left; color: #666; font-size: 14px; margin-bottom: 20px; padding-left: 20px;">
                            <li>Сервер запущен на <strong>http://127.0.0.1:8080</strong></li>
                            <li>Откройте консоль (F12) для деталей</li>
                        </ul>
                        <div style="margin-bottom: 16px; padding: 12px; background: #f5f5f5; border-radius: 8px; font-size: 12px; color: #666; text-align: left;">
                            <strong>Ошибка:</strong><br>
                            ${error.message || 'Неизвестная ошибка'}
                        </div>
                        <button onclick="location.reload()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
                            Обновить страницу
                        </button>
                    </div>
                `;
            }
        }
        
        // Загружаем корзину отдельно (избранное уже загружено выше)
        if (state.user) {
            try {
                await loadCart();
            } catch (error) {
                console.error('Error loading cart:', error);
            }
        }
        
        // Скрываем кнопку "Мой магазин" по умолчанию (будет показана если магазин есть при переходе на профиль)
        if (elements.myShopBtn) {
            elements.myShopBtn.setAttribute('hidden', '');
            elements.myShopBtn.style.display = 'none';
        }
        
        // Инициализируем модуль подписки
        if (typeof initSubscriptionModule === 'function') {
            initSubscriptionModule(state, elements, api, {
                formatPrice: formatPrice,
                formatDateObject: formatDateObject,
                pluralize: pluralize,
                showToast: showToast,
                navigateTo: navigateTo
            });
            console.log('[INIT] Subscription module initialized');
        }
        
        // Инициализируем обработчики
        console.log('[INIT] Initializing event listeners...');
        initEventListeners();
        initSubscriptionManagementHandlers();
        initStatisticsDashboard();
        
        console.log('[INIT] Initialization complete!');
    } catch (error) {
        console.error('[INIT] Ошибка при инициализации:', error);
        console.error('Stack:', error.stack);
        alert('Ошибка инициализации: ' + error.message + '\nПроверьте консоль для деталей.');
    }
}

function applyTelegramTheme() {
    if (!tg?.themeParams) return;
    
    const theme = tg.themeParams;
    const root = document.documentElement;
    
    if (theme.bg_color) {
        root.style.setProperty('--bg-secondary', theme.bg_color);
    }
    if (theme.secondary_bg_color) {
        root.style.setProperty('--bg-primary', theme.secondary_bg_color);
        root.style.setProperty('--bg-tertiary', theme.secondary_bg_color);
    }
    if (theme.text_color) {
        root.style.setProperty('--text-primary', theme.text_color);
    }
    if (theme.hint_color) {
        root.style.setProperty('--text-secondary', theme.hint_color);
        root.style.setProperty('--text-muted', theme.hint_color);
    }
    if (theme.button_color) {
        root.style.setProperty('--primary', theme.button_color);
    }
}

// ==================== Data Loading ====================
// Функции loadCategories, loadProducts перенесены в modules/catalog.js
// Функция loadCart перенесена в modules/cart.js
// Функции loadFavorites, isProductFavorite, updateFavoriteButtons перенесены в modules/favorites.js

// ==================== Filters ====================

function openFilterModal() {
    console.log('[FILTER] openFilterModal called');
    console.log('[FILTER] elements.filterModal:', elements?.filterModal);
    
    if (!elements?.filterModal) {
        console.error('[FILTER] filterModal element not found');
        return;
    }
    
    // Заполняем поля фильтра текущими значениями
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
    console.log('[FILTER] Filter modal opened');
}

function closeFilterModal() {
    if (elements?.filterModal) {
        elements.filterModal.hidden = true;
    }
}

function applyFilters() {
    if (!elements) return;
    
    // Сохраняем значения из формы в state
    state.filters.minPrice = elements.filterMinPrice?.value ? parseFloat(elements.filterMinPrice.value) : null;
    state.filters.maxPrice = elements.filterMaxPrice?.value ? parseFloat(elements.filterMaxPrice.value) : null;
    state.filters.inStock = elements.filterInStock?.checked !== false;
    
    console.log('[FILTERS] Applied filters:', state.filters);
    
    closeFilterModal();
    loadProducts();
}

function resetFilters() {
    if (!elements) return;
    
    // Сбрасываем фильтры
    state.filters = {
        minPrice: null,
        maxPrice: null,
        inStock: true,
    };
    
    // Очищаем поля формы
    if (elements.filterMinPrice) elements.filterMinPrice.value = '';
    if (elements.filterMaxPrice) elements.filterMaxPrice.value = '';
    if (elements.filterInStock) elements.filterInStock.checked = true;
    
    console.log('[FILTERS] Filters reset');
    
    closeFilterModal();
    loadProducts();
}

// ==================== Rendering ====================
// Функции getCategoryIconFileName, renderCategories, renderProducts, createProductCard, initProductCardSlider, renderSubcategories перенесены в modules/catalog.js
// Функция renderFavorites перенесена в modules/favorites.js

// ==================== Event Listeners ====================

function initEventListeners() {
    console.log('[EVENTS] Setting up event listeners...');
    
    // Поиск
    if (!elements.categoriesSlider) {
        console.error('[EVENTS] Critical elements not found. Some features may not work.');
        return;
    }
    
    // Поиск через header
    console.log('[EVENTS] Setting up header search...');
    if (elements.headerSearchInput) {
        elements.headerSearchInput.addEventListener('input', debounce(handleHeaderSearch, 300));
        elements.headerSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                handleHeaderSearch();
            }
        });
    }
    
    // Модальное окно поиска (если используется)
    if (elements.closeSearch) {
        elements.closeSearch.addEventListener('click', closeSearch);
    }
    elements.searchInput?.addEventListener('input', debounce(handleSearch, 300));
    
    // Категории
    elements.categoriesSlider.addEventListener('click', (e) => {
        const chip = e.target.closest('.category-chip');
        if (chip) {
            const category = chip.dataset.category;
            selectCategory(category);
        }
    });
    
    // Кнопка назад на странице товара
    elements.productBackBtn?.addEventListener('click', () => {
        closeProductPage();
    });
    
    // Кнопки изменения количества удалены - теперь используем кнопки в корзине
    
    // Добавить в корзину
    elements.addToCartBtn?.addEventListener('click', addToCart);
    
    // Кнопки когда товар в корзине
    elements.cartQtyMinus?.addEventListener('click', () => updateProductCartQuantity(-1));
    elements.cartQtyPlus?.addEventListener('click', () => updateProductCartQuantity(1));
    elements.goToCartBtn?.addEventListener('click', () => {
        closeProductPage();
        navigateTo('cart');
    });
    
    // Избранное в модалке
    elements.productFavoriteBtn?.addEventListener('click', () => {
        if (state.currentProduct) {
            toggleFavorite(state.currentProduct.id);
        }
    });
    
    // Поделиться товаром
    elements.shareProductBtn?.addEventListener('click', () => {
        if (state.currentProduct) {
            shareProduct(state.currentProduct);
        }
    });
    
    // Фильтры
    console.log('[EVENTS] Setting up filter buttons...');
    console.log('[EVENTS] filterBtn:', elements.filterBtn);
    console.log('[EVENTS] filterModal:', elements.filterModal);
    console.log('[EVENTS] closeFilterModal:', elements.closeFilterModal);
    console.log('[EVENTS] applyFilters:', elements.applyFilters);
    console.log('[EVENTS] resetFilters:', elements.resetFilters);
    
    if (elements.filterBtn) {
        elements.filterBtn.addEventListener('click', () => {
            console.log('[CLICK] Filter button clicked');
            openFilterModal();
        });
    } else {
        console.error('[EVENTS] filterBtn not found!');
    }
    if (elements.closeFilterModal) {
        elements.closeFilterModal.addEventListener('click', () => {
            console.log('[CLICK] Close filter modal clicked');
            closeFilterModal();
        });
    } else {
        console.error('[EVENTS] closeFilterModal not found!');
    }
    if (elements.applyFilters) {
        elements.applyFilters.addEventListener('click', () => {
            console.log('[CLICK] Apply filters clicked');
            applyFilters();
        });
    } else {
        console.error('[EVENTS] applyFilters button not found!');
    }
    if (elements.resetFilters) {
        elements.resetFilters.addEventListener('click', () => {
            console.log('[CLICK] Reset filters clicked');
            resetFilters();
        });
    } else {
        console.error('[EVENTS] resetFilters button not found!');
    }
    
    // Навигация
    console.log('[EVENTS] Setting up navigation...');
    elements.bottomNav?.addEventListener('click', (e) => {
        console.log('[CLICK] Bottom nav clicked', e.target);
        const navItem = e.target.closest('.nav-item');
        if (navItem) {
            console.log('[NAV] Navigating to:', navItem.dataset.page);
            navigateTo(navItem.dataset.page);
        }
    });
    
    // Кнопки Header
    console.log('[EVENTS] Setting up header buttons...');
    elements.favoritesBtn?.addEventListener('click', () => {
        console.log('[CLICK] Favorites button clicked');
        navigateTo('favorites');
    });
    elements.cartBtn?.addEventListener('click', () => {
        console.log('[CLICK] Cart button clicked');
        navigateTo('cart');
    });
    
    // Корзина
    elements.clearCartBtn?.addEventListener('click', clearCart);
    elements.checkoutBtn?.addEventListener('click', checkout);
    
    // Обработчики модального окна оформления заказа
    const checkoutModal = document.getElementById('checkoutModal');
    const closeCheckoutModalBtns = document.querySelectorAll('[id^="closeCheckoutModal"]');
    closeCheckoutModalBtns.forEach(btn => {
        btn.addEventListener('click', closeCheckoutModal);
    });
    
    // Кнопки возврата на предыдущий шаг
    document.querySelectorAll('.back-to-step').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const step = parseInt(e.currentTarget.dataset.step);
            showCheckoutStep(step);
        });
    });
    
    // Закрытие модального окна при клике на фон
    if (checkoutModal) {
        checkoutModal.addEventListener('click', (e) => {
            if (e.target.id === 'checkoutModal') {
                closeCheckoutModal();
            }
        });
    }
    
    // Кнопки "Назад"
    document.querySelectorAll('[data-back]').forEach(btn => {
        btn.addEventListener('click', () => navigateTo(btn.dataset.back));
    });
    
    // Кнопка "Назад" на странице магазина
    const shopBackBtn = document.getElementById('shopBackBtn');
    if (shopBackBtn) {
        shopBackBtn.addEventListener('click', () => {
            // Если открыли из страницы товара, возвращаемся туда
            if (state.currentProduct) {
                navigateTo('product');
            } else {
                navigateTo('catalog');
            }
        });
    }
    
    // ============ My Orders ============
    
    // Открыть страницу заказов
    elements.myOrdersBtn?.addEventListener('click', () => navigateTo('myorders'));
    
    // ============ My Shop ============
    
    // Открыть страницу магазина
    elements.myShopBtn?.addEventListener('click', () => navigateTo('myshop'));
    
    // Настройки
    elements.settingsBtn?.addEventListener('click', () => navigateTo('settings'));
    
    // Помощь
    elements.helpBtn?.addEventListener('click', () => navigateTo('help'));
    
    // Сохранение настроек
    elements.saveSettingsBtn?.addEventListener('click', saveSettings);
    
    // Очистка кэша
    elements.clearCacheBtn?.addEventListener('click', clearCache);
    
    // Добавление на главный экран
    elements.addToHomeBtn?.addEventListener('click', addToHomeScreen);
    elements.addToHomeProfileBtn?.addEventListener('click', addToHomeScreen);
    
    // Счётчик символов в описании
    elements.shopDescription?.addEventListener('input', (e) => {
        elements.descCharCount.textContent = e.target.value.length;
    });
    
    // Загрузка фото магазина
    elements.shopPhotoUpload?.addEventListener('click', () => {
        elements.shopPhoto.click();
    });
    
    elements.shopPhoto?.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                elements.shopPhotoPreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
            };
            reader.readAsDataURL(file);
        }
    });
    
    // Форма создания магазина
    elements.shopCreateForm?.addEventListener('submit', handleCreateShop);
    
    // Кнопки управления магазином
    elements.editShopBtn?.addEventListener('click', openEditShopModal);
    elements.closeEditShopModal?.addEventListener('click', () => {
        elements.editShopModal.hidden = true;
    });
    elements.shopEditForm?.addEventListener('submit', handleUpdateShop);
    
    // Загрузка фото магазина в форме редактирования
    const editShopPhotoUpload = document.getElementById('editShopPhotoUpload');
    const editShopPhoto = document.getElementById('editShopPhoto');
    const editShopPhotoPreview = document.getElementById('editShopPhotoPreview');
    
    if (editShopPhotoUpload && editShopPhoto) {
        editShopPhotoUpload.addEventListener('click', () => {
            editShopPhoto.click();
        });
        
        editShopPhoto.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // Проверяем тип файла
                if (!file.type.startsWith('image/')) {
                    showToast('Выберите изображение', 'error');
                    return;
                }
                
                // Проверяем размер (макс 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    showToast('Файл слишком большой (максимум 5MB)', 'error');
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = (e) => {
                    if (editShopPhotoPreview) {
                        editShopPhotoPreview.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Подписки
    elements.manageSubscriptionBtn?.addEventListener('click', () => navigateTo('subscription-management'));
    
    // Товары
    elements.addProductBtn?.addEventListener('click', () => openAddProductModal());
    elements.addProductFromListBtn?.addEventListener('click', () => openAddProductModal());
    elements.addFirstProductBtn?.addEventListener('click', () => openAddProductModal());
    elements.closeAddProductModal?.addEventListener('click', () => {
        elements.addProductModal.hidden = true;
        resetProductForm();
    });
    elements.addProductForm?.addEventListener('submit', handleAddProduct);
    
    // Закрытие модалки по клику на фон
    document.getElementById('addProductModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'addProductModal') {
            elements.addProductModal.hidden = true;
            resetProductForm();
        }
    });
    
    // Мои товары
    elements.myProductsBtn?.addEventListener('click', () => navigateTo('myproducts'));
    
    // Заказы и отзывы магазина
    document.getElementById('shopOrdersBtn')?.addEventListener('click', () => {
        if (state.myShop) {
            navigateTo('shoporders');
        }
    });
    
    document.getElementById('shopReviewsBtn')?.addEventListener('click', () => {
        if (state.myShop) {
            navigateTo('shopreviews');
        }
    });
    
    document.getElementById('shopStatisticsBtn')?.addEventListener('click', () => {
        if (state.myShop) {
            navigateTo('shopstatistics');
        }
    });
}

// ==================== Actions ====================

// Функции selectCategory и findCategory перенесены в modules/catalog.js
// Функции openProductPage, closeProductPage, loadSellerProducts, initGalleryNavigation, changeGallerySlide, goToGallerySlide, updateQuantity, addToCart перенесены в modules/product.js

// ==================== Shop Page ====================
// Функции openShopPage, loadShopData, loadShopMap, loadShopReviews, loadShopProducts перенесены в modules/shop.js

// ==================== Checkout ====================
// Функции checkout перенесены в modules/checkout.js
// Используем функции из модуля для обратной совместимости
const checkout = window.checkout || window.App?.checkout?.checkout || (async () => {
    console.warn('[CHECKOUT] checkout not loaded from module');
});
const showCheckoutStep = window.showCheckoutStep || window.App?.checkout?.showCheckoutStep || ((step) => {
    console.warn('[CHECKOUT] showCheckoutStep not loaded from module');
});
const submitOrder = window.submitOrder || window.App?.checkout?.submitOrder || (async () => {
    console.warn('[CHECKOUT] submitOrder not loaded from module');
});
const closeCheckoutModal = window.closeCheckoutModal || window.App?.checkout?.closeCheckoutModal || (() => {
    console.warn('[CHECKOUT] closeCheckoutModal not loaded from module');
});

// Экспортируем для глобального доступа
window.checkout = checkout;
window.showCheckoutStep = showCheckoutStep;
window.submitOrder = submitOrder;
window.closeCheckoutModal = closeCheckoutModal;

// Константа и состояние checkout остаются в app.js для обратной совместимости
// В будущем можно вынести в modules/state.js
const DELIVERY_FEE = window.App?.checkout?.DELIVERY_FEE || 500;
let checkoutState = window.App?.checkout?.checkoutState || {
    step: 1,
    phone: null,
    address: null,
    addressIsValid: null,
    latitude: null,
    longitude: null,
    recipientName: '',
    deliveryComment: '',
    deliveryDate: null,
    deliveryTime: null,
    shopId: null,
    shopCity: null,
    items: [],
    promoCode: null,
    promoDiscount: 0,
    promoType: null
};

// Старые функции checkout удалены - используем из modules/checkout.js
// Полный код checkout находится в modules/checkout.js
// TODO: Перенести полный код checkout в modules/checkout.js (около 2000 строк)
// Временный код checkout оставлен здесь до полного переноса в модуль
// Полный код checkout (около 2000 строк) будет перенесен в modules/checkout.js позже
// ==================== Navigation ====================

// Функции navigateTo, openSearch, closeSearch, handleSearch перенесены в modules/navigation.js

// ==================== Utils ====================
// Функции getMediaUrl, formatPrice, formatDate, getOrderStatusText, updateCartBadge, updateFavoritesBadge, showLoading, showToast, debounce, pluralize перенесены в modules/utils.js

// ==================== My Shop ====================
// Все функции My Shop перенесены в modules/myshop.js

// Заглушки для обратной совместимости (если модули еще не загружены)
// Если модули загружены, используем функции из них
async function navigateTo(page) {
    console.log('[NAV] Navigating to:', page);
    
    // Скрываем header при переходе на страницы (кроме каталога)
    const header = document.querySelector('.header');
    if (header) {
        header.style.display = (page === 'catalog') ? 'block' : 'none';
    }
    
    // Скрываем все страницы (включая главную)
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.style.display = (page === 'catalog') ? 'block' : 'none';
    }
    
    const shopOrdersPage = document.getElementById('shopOrdersPage');
    const shopReviewsPage = document.getElementById('shopReviewsPage');
    const shopStatisticsPage = document.getElementById('shopStatisticsPage');
    
    const allPages = [
        elements.productPage,
        elements.cartPage, 
        elements.favoritesPage, 
        elements.profilePage,
        elements.myShopPage,
        elements.myProductsPage,
        elements.subscriptionManagementPage,
        elements.subscriptionPage,
        elements.shopPage,
        elements.settingsPage,
        elements.helpPage
    ];
    
    const myOrdersPage = document.getElementById('myOrdersPage');
    if (myOrdersPage) allPages.push(myOrdersPage);
    if (shopOrdersPage) allPages.push(shopOrdersPage);
    if (shopReviewsPage) allPages.push(shopReviewsPage);
    if (shopStatisticsPage) allPages.push(shopStatisticsPage);
    allPages.forEach(p => {
        if (p) {
            p.setAttribute('hidden', '');
            p.style.display = 'none';
        }
    });
    
    // Обновляем навигацию (только для основных страниц)
    const mainPages = ['catalog', 'favorites', 'cart', 'profile'];
    if (mainPages.includes(page)) {
        if (elements.bottomNav) {
            elements.bottomNav.querySelectorAll('.nav-item').forEach(item => {
                item.classList.toggle('active', item.dataset.page === page);
            });
        }
    }
    
    // Показываем нужную страницу
    switch (page) {
        case 'catalog':
            if (mainContent) {
                mainContent.style.display = 'block';
                mainContent.hidden = false;
            }
            if (header) header.style.display = 'block';
            window.scrollTo(0, 0);
            break;
        case 'product':
            if (elements.productPage) {
                elements.productPage.hidden = false;
                elements.productPage.style.display = 'flex';
                // Сбрасываем скролл
                setTimeout(() => {
                    elements.productPage.scrollTop = 0;
                }, 0);
            }
            break;
        case 'cart':
            if (elements.cartPage) {
                elements.cartPage.hidden = false;
                elements.cartPage.style.display = 'flex';
                setTimeout(() => {
                    elements.cartPage.scrollTop = 0;
                }, 0);
                await loadCart();
                renderCart();
            }
            break;
        case 'favorites':
            if (elements.favoritesPage) {
                elements.favoritesPage.hidden = false;
                elements.favoritesPage.style.display = 'flex';
                setTimeout(() => {
                    elements.favoritesPage.scrollTop = 0;
                }, 0);
                // Всегда перезагружаем избранное при открытии страницы для актуальности данных
                try {
                    await loadFavorites();
                    await renderFavorites();
                } catch (error) {
                    console.error('[NAV] Error loading favorites:', error);
                    // Показываем пустое состояние при ошибке
                    if (elements.favoritesEmpty) elements.favoritesEmpty.hidden = false;
                    if (elements.favoritesGrid) elements.favoritesGrid.innerHTML = '';
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
                
                // Заполняем данные профиля
                if (state.user) {
                    elements.profileName.textContent = state.user.first_name || 'Пользователь';
                    if (elements.profileUsername) {
                        elements.profileUsername.textContent = state.user.username ? `@${state.user.username}` : '';
                    }
                }
                
                // Проверяем наличие магазина и показываем/скрываем кнопку
                console.log('[PROFILE] About to call checkAndShowMyShopButton()');
                try {
                    if (typeof checkAndShowMyShopButton === 'function') {
                        console.log('[PROFILE] checkAndShowMyShopButton is a function, calling...');
                        await checkAndShowMyShopButton();
                    } else {
                        console.error('[PROFILE] checkAndShowMyShopButton is not defined! Type:', typeof checkAndShowMyShopButton);
                    }
                } catch (error) {
                    console.error('[PROFILE] Error in checkAndShowMyShopButton:', error);
                    console.error('[PROFILE] Error stack:', error.stack);
                }
            }
            break;
        case 'myorders':
            const myOrdersPageEl = document.getElementById('myOrdersPage');
            if (myOrdersPageEl) {
                myOrdersPageEl.hidden = false;
                myOrdersPageEl.style.display = 'flex';
                setTimeout(() => {
                    myOrdersPageEl.scrollTop = 0;
                }, 0);
                await loadUserOrders();
            }
            break;
        case 'myshop':
            if (elements.myShopPage) {
                elements.myShopPage.hidden = false;
                elements.myShopPage.style.display = 'flex';
                setTimeout(() => {
                    elements.myShopPage.scrollTop = 0;
                }, 0);
                await loadMyShop();
            }
            break;
        case 'shoporders':
            const shopOrdersPageEl = document.getElementById('shopOrdersPage');
            if (shopOrdersPageEl) {
                shopOrdersPageEl.hidden = false;
                shopOrdersPageEl.style.display = 'flex';
                setTimeout(() => {
                    shopOrdersPageEl.scrollTop = 0;
                }, 0);
                await loadShopOrders();
            }
            break;
        case 'shopreviews':
            const shopReviewsPageEl = document.getElementById('shopReviewsPage');
            if (shopReviewsPageEl) {
                shopReviewsPageEl.hidden = false;
                shopReviewsPageEl.style.display = 'flex';
                setTimeout(() => {
                    shopReviewsPageEl.scrollTop = 0;
                }, 0);
                await loadShopReviewsPage();
            }
            break;
        case 'shopstatistics':
            const shopStatisticsPageEl = document.getElementById('shopStatisticsPage');
            if (shopStatisticsPageEl) {
                shopStatisticsPageEl.hidden = false;
                shopStatisticsPageEl.style.display = 'flex';
                setTimeout(() => {
                    shopStatisticsPageEl.scrollTop = 0;
                }, 0);
                await loadShopStatistics();
            }
            break;
        case 'myproducts':
            if (elements.myProductsPage) {
                elements.myProductsPage.hidden = false;
                elements.myProductsPage.style.display = 'flex';
                setTimeout(() => {
                    elements.myProductsPage.scrollTop = 0;
                }, 0);
                await loadMyProducts();
            }
            break;
        case 'subscription-management':
            if (elements.subscriptionManagementPage) {
                elements.subscriptionManagementPage.hidden = false;
                elements.subscriptionManagementPage.style.display = 'flex';
                setTimeout(() => {
                    elements.subscriptionManagementPage.scrollTop = 0;
                }, 0);
                await loadSubscriptionManagement();
            }
            break;
        case 'subscription':
            if (elements.subscriptionPage) {
                elements.subscriptionPage.hidden = false;
                elements.subscriptionPage.style.display = 'flex';
                setTimeout(() => {
                    elements.subscriptionPage.scrollTop = 0;
                }, 0);
                if (typeof loadSubscriptionPage === 'function') {
                    await loadSubscriptionPage();
                }
            }
            break;
        case 'shop':
            if (elements.shopPage) {
                elements.shopPage.hidden = false;
                elements.shopPage.style.display = 'flex';
                setTimeout(() => {
                    elements.shopPage.scrollTop = 0;
                }, 0);
                // Данные загружаются в loadShopData, вызывается из openShopPage
            }
            break;
        case 'settings':
            if (elements.settingsPage) {
                elements.settingsPage.removeAttribute('hidden');
                elements.settingsPage.style.display = 'flex';
                setTimeout(() => {
                    elements.settingsPage.scrollTop = 0;
                }, 0);
                // loadSettings();
            } else {
                console.error('[NAV] settingsPage element not found');
            }
            break;
        case 'help':
            if (elements.helpPage) {
                elements.helpPage.removeAttribute('hidden');
                elements.helpPage.style.display = 'flex';
                setTimeout(() => {
                    elements.helpPage.scrollTop = 0;
                }, 0);
            } else {
                console.error('[NAV] helpPage element not found');
            }
            break;
    }
}

// ==================== Search ====================
// Функции поиска перенесены в modules/navigation.js

// ==================== Helpers ====================
// Все функции-утилиты (getMediaUrl, formatPrice, formatDate, getOrderStatusText, updateCartBadge, updateFavoritesBadge, showLoading, showToast, debounce) перенесены в modules/utils.js

// ==================== Demo Data ====================

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

// ==================== My Shop Functions ====================

// ==================== Shop Management ====================
// Функции управления магазином перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const checkAndShowMyShopButton = window.checkAndShowMyShopButton || (async () => {
    console.warn('[MYSHOP] checkAndShowMyShopButton not loaded from module');
});
const loadMyShop = window.loadMyShop || (async () => {
    console.warn('[MYSHOP] loadMyShop not loaded from module');
});
const renderShopPage = window.renderShopPage || (() => {
    console.warn('[MYSHOP] renderShopPage not loaded from module');
});
const handleCreateShop = window.handleCreateShop || (async (e) => {
    console.warn('[MYSHOP] handleCreateShop not loaded from module');
    e?.preventDefault();
});

// ==================== Shop Editing ====================
// Функции редактирования магазина перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const openEditShopModal = window.openEditShopModal || (() => {
    console.warn('[MYSHOP] openEditShopModal not loaded from module');
});
const handleUpdateShop = window.handleUpdateShop || (async (e) => {
    console.warn('[MYSHOP] handleUpdateShop not loaded from module');
    e?.preventDefault();
});

// Функции подписки перенесены в subscription.js

// ==================== Product Form Management ====================
// Функции управления формой товара перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const openAddProductModal = window.openAddProductModal || window.App?.myshop?.openAddProductModal || (async (productId = null) => {
    console.warn('[MYSHOP] openAddProductModal not loaded from module');
});
const loadProductForEdit = window.loadProductForEdit || window.App?.myshop?.loadProductForEdit || (async (productId) => {
    console.warn('[MYSHOP] loadProductForEdit not loaded from module');
});

// Экспортируем для глобального доступа
window.openAddProductModal = openAddProductModal;
window.loadProductForEdit = loadProductForEdit;
// resetProductForm, initProductFormHandlers, renderPhotosPreviews, handleAddProduct экспортируются позже

// Функция для редактирования товара
// ==================== Shop Products ====================
// Функции товаров магазина перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const editProduct = window.editProduct || (async (productId) => {
    console.warn('[MYSHOP] editProduct not loaded from module');
});
const loadMyProducts = window.loadMyProducts || (async () => {
    console.warn('[MYSHOP] loadMyProducts not loaded from module');
});

// Экспортируем для глобального доступа
window.editProduct = editProduct;
window.loadMyProducts = loadMyProducts;

// Состояние формы добавления/редактирования товара
// Используем window.productFormState, если он уже создан модулем myshop.js
// Иначе создаём новый объект (для обратной совместимости)
if (!window.productFormState) {
    window.productFormState = {
        photos: [],
        video: null,
        editingProductId: null, // ID товара для редактирования, null если создание
    };
}
const productFormState = window.productFormState;

function resetProductForm() {
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
    // Добавление фото
    const addPhotoBtn = document.getElementById('addPhotoBtn');
    const productPhotos = document.getElementById('productPhotos');
    
    if (addPhotoBtn && productPhotos) {
        addPhotoBtn.onclick = () => productPhotos.click();
        
        productPhotos.onchange = (e) => {
            const files = Array.from(e.target.files);
            const remaining = 5 - productFormState.photos.length;
            
            if (files.length > remaining) {
                showToast(`Можно добавить ещё ${remaining} фото`, 'error');
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
                showToast('Видео слишком большое (макс. 50 МБ)', 'error');
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
        const price = parseFloat(priceInput?.value) || 0;
        const discount = parseInt(discountInput?.value) || 0;
        const discountPreview = document.getElementById('discountPreview');
        
        if (price > 0 && discount > 0 && discountPreview) {
            const newPrice = price * (1 - discount / 100);
            const savings = price - newPrice;
            
            const oldPriceEl = document.getElementById('previewOldPrice');
            const newPriceEl = document.getElementById('previewNewPrice');
            const savingsEl = document.getElementById('previewSavings');
            
            if (oldPriceEl) oldPriceEl.textContent = formatPrice(price);
            if (newPriceEl) newPriceEl.textContent = formatPrice(newPrice);
            if (savingsEl) savingsEl.textContent = `-${formatPrice(savings)}`;
            
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
            elements.addProductModal.hidden = true;
        };
    }
}

function renderPhotosPreviews() {
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
        const displayUrl = photoUrl.startsWith('blob:') || photoUrl.startsWith('http') 
            ? photoUrl 
            : getMediaUrl(photoUrl);
        
        slot.innerHTML = `
            <img src="${displayUrl}" alt="Photo ${index + 1}" loading="lazy">
            <button type="button" class="remove-photo-btn" data-index="${index}">✕</button>
            ${index === 0 ? '<span class="primary-badge">Главное</span>' : ''}
        `;
        
        slot.querySelector('.remove-photo-btn').onclick = async (e) => {
            e.stopPropagation();
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
        showToast('Введите название товара', 'error');
        return;
    }
    
    if (!categoryId) {
        showToast('Выберите категорию', 'error');
        return;
    }
    
    if (!price || price <= 0) {
        showToast('Укажите корректную цену', 'error');
        return;
    }
    
    const isEditing = !!productFormState.editingProductId;
    
    if (!isEditing && productFormState.photos.length === 0) {
        showToast('Добавьте хотя бы одно фото', 'error');
        return;
    }
    
    // При редактировании проверяем, что есть хотя бы одно фото (новое или существующее)
    if (isEditing && productFormState.photos.length === 0) {
        showToast('Добавьте хотя бы одно фото', 'error');
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
        
        showToast(isEditing ? '✅ Товар успешно обновлён!' : '🎉 Товар успешно добавлен!', 'success');
        
        // Обновляем список товаров после сохранения
        if (isEditing) {
            await loadMyProducts();
        }
        elements.addProductModal.hidden = true;
        
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
        showToast(`Ошибка сохранения: ${errorMessage}`, 'error');
    } finally {
        submitBtn.disabled = false;
        if (btnText) btnText.hidden = false;
        if (btnLoader) btnLoader.hidden = true;
    }
}

// Экспортируем функции формы товара для глобального доступа
window.resetProductForm = resetProductForm;
window.initProductFormHandlers = initProductFormHandlers;
window.renderPhotosPreviews = renderPhotosPreviews;
window.handleAddProduct = handleAddProduct;

// ==================== Shop Orders ====================

// ==================== Orders ====================
// Функции заказов перенесены в modules/orders.js
// Используем функции из модуля для обратной совместимости
const loadShopOrders = window.loadShopOrders || (async (status) => {
    console.warn('[ORDERS] loadShopOrders not loaded from module');
});
const loadUserOrders = window.loadUserOrders || (async (status) => {
    console.warn('[ORDERS] loadUserOrders not loaded from module');
});
const updateOrderStatus = window.updateOrderStatus || (async (orderId, newStatus) => {
    console.warn('[ORDERS] updateOrderStatus not loaded from module');
});
const renderShopOrderCard = window.renderShopOrderCard || (() => {
    console.warn('[ORDERS] renderShopOrderCard not loaded from module');
    return '';
});
const renderUserOrderCard = window.renderUserOrderCard || (() => {
    console.warn('[ORDERS] renderUserOrderCard not loaded from module');
    return '';
});
const initOrderFilters = window.initOrderFilters || (() => {
    console.warn('[ORDERS] initOrderFilters not loaded from module');
});

// ==================== Shop Statistics Dashboard ====================
// Функции статистики перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const loadShopStatistics = window.loadShopStatistics || (() => {
    console.warn('[STATISTICS] loadShopStatistics not loaded from module');
});
const renderStatisticsCharts = window.renderStatisticsCharts || (() => {
    console.warn('[STATISTICS] renderStatisticsCharts not loaded from module');
});
const initStatisticsDashboard = window.initStatisticsDashboard || (() => {
    console.warn('[STATISTICS] initStatisticsDashboard not loaded from module');
});

// ==================== Shop Reviews Page ====================
// Функции отзывов магазина перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const loadShopReviewsPage = window.loadShopReviewsPage || (async () => {
    console.warn('[MYSHOP] loadShopReviewsPage not loaded from module');
});
const renderReviewsStats = window.renderReviewsStats || (() => {
    console.warn('[MYSHOP] renderReviewsStats not loaded from module');
});
const renderShopReviewCard = window.renderShopReviewCard || (() => {
    console.warn('[MYSHOP] renderShopReviewCard not loaded from module');
    return '';
});

// Эта функция удалена, так как правильная функция editProduct определена выше
// function editProduct(productId) {
//     showToast('Редактирование будет добавлено позже', 'info');
// }

// ============= Subscription Management =============

// ==================== Subscription Management ====================
// Функции управления подпиской перенесены в modules/myshop.js
// Используем функции из модуля для обратной совместимости
const loadSubscriptionManagement = window.loadSubscriptionManagement || (async () => {
    console.warn('[MYSHOP] loadSubscriptionManagement not loaded from module');
});
const loadSubscriptionUsage = window.loadSubscriptionUsage || (async () => {
    console.warn('[MYSHOP] loadSubscriptionUsage not loaded from module');
});
const renderSubscriptionManagementInfo = window.renderSubscriptionManagementInfo || (() => {
    console.warn('[MYSHOP] renderSubscriptionManagementInfo not loaded from module');
});
const renderNoSubscription = window.renderNoSubscription || (() => {
    console.warn('[MYSHOP] renderNoSubscription not loaded from module');
});
const loadSubscriptionHistory = window.loadSubscriptionHistory || (async () => {
    console.warn('[MYSHOP] loadSubscriptionHistory not loaded from module');
});
const initSubscriptionManagementHandlers = window.initSubscriptionManagementHandlers || (() => {
    console.warn('[MYSHOP] initSubscriptionManagementHandlers not loaded from module');
});

// Делаем функции глобальными для onclick
window.openProductPage = openProductPage;
window.openFilterModal = openFilterModal;
window.closeFilterModal = closeFilterModal;
window.applyFilters = applyFilters;
window.resetFilters = resetFilters;
window.openShopPage = openShopPage;
window.closeSearch = closeSearch;
window.updateCartQuantity = updateCartQuantity;
window.removeFromCart = removeFromCart;
// Функции подписки экспортированы из subscription.js
// window.editProduct и window.deleteProduct уже определены выше
// window.editProduct = editProduct;
// window.deleteProduct = deleteProduct;

// ==================== Settings ====================

// Загрузка настроек из localStorage
function loadSettings() {
    try {
        const settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
        
        if (elements.appVersion) elements.appVersion.textContent = '1.0.0';
        
        console.log('[SETTINGS] Settings loaded:', settings);
    } catch (error) {
        console.error('[SETTINGS] Error loading settings:', error);
    }
}

// Сохранение настроек в localStorage
function saveSettings() {
    try {
        const settings = {};
        
        localStorage.setItem('appSettings', JSON.stringify(settings));
        console.log('[SETTINGS] Settings saved:', settings);
        
        showToast('✅ Настройки сохранены', 'success');
        
        // Применяем настройки к приложению
        applySettings(settings);
    } catch (error) {
        console.error('[SETTINGS] Error saving settings:', error);
        showToast('Ошибка сохранения настроек', 'error');
    }
}

// Применение настроек к приложению
function applySettings(settings) {
    // Все настройки удалены, функция оставлена для совместимости
    console.log('[SETTINGS] Applying settings:', settings);
}

// Очистка кэша
function clearCache() {
    if (!confirm('Вы уверены, что хотите очистить кэш? Это может замедлить загрузку изображений.')) {
        return;
    }
    
    try {
        // Очищаем localStorage (кроме настроек и важных данных)
        const settings = localStorage.getItem('appSettings');
        const favorites = localStorage.getItem('favorites');
        
        localStorage.clear();
        
        // Восстанавливаем важные данные
        if (settings) localStorage.setItem('appSettings', settings);
        if (favorites) localStorage.setItem('favorites', favorites);
        
        // Очищаем все blob URL
        document.querySelectorAll('video[src^="blob:"], img[src^="blob:"]').forEach(el => {
            try {
                URL.revokeObjectURL(el.src);
            } catch (e) {
                // Игнорируем ошибки
            }
        });
        
        // Перезагружаем страницу для применения изменений
        showToast('✅ Кэш очищен. Страница будет перезагружена', 'success');
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    } catch (error) {
        console.error('[SETTINGS] Error clearing cache:', error);
        showToast('Ошибка очистки кэша', 'error');
    }
}

// Добавление на главный экран
function addToHomeScreen() {
    console.log('[SETTINGS] Add to home screen clicked');
    
    // Проверяем поддержку метода addToHomeScreen в Telegram WebApp (версия 8.0+)
    if (tg && tg.addToHomeScreen && tg.isVersionAtLeast && tg.isVersionAtLeast('8.0')) {
        console.log('[SETTINGS] Using Telegram addToHomeScreen API');
        try {
            tg.addToHomeScreen();
            return;
        } catch (e) {
            console.warn('[SETTINGS] addToHomeScreen failed:', e);
        }
    }
    
    // Fallback: показываем инструкции
    console.log('[SETTINGS] Telegram addToHomeScreen not available, showing instructions');
    
    // Определяем платформу
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    
    let instructions = '';
    if (isIOS) {
        instructions = `📱 Как добавить на главный экран (iOS):

Через Telegram (рекомендуется):
1. Нажмите на меню бота (≡) справа вверху
2. Выберите "Добавить на главный экран"

Альтернативный способ:
1. Нажмите кнопку "Поделиться" (□↑)
2. Выберите "На экран «Домой»"
3. Нажмите "Добавить"`;
    } else if (isAndroid) {
        instructions = `📱 Как добавить на главный экран (Android):

Через Telegram (рекомендуется):
1. Нажмите на меню бота (⋮) справа вверху
2. Выберите "Добавить на главный экран"

Альтернативный способ:
1. Откройте меню браузера (⋮)
2. Выберите "Добавить на главный экран"
3. Подтвердите добавление`;
    } else {
        instructions = `📱 Как добавить на главный экран:

1. Откройте меню Telegram бота
2. Выберите "Добавить на главный экран"

Или через браузер:
- Chrome/Edge: меню → "Установить приложение"
- Firefox: меню → "Установить"`;
    }
    
    // Показываем модальное окно с инструкциями
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
    modal.innerHTML = `
        <div class="modal-content" style="background: var(--bg-primary); padding: 24px; border-radius: 16px; max-width: 90%; max-height: 80%; overflow-y: auto;">
            <h2 style="margin-top: 0;">📲 Добавить на главный экран</h2>
            <div style="white-space: pre-line; line-height: 1.6; margin-bottom: 20px;">${instructions}</div>
            <button class="btn-primary" style="width: 100%;" onclick="this.closest('.modal').remove()">Понятно</button>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Закрытие по клику вне модального окна
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Загружаем настройки при инициализации
if (typeof window !== 'undefined') {
    window.addEventListener('load', () => {
        try {
            const settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
            applySettings(settings);
        } catch (error) {
            console.error('[SETTINGS] Error applying settings on load:', error);
        }
    });
}


// Тестовая функция для проверки кликов
window.testClick = function(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        console.log(`[TEST] Element ${elementId} found:`, el);
        el.style.border = '2px solid red';
        setTimeout(() => el.style.border = '', 1000);
    } else {
        console.error(`[TEST] Element ${elementId} NOT FOUND`);
    }
};

// Простой тест - если видите этот alert, скрипт загружен
console.log('🚀 app.js загружен!');

// ==================== Pull to Refresh ====================
function initPullToRefresh() {
    const mainContent = document.getElementById('mainContent');
    const pullIndicator = document.getElementById('pullToRefresh');
    
    if (!mainContent || !pullIndicator) return;
    
    let startY = 0;
    let currentY = 0;
    let isPulling = false;
    let isRefreshing = false;
    
    mainContent.addEventListener('touchstart', (e) => {
        if (mainContent.scrollTop === 0 && !isRefreshing) {
            startY = e.touches[0].clientY;
            isPulling = true;
        }
    }, { passive: true });
    
    mainContent.addEventListener('touchmove', (e) => {
        if (!isPulling || isRefreshing) return;
        
        currentY = e.touches[0].clientY;
        const pullDistance = currentY - startY;
        
        if (pullDistance > 0 && mainContent.scrollTop === 0) {
            const progress = Math.min(pullDistance / 100, 1);
            pullIndicator.style.transform = `translateY(${Math.min(pullDistance * 0.5, 60)}px)`;
            pullIndicator.querySelector('.ptr-text').textContent = 
                progress >= 1 ? 'Отпустите для обновления' : 'Потяните для обновления';
        }
    }, { passive: true });
    
    mainContent.addEventListener('touchend', async () => {
        if (!isPulling || isRefreshing) return;
        
        const pullDistance = currentY - startY;
        isPulling = false;
        
        if (pullDistance > 100 && mainContent.scrollTop === 0) {
            // Обновление
            isRefreshing = true;
            pullIndicator.classList.add('refreshing');
            pullIndicator.querySelector('.ptr-text').textContent = 'Обновление...';
            
            try {
                // Перезагружаем данные
                await loadCategories();
                await loadProducts({ forceRefresh: true });
            } catch (error) {
                console.error('Pull to refresh error:', error);
            }
            
            // Скрываем индикатор
            setTimeout(() => {
                pullIndicator.style.transform = '';
                pullIndicator.classList.remove('refreshing');
                isRefreshing = false;
            }, 500);
        } else {
            pullIndicator.style.transform = '';
        }
        
        startY = 0;
        currentY = 0;
    });
}

// Глобальная обработка ошибок
window.addEventListener('error', function(e) {
    console.error('❌ ГЛОБАЛЬНАЯ ОШИБКА:', e.error);
    console.error('Файл:', e.filename, 'Строка:', e.lineno);
    alert('ОШИБКА JavaScript: ' + e.message + '\nПроверьте консоль (F12)');
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('❌ Необработанное отклонение промиса:', e.reason);
});

// Инициализация
console.log('🚀 [APP] Script loaded, waiting for DOM...');
console.log('📄 Document readyState:', document.readyState);

try {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            console.log('✅ [APP] DOMContentLoaded fired');
            try {
                init();
            } catch (error) {
                console.error('❌ Ошибка в init():', error);
                alert('Ошибка инициализации: ' + error.message);
            }
        });
    } else {
        // DOM уже загружен
        console.log('✅ [APP] DOM already loaded, initializing immediately');
        try {
            init();
        } catch (error) {
            console.error('❌ Ошибка в init():', error);
            alert('Ошибка инициализации: ' + error.message);
        }
    }
} catch (error) {
    console.error('❌ Критическая ошибка при настройке инициализации:', error);
    alert('Критическая ошибка: ' + error.message);
}

// Проверка через 2 секунды
setTimeout(() => {
    console.log('🔍 Проверка инициализации...');
    if (typeof elements === 'undefined') {
        console.error('❌ ОШИБКА: elements не определён!');
    } else {
        console.log('✅ Приложение инициализировано успешно!');
    }
}, 2000);

// Глобальная проверка элементов после загрузки
setTimeout(() => {
    console.log('[APP] Element check after 1 second:');
    console.log('  bottomNav:', !!elements.bottomNav);
    console.log('  headerSearchInput:', !!elements.headerSearchInput);
}, 1000);


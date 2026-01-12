/**
 * State Module - глобальное состояние приложения и DOM элементы
 */

(function() {
    'use strict';

// Telegram WebApp
const tg = window.Telegram?.WebApp;

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
        trending: false,
    },
};

// DOM элементы (будут инициализированы после загрузки DOM)
let elements = {};

// Функция для безопасного получения элементов
function initElements() {
    elements = {
        // Header
        searchBtn: document.getElementById('searchBtn'),
        favoritesBtn: document.getElementById('favoritesBtn'),
        cartBtn: document.getElementById('cartBtn'),
        favoritesBadge: document.getElementById('favoritesBadge'),
        cartBadge: document.getElementById('cartBadge'),
        
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
        filterDiscounted: document.getElementById('filterDiscounted'),
        filterTrending: document.getElementById('filterTrending'),
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
        bannerSection: document.getElementById('bannerSection'),
        
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
        qtyMinus: document.getElementById('qtyMinus'),
        qtyPlus: document.getElementById('qtyPlus'),
        qtyValue: document.getElementById('qtyValue'),
        addToCartBtn: document.getElementById('addToCartBtn'),
        
        // Pages
        cartPage: document.getElementById('cartPage'),
        favoritesPage: document.getElementById('favoritesPage'),
        profilePage: document.getElementById('profilePage'),
        settingsPage: document.getElementById('settingsPage'),
        helpPage: document.getElementById('helpPage'),
        
        // Cart
        cartItems: document.getElementById('cartItems'),
        cartEmpty: document.getElementById('cartEmpty'),
        cartSummary: document.getElementById('cartSummary'),
        cartTotal: document.getElementById('cartTotal'),
        summaryCount: document.getElementById('summaryCount'),
        summarySubtotal: document.getElementById('summarySubtotal'),
        summaryDiscountRow: document.getElementById('summaryDiscountRow'),
        summaryDiscount: document.getElementById('summaryDiscount'),
        summaryTotal: document.getElementById('summaryTotal'),
        checkoutBtn: document.getElementById('checkoutBtn'),
        clearCartBtn: document.getElementById('clearCartBtn'),
        cartNavBadge: document.getElementById('cartNavBadge'),
        
        // Favorites
        favoritesGrid: document.getElementById('favoritesGrid'),
        favoritesEmpty: document.getElementById('favoritesEmpty'),
        
        // Profile
        profileName: document.getElementById('profileName'),
        profileUsername: document.getElementById('profileUsername'),
        profilePhone: document.getElementById('profilePhone'),
        profileAvatar: document.getElementById('profileAvatar'),
        
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
        shopOrdersPage: document.getElementById('shopOrdersPage'),
        shopReviewsPage: document.getElementById('shopReviewsPage'),
        shopStatisticsPage: document.getElementById('shopStatisticsPage'),
        shopProductsPage: document.getElementById('shopProductsPage'),
        shopSubscriptionPage: document.getElementById('shopSubscriptionPage'),
        
        // Shop Dashboard
        dashboardShopPhoto: document.getElementById('dashboardShopPhoto'),
        dashboardShopName: document.getElementById('dashboardShopName'),
        shopRating: document.getElementById('shopRating'),
        shopOrdersCount: document.getElementById('shopOrdersCount'),
        shopProductsCount: document.getElementById('shopProductsCount'),
        shopRevenue: document.getElementById('shopRevenue'),
        
        dashboardShopRating: document.getElementById('dashboardShopRating'),
        dashboardReviewsCount: document.getElementById('dashboardReviewsCount'),
        dashboardProductsCount: document.getElementById('dashboardProductsCount'),
        
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
        myProductsList: document.getElementById('myProductsList'),
        myProductsEmpty: document.getElementById('myProductsEmpty'),
        addProductFromListBtn: document.getElementById('addProductFromListBtn'),
        addFirstProductBtn: document.getElementById('addFirstProductBtn'),
        
        // Subscription Management
        subscriptionManagementPage: document.getElementById('subscriptionManagementPage'),
        shopPage: document.getElementById('shopPage'),
        subscriptionStatusBadge: document.getElementById('subscriptionStatusBadge'),
        managementPlanName: document.getElementById('managementPlanName'),
        subscriptionStartDate: document.getElementById('subscriptionStartDate'),
        subscriptionEndDate: document.getElementById('subscriptionEndDate'),
        subscriptionDaysRemaining: document.getElementById('subscriptionDaysRemaining'),
        subscriptionProgressFill: document.getElementById('subscriptionProgressFill'),
        extendSubscriptionBtn: document.getElementById('extendSubscriptionBtn'),
        changePlanBtn: document.getElementById('changePlanBtn'),
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
        
        // Orders
        shopOrdersList: document.getElementById('shopOrdersList'),
        ordersFilterTabs: document.querySelector('.orders-filter-tabs'),
        
        // User Orders
        myOrdersBtn: document.getElementById('myOrdersBtn'),
        myOrdersPage: document.getElementById('myOrdersPage'),
        userOrdersList: document.getElementById('userOrdersList'),
        userOrdersEmpty: document.getElementById('userOrdersEmpty'),
        
        // Profile menu items
        myShopBtn: document.getElementById('myShopBtn'),
        settingsBtn: document.getElementById('settingsBtn'),
        helpBtn: document.getElementById('helpBtn'),
        supportBtn: document.getElementById('supportBtn'),
        
        // Shop Reviews
        shopReviewsPage: document.getElementById('shopReviewsPage'),
    };
    
    // Проверяем, что основные элементы найдены
    const requiredElements = ['searchBtn', 'categoriesSlider', 'productsGrid', 'bottomNav'];
    const missing = requiredElements.filter(id => !elements[id]);
    if (missing.length > 0) {
        console.error('Missing required elements:', missing);
    }
}

// Экспортируем в глобальный объект App
window.App = window.App || {};
window.App.state = state;
window.App.elements = elements;
window.App.initElements = initElements;
window.App.tg = tg;

})();

/**
 * Main App Module - инициализация приложения
 */

import { loadCategories, loadProducts, initCategoryFilter } from './catalog.js';
import { initFavorites } from './favorites.js';
import { initCart } from './cart.js';
import { navigateTo } from './navigation.js';

async function init() {
    console.log('🌸 Дарибри App initializing...');
    
    // Init category filter
    initCategoryFilter();
    
    // Load initial data
    await loadCategories();
    await loadProducts();
    
    // Load user data in background
    await initFavorites();
    await initCart();
    
    console.log('✅ App initialized');
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', init);

// Expose navigation to window for onclick handlers in HTML
window.navigateTo = navigateTo;




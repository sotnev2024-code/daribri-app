/**
 * Дарибри - Main Application
 */

// ============= CONFIG =============
// Автоматически определяем URL API на основе текущего location
const API_URL = window.location.origin + '/api';
console.log('🌐 API URL:', API_URL);

// ============= STATE =============
const state = {
    currentQuantity: 1,
    cartItems: [],
    favoriteItems: [],
    currentSlide: 0,
    totalSlides: 0
};

// ============= API =============
async function apiRequest(endpoint, options = {}) {
    const response = await fetch(API_URL + endpoint, {
        ...options,
        headers: { 
            'X-Telegram-ID': '1724263429',
            'Content-Type': 'application/json',
            ...options.headers 
        }
    });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
}

function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU').format(price) + ' ₽';
}

// ============= NAVIGATION =============
function navigateTo(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    
    // Show target page
    const pageEl = document.getElementById(page + 'Page');
    if (pageEl) pageEl.classList.add('active');
    
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });
    
    // Load page data
    switch(page) {
        case 'catalog': loadProducts(); break;
        case 'favorites': loadFavorites(); break;
        case 'cart': loadCart(); break;
        case 'profile': loadProfile(); break;
    }
    
    window.scrollTo(0, 0);
}

// ============= CATALOG =============
function createProductCard(product) {
    const media = product.media || [];
    const firstMedia = media[0];
    const hasDiscount = product.discount_price && product.discount_price < product.price;
    const rating = product.shop_rating ? product.shop_rating.toFixed(1) : '—';
    
    const card = document.createElement('div');
    card.className = 'product-card';
    card.onclick = () => openProduct(product.id);
    
    let mediaHtml = '<div class="card-placeholder">🌸</div>';
    if (firstMedia) {
        mediaHtml = firstMedia.media_type === 'video'
            ? `<video src="${firstMedia.url}" muted></video>`
            : `<img src="${firstMedia.url}" alt="${product.name}" loading="lazy">`;
    } else if (product.primary_image) {
        mediaHtml = `<img src="${product.primary_image}" alt="${product.name}" loading="lazy">`;
    }
    
    const isFav = state.favoriteItems.some(f => f.product_id === product.id);
    
    card.innerHTML = `
        <div class="card-image">
            ${mediaHtml}
            <button class="card-favorite ${isFav ? 'active' : ''}" data-product-id="${product.id}">${isFav ? '♥' : '♡'}</button>
            ${hasDiscount ? `<div class="card-badge">-${Math.round((1 - product.discount_price / product.price) * 100)}%</div>` : ''}
            ${media.length > 1 ? `<div class="card-media-count">📷 ${media.length}</div>` : ''}
        </div>
        <div class="card-info">
            <div class="card-name">${product.name}</div>
            <div class="card-price">
                ${formatPrice(hasDiscount ? product.discount_price : product.price)}
                ${hasDiscount ? `<span class="card-old-price">${formatPrice(product.price)}</span>` : ''}
            </div>
            <div class="card-seller">
                <span class="card-seller-name">${product.shop_name || 'Магазин'}</span>
                <span class="card-seller-rating">⭐ ${rating}</span>
            </div>
        </div>
    `;
    
    // Favorite button handler
    const favBtn = card.querySelector('.card-favorite');
    favBtn.onclick = (e) => {
        e.stopPropagation();
        toggleFavorite(product.id, favBtn);
    };
    
    return card;
}

async function loadCategories() {
    try {
        const categories = await apiRequest('/categories/');
        const container = document.getElementById('categories');
        categories.forEach(cat => {
            const btn = document.createElement('button');
            btn.className = 'category-chip';
            btn.dataset.id = cat.id;
            btn.textContent = (cat.icon || '📦') + ' ' + cat.name;
            container.appendChild(btn);
        });
    } catch (e) { 
        console.error('Load categories error:', e); 
    }
}

async function loadProducts() {
    const container = document.getElementById('productsContainer');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        const products = await apiRequest('/products/');
        
        if (products.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🌷</div><p>Пока нет товаров</p></div>`;
            return;
        }
        
        const grid = document.createElement('div');
        grid.className = 'products-grid';
        products.forEach(product => grid.appendChild(createProductCard(product)));
        container.innerHTML = '';
        container.appendChild(grid);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><p>Ошибка загрузки: ${e.message}</p></div>`;
    }
}

// ============= PRODUCT DETAIL =============
async function openProduct(productId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('productPage').classList.add('active');
    
    const container = document.getElementById('productContent');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        const product = await apiRequest(`/products/${productId}?x_telegram_id=1724263429`);
        const sellerProducts = await apiRequest(`/shops/${product.shop_id}/products`).catch(() => []);
        renderProductDetail(product, sellerProducts);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><p>Ошибка загрузки</p></div>`;
    }
}

function renderProductDetail(product, sellerProducts) {
    const container = document.getElementById('productContent');
    const media = product.media || [];
    const hasDiscount = product.discount_price && product.discount_price < product.price;
    
    state.totalSlides = media.length;
    state.currentSlide = 0;
    state.currentQuantity = 1;
    
    let stockHtml = product.quantity > 10 
        ? '<div class="detail-stock">✓ В наличии</div>'
        : product.quantity > 0 
            ? `<div class="detail-stock low">⚠ Осталось ${product.quantity} шт</div>`
            : '<div class="detail-stock out">✕ Нет в наличии</div>';
    
    let slidesHtml = media.length > 0 
        ? media.map(m => `<div class="gallery-slide">${m.media_type === 'video' ? `<video src="${m.url}" controls></video>` : `<img src="${m.url}">`}</div>`).join('')
        : '<div class="gallery-slide"><div class="card-placeholder" style="height:100%;font-size:5rem;">🌸</div></div>';
    
    let dotsHtml = media.length > 1 ? `<div class="gallery-dots">${media.map((_, i) => `<div class="gallery-dot ${i === 0 ? 'active' : ''}" data-index="${i}"></div>`).join('')}</div>` : '';
    let arrowsHtml = media.length > 1 ? `<button class="gallery-arrow prev">‹</button><button class="gallery-arrow next">›</button>` : '';
    
    const otherProducts = sellerProducts.filter(p => p.id !== product.id).slice(0, 10);
    let sellerProductsHtml = otherProducts.length > 0 ? `
        <div class="section-title">Ещё товары продавца</div>
        <div class="seller-products-scroll">
            ${otherProducts.map(p => `
                <div class="mini-product-card" data-product-id="${p.id}">
                    <div class="mini-card-image">${p.primary_image ? `<img src="${p.primary_image}">` : '<div class="card-placeholder" style="height:100%">🌸</div>'}</div>
                    <div class="mini-card-info">
                        <div class="mini-card-name">${p.name}</div>
                        <div class="mini-card-price">${formatPrice(p.discount_price || p.price)}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    ` : '';
    
    container.innerHTML = `
        <div class="detail-gallery" id="productGallery">
            <div class="gallery-slides" id="gallerySlides">${slidesHtml}</div>
            ${media.length > 1 ? `<div class="gallery-counter"><span id="slideNum">1</span>/${media.length}</div>` : ''}
            <button class="gallery-favorite" data-product-id="${product.id}">${product.is_favorite ? '♥' : '♡'}</button>
            ${arrowsHtml}${dotsHtml}
        </div>
        <div class="detail-content">
            <h1 class="detail-name">${product.name}</h1>
            <div class="detail-price-row">
                <span class="detail-price">${formatPrice(hasDiscount ? product.discount_price : product.price)}</span>
                ${hasDiscount ? `<span class="detail-old-price">${formatPrice(product.price)}</span><span class="detail-discount">-${Math.round((1 - product.discount_price / product.price) * 100)}%</span>` : ''}
            </div>
            ${product.description ? `<p class="detail-description">${product.description}</p>` : ''}
            ${stockHtml}
            <div class="quantity-section">
                <span class="quantity-label">Количество:</span>
                <div class="quantity-controls">
                    <button class="qty-btn qty-minus">−</button>
                    <span class="qty-value" id="qtyValue">1</span>
                    <button class="qty-btn qty-plus">+</button>
                </div>
            </div>
            <button class="add-to-cart-btn" data-product-id="${product.id}">🛒 Добавить в корзину</button>
            <div class="seller-card">
                <div class="seller-header">
                    <div class="seller-avatar">${product.shop_photo ? `<img src="${product.shop_photo}">` : '🏪'}</div>
                    <div class="seller-details">
                        <div class="seller-shop-name">${product.shop_name || 'Магазин'}</div>
                        <div class="seller-stats">
                            <span class="seller-rating-stars">⭐ ${product.shop_rating?.toFixed(1) || '—'}</span>
                            <span>${product.shop_reviews_count || 0} отзывов</span>
                        </div>
                    </div>
                </div>
            </div>
            ${sellerProductsHtml}
        </div>
    `;
    
    initProductHandlers(product.id, media.length);
}

function initProductHandlers(productId, mediaCount) {
    // Quantity buttons
    document.querySelector('.qty-minus')?.addEventListener('click', () => {
        state.currentQuantity = Math.max(1, state.currentQuantity - 1);
        document.getElementById('qtyValue').textContent = state.currentQuantity;
    });
    document.querySelector('.qty-plus')?.addEventListener('click', () => {
        state.currentQuantity++;
        document.getElementById('qtyValue').textContent = state.currentQuantity;
    });
    
    // Add to cart
    document.querySelector('.add-to-cart-btn')?.addEventListener('click', () => addToCart(productId));
    
    // Favorite button
    const favBtn = document.querySelector('.gallery-favorite');
    if (favBtn) {
        favBtn.addEventListener('click', () => toggleFavorite(productId, favBtn));
    }
    
    // Gallery navigation
    if (mediaCount > 1) {
        document.querySelector('.gallery-arrow.prev')?.addEventListener('click', prevSlide);
        document.querySelector('.gallery-arrow.next')?.addEventListener('click', nextSlide);
        
        document.querySelectorAll('.gallery-dot').forEach(dot => {
            dot.addEventListener('click', () => goToSlide(parseInt(dot.dataset.index)));
        });
        
        // Touch swipe
        const gallery = document.getElementById('productGallery');
        let touchStartX = 0;
        gallery.addEventListener('touchstart', e => touchStartX = e.touches[0].clientX, { passive: true });
        gallery.addEventListener('touchend', e => {
            const diff = touchStartX - e.changedTouches[0].clientX;
            if (Math.abs(diff) > 50) diff > 0 ? nextSlide() : prevSlide();
        }, { passive: true });
    }
    
    // Mini product cards
    document.querySelectorAll('.mini-product-card').forEach(card => {
        card.addEventListener('click', () => openProduct(parseInt(card.dataset.productId)));
    });
}

function goToSlide(index) {
    if (index < 0) index = state.totalSlides - 1;
    if (index >= state.totalSlides) index = 0;
    state.currentSlide = index;
    
    const slides = document.getElementById('gallerySlides');
    if (slides) slides.style.transform = `translateX(-${index * 100}%)`;
    
    document.querySelectorAll('.gallery-dot').forEach((d, i) => d.classList.toggle('active', i === index));
    
    const counter = document.getElementById('slideNum');
    if (counter) counter.textContent = index + 1;
}

function nextSlide() { goToSlide(state.currentSlide + 1); }
function prevSlide() { goToSlide(state.currentSlide - 1); }

async function addToCart(productId) {
    try {
        await apiRequest('/cart/', { 
            method: 'POST', 
            body: JSON.stringify({ product_id: productId, quantity: state.currentQuantity }) 
        });
        await initCart();
        alert('Добавлено в корзину!');
    } catch (e) { 
        alert('Ошибка: ' + e.message); 
    }
}

// ============= FAVORITES =============
async function toggleFavorite(productId, btn) {
    const isActive = btn.classList.contains('active');
    try {
        if (isActive) {
            await apiRequest(`/favorites/${productId}`, { method: 'DELETE' });
            btn.classList.remove('active');
            btn.textContent = '♡';
            state.favoriteItems = state.favoriteItems.filter(f => f.product_id !== productId);
        } else {
            await apiRequest('/favorites/', { 
                method: 'POST',
                body: JSON.stringify({ product_id: productId })
            });
            btn.classList.add('active');
            btn.textContent = '♥';
            state.favoriteItems.push({ product_id: productId });
        }
    } catch (e) {
        console.error('Favorite error:', e);
    }
}

async function loadFavorites() {
    const container = document.getElementById('favoritesContainer');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        const favorites = await apiRequest('/favorites/');
        state.favoriteItems = favorites;
        
        if (favorites.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❤️</div><p>Пока ничего нет</p><p style="color:#666;margin-top:10px;">Добавляйте товары в избранное</p></div>`;
            return;
        }
        
        const grid = document.createElement('div');
        grid.className = 'products-grid';
        favorites.forEach(fav => {
            if (fav.product) grid.appendChild(createProductCard(fav.product));
        });
        container.innerHTML = '';
        container.appendChild(grid);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><p>Ошибка загрузки</p></div>`;
    }
}

async function initFavorites() {
    try {
        const favs = await apiRequest('/favorites/');
        state.favoriteItems = favs;
    } catch (e) {
        console.error('Init favorites error:', e);
    }
}

// ============= CART =============
async function loadCart() {
    const container = document.getElementById('cartContainer');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        const cart = await apiRequest('/cart/');
        state.cartItems = cart.items || [];
        
        if (state.cartItems.length === 0) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🛒</div><p>Корзина пуста</p><p style="color:#666;margin-top:10px;">Добавьте товары из каталога</p></div>`;
            updateCartBadge();
            return;
        }
        
        let itemsHtml = state.cartItems.map(item => `
            <div class="cart-item" data-id="${item.id}">
                <div class="cart-item-image">
                    ${item.product?.primary_image ? `<img src="${item.product.primary_image}">` : '<div class="card-placeholder" style="height:100%">🌸</div>'}
                </div>
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.product?.name || 'Товар'}</div>
                    <div class="cart-item-price">${formatPrice(item.product?.discount_price || item.product?.price || 0)}</div>
                    <div class="cart-item-controls">
                        <button class="cart-qty-btn cart-qty-minus" data-id="${item.id}" data-qty="${item.quantity}">−</button>
                        <span>${item.quantity}</span>
                        <button class="cart-qty-btn cart-qty-plus" data-id="${item.id}" data-qty="${item.quantity}">+</button>
                        <button class="cart-remove-btn" data-id="${item.id}">🗑️</button>
                    </div>
                </div>
            </div>
        `).join('');
        
        const total = state.cartItems.reduce((sum, item) => sum + (item.product?.discount_price || item.product?.price || 0) * item.quantity, 0);
        
        container.innerHTML = `
            ${itemsHtml}
            <div class="cart-summary">
                <div class="cart-summary-row"><span>Товары (${state.cartItems.length})</span><span>${formatPrice(total)}</span></div>
                <div class="cart-summary-row"><span>Доставка</span><span>Бесплатно</span></div>
                <div class="cart-summary-total"><span>Итого</span><span>${formatPrice(total)}</span></div>
            </div>
            <button class="checkout-btn">Оформить заказ</button>
        `;
        
        initCartHandlers();
        updateCartBadge();
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❌</div><p>Ошибка загрузки</p></div>`;
    }
}

function initCartHandlers() {
    document.querySelectorAll('.cart-qty-minus').forEach(btn => {
        btn.addEventListener('click', () => updateCartItem(parseInt(btn.dataset.id), parseInt(btn.dataset.qty) - 1));
    });
    
    document.querySelectorAll('.cart-qty-plus').forEach(btn => {
        btn.addEventListener('click', () => updateCartItem(parseInt(btn.dataset.id), parseInt(btn.dataset.qty) + 1));
    });
    
    document.querySelectorAll('.cart-remove-btn').forEach(btn => {
        btn.addEventListener('click', () => removeCartItem(parseInt(btn.dataset.id)));
    });
    
    document.querySelector('.checkout-btn')?.addEventListener('click', () => {
        alert('Оформление заказа - в разработке');
    });
}

async function updateCartItem(itemId, quantity) {
    if (quantity < 1) return removeCartItem(itemId);
    try {
        await apiRequest(`/cart/${itemId}`, { method: 'PATCH', body: JSON.stringify({ quantity }) });
        loadCart();
    } catch (e) { console.error('Update cart error:', e); }
}

async function removeCartItem(itemId) {
    try {
        await apiRequest(`/cart/${itemId}`, { method: 'DELETE' });
        loadCart();
    } catch (e) { console.error('Remove cart error:', e); }
}

function updateCartBadge() {
    const badge = document.getElementById('cartBadge');
    if (badge) {
        const count = state.cartItems.length;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'block' : 'none';
    }
}

async function initCart() {
    try {
        const cart = await apiRequest('/cart/');
        state.cartItems = cart.items || [];
        updateCartBadge();
    } catch (e) {
        console.error('Init cart error:', e);
    }
}

// ============= PROFILE =============
async function loadProfile() {
    try {
        const user = await apiRequest('/users/me');
        document.getElementById('profileName').textContent = user.first_name || 'Пользователь';
        document.getElementById('profileId').textContent = 'ID: ' + user.telegram_id;
    } catch (e) { console.error('Load profile error:', e); }
}

// ============= MY SHOP =============
let myShop = null;
let myProducts = [];
let myOrders = [];
let myReviews = [];
let mySubscription = null;
let productPhotos = [];
let currentShopTab = 'info';

async function openMyShop() {
    showPage('myShopPage');
    const container = document.getElementById('myShopContent');
    const tabsEl = document.getElementById('shopTabs');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        console.log('Loading shop...');
        myShop = await apiRequest('/shops/my');
        console.log('Shop response:', myShop);
        
        if (!myShop) {
            console.log('No shop found, showing create form');
            tabsEl.style.display = 'none';
            renderCreateShopForm();
        } else {
            console.log('Shop found:', myShop.name);
            tabsEl.style.display = 'flex';
            initShopTabs();
            await loadShopData();
            renderShopTab('info');
        }
    } catch (e) {
        console.error('Error loading shop:', e);
        tabsEl.style.display = 'none';
        renderCreateShopForm();
    }
}

function initShopTabs() {
    document.querySelectorAll('.shop-tab').forEach(tab => {
        tab.onclick = () => {
            document.querySelectorAll('.shop-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderShopTab(tab.dataset.tab);
        };
    });
}

async function loadShopData() {
    try {
        const [products, subscription] = await Promise.all([
            apiRequest(`/shops/${myShop.id}/products`),
            apiRequest('/subscriptions/my').catch(() => null)
        ]);
        myProducts = products || [];
        mySubscription = subscription;
    } catch (e) {
        myProducts = [];
    }
}

function renderShopTab(tab) {
    currentShopTab = tab;
    switch(tab) {
        case 'info': renderShopInfo(); break;
        case 'products': renderShopProducts(); break;
        case 'orders': renderShopOrders(); break;
        case 'reviews': renderShopReviews(); break;
        case 'settings': renderShopSettings(); break;
    }
}

function renderCreateShopForm() {
    const container = document.getElementById('myShopContent');
    container.innerHTML = `
        <div class="create-shop-container">
            <div class="create-shop-icon">🏪</div>
            <div class="create-shop-title">Создайте свой магазин</div>
            <div class="create-shop-text">Начните продавать товары прямо сейчас!</div>
            
            <form id="createShopForm">
                <div class="form-group">
                    <label class="form-label">Название магазина *</label>
                    <input type="text" class="form-input" id="shopName" placeholder="Например: Цветочный рай" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Описание</label>
                    <textarea class="form-textarea" id="shopDescription" placeholder="Расскажите о вашем магазине..." rows="3"></textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Телефон</label>
                    <input type="tel" class="form-input" id="shopPhone" placeholder="+7 (999) 123-45-67">
                </div>
                <div class="form-group">
                    <label class="form-label">Адрес</label>
                    <input type="text" class="form-input" id="shopAddress" placeholder="Город, улица, дом">
                </div>
                <button type="submit" class="btn-primary">Создать магазин</button>
            </form>
        </div>
    `;
    
    document.getElementById('createShopForm').addEventListener('submit', handleCreateShop);
}

async function handleCreateShop(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Создание...';
    
    try {
        const data = {
            name: document.getElementById('shopName').value,
            description: document.getElementById('shopDescription').value || null,
            phone: document.getElementById('shopPhone').value || null,
            address: document.getElementById('shopAddress').value || null
        };
        
        myShop = await apiRequest('/shops/', { method: 'POST', body: JSON.stringify(data) });
        alert('Магазин создан! 🎉');
        openMyShop();
    } catch (e) {
        alert('Ошибка: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Создать магазин';
    }
}

// ===== Shop Info Tab =====
function renderShopInfo() {
    const container = document.getElementById('myShopContent');
    const subEndDate = mySubscription ? new Date(mySubscription.end_date).toLocaleDateString('ru-RU') : null;
    const hasActiveSub = mySubscription && new Date(mySubscription.end_date) > new Date();
    
    container.innerHTML = `
        <div style="padding: 15px;">
            <!-- Shop Card -->
            <div class="shop-info-card">
                <div class="shop-info-header">
                    <div class="shop-info-avatar">
                        ${myShop.photo_url ? `<img src="${myShop.photo_url}">` : '🏪'}
                    </div>
                    <div class="shop-info-details">
                        <div class="shop-info-name">${myShop.name}</div>
                        <div class="shop-info-desc">${myShop.description || 'Нет описания'}</div>
                    </div>
                </div>
            </div>
            
            <!-- Subscription Banner -->
            <div class="subscription-banner ${hasActiveSub ? 'active' : ''}">
                <div class="subscription-banner-icon">${hasActiveSub ? '✨' : '⭐'}</div>
                <div class="subscription-banner-info">
                    <div class="subscription-banner-title">${hasActiveSub ? 'Подписка активна' : 'Нет подписки'}</div>
                    <div class="subscription-banner-text">${hasActiveSub ? `Действует до ${subEndDate}` : 'Подключите для добавления товаров'}</div>
                </div>
                <button class="subscription-banner-btn" onclick="openSubscription()">${hasActiveSub ? 'Продлить' : 'Подключить'}</button>
            </div>
            
            <!-- Quick Stats -->
            <div class="quick-stats">
                <div class="quick-stat">
                    <div class="quick-stat-value">${myProducts.length}</div>
                    <div class="quick-stat-label">Товаров</div>
                </div>
                <div class="quick-stat">
                    <div class="quick-stat-value">${myShop.orders_count || 0}</div>
                    <div class="quick-stat-label">Заказов</div>
                </div>
                <div class="quick-stat">
                    <div class="quick-stat-value">⭐${myShop.average_rating?.toFixed(1) || '—'}</div>
                    <div class="quick-stat-label">Рейтинг</div>
                </div>
                <div class="quick-stat">
                    <div class="quick-stat-value">${myShop.reviews_count || 0}</div>
                    <div class="quick-stat-label">Отзывов</div>
                </div>
            </div>
            
            <!-- Quick Actions Menu -->
            <div class="shop-menu">
                <div class="shop-menu-item" onclick="openAddProduct()">
                    <div class="shop-menu-icon">📦</div>
                    <div class="shop-menu-text">
                        <div class="shop-menu-title">Добавить товар</div>
                        <div class="shop-menu-subtitle">Разместите новый товар</div>
                    </div>
                    <span class="shop-menu-arrow">→</span>
                </div>
                <div class="shop-menu-item" onclick="renderShopTab('products')">
                    <div class="shop-menu-icon">🛍️</div>
                    <div class="shop-menu-text">
                        <div class="shop-menu-title">Мои товары</div>
                        <div class="shop-menu-subtitle">${myProducts.length} товаров</div>
                    </div>
                    <span class="shop-menu-arrow">→</span>
                </div>
                <div class="shop-menu-item" onclick="renderShopTab('orders')">
                    <div class="shop-menu-icon">📋</div>
                    <div class="shop-menu-text">
                        <div class="shop-menu-title">Заказы</div>
                        <div class="shop-menu-subtitle">${myShop.orders_count || 0} заказов</div>
                    </div>
                    ${myShop.pending_orders ? `<span class="shop-menu-badge">${myShop.pending_orders}</span>` : ''}
                    <span class="shop-menu-arrow">→</span>
                </div>
                <div class="shop-menu-item" onclick="renderShopTab('reviews')">
                    <div class="shop-menu-icon">💬</div>
                    <div class="shop-menu-text">
                        <div class="shop-menu-title">Отзывы</div>
                        <div class="shop-menu-subtitle">${myShop.reviews_count || 0} отзывов</div>
                    </div>
                    <span class="shop-menu-arrow">→</span>
                </div>
                <div class="shop-menu-item" onclick="renderShopTab('settings')">
                    <div class="shop-menu-icon">⚙️</div>
                    <div class="shop-menu-text">
                        <div class="shop-menu-title">Настройки</div>
                        <div class="shop-menu-subtitle">Редактировать магазин</div>
                    </div>
                    <span class="shop-menu-arrow">→</span>
                </div>
            </div>
        </div>
    `;
}

// ===== Products Tab =====
function renderShopProducts() {
    const container = document.getElementById('myShopContent');
    
    const productsHtml = myProducts.length > 0 
        ? myProducts.map(p => `
            <div class="my-product-item">
                <div class="my-product-image">
                    ${p.primary_image ? `<img src="${p.primary_image}">` : '<div class="card-placeholder" style="height:100%">🌸</div>'}
                </div>
                <div class="my-product-info">
                    <div class="my-product-name">${p.name}</div>
                    <div class="my-product-price">${formatPrice(p.discount_price || p.price)}</div>
                    <div class="my-product-stock">В наличии: ${p.quantity} шт</div>
                </div>
                <div class="my-product-actions">
                    <button class="my-product-btn" onclick="editProduct(${p.id})">✏️</button>
                    <button class="my-product-btn delete" onclick="deleteProduct(${p.id})">🗑️</button>
                </div>
            </div>
        `).join('')
        : '<div class="empty-state"><div class="empty-state-icon">📦</div><p>Пока нет товаров</p><p style="color:#888;font-size:0.9rem;margin-top:10px;">Добавьте свой первый товар</p></div>';
    
    container.innerHTML = `
        <div style="padding: 15px;">
            <div class="shop-products-header">
                <div class="shop-products-title">Мои товары (${myProducts.length})</div>
                <button class="add-product-btn" onclick="openAddProduct()">➕ Добавить</button>
            </div>
            ${productsHtml}
        </div>
    `;
}

// ===== Orders Tab =====
async function renderShopOrders() {
    const container = document.getElementById('myShopContent');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        myOrders = await apiRequest('/orders/shop').catch(() => []);
    } catch (e) {
        myOrders = [];
    }
    
    const ordersHtml = myOrders.length > 0
        ? myOrders.map(o => `
            <div class="order-item">
                <div class="order-header">
                    <div>
                        <div class="order-number">Заказ #${o.id}</div>
                        <div class="order-date">${new Date(o.created_at).toLocaleDateString('ru-RU')}</div>
                    </div>
                    <div class="order-status ${o.status}">${getOrderStatusText(o.status)}</div>
                </div>
                <div class="order-products">
                    ${(o.items || []).slice(0, 3).map(item => `
                        <div class="order-product-thumb">
                            ${item.product?.primary_image ? `<img src="${item.product.primary_image}">` : '🌸'}
                        </div>
                    `).join('')}
                    ${(o.items?.length || 0) > 3 ? `<div class="order-product-thumb" style="display:flex;align-items:center;justify-content:center;font-size:0.8rem;">+${o.items.length - 3}</div>` : ''}
                </div>
                <div class="order-footer">
                    <div class="order-total">${formatPrice(o.total_amount)}</div>
                    <button class="btn-secondary" style="padding:8px 16px;width:auto;">Подробнее</button>
                </div>
            </div>
        `).join('')
        : '<div class="empty-state"><div class="empty-state-icon">📋</div><p>Пока нет заказов</p></div>';
    
    container.innerHTML = `<div style="padding: 15px;">${ordersHtml}</div>`;
}

function getOrderStatusText(status) {
    const statuses = {
        pending: 'Ожидает',
        processing: 'В обработке',
        completed: 'Выполнен',
        cancelled: 'Отменён'
    };
    return statuses[status] || status;
}

// ===== Reviews Tab =====
async function renderShopReviews() {
    const container = document.getElementById('myShopContent');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        myReviews = await apiRequest(`/reviews/shop/${myShop.id}`).catch(() => []);
    } catch (e) {
        myReviews = [];
    }
    
    const reviewsHtml = myReviews.length > 0
        ? myReviews.map(r => `
            <div class="review-item">
                <div class="review-header">
                    <div class="review-avatar">👤</div>
                    <div class="review-author">
                        <div class="review-name">${r.user_name || 'Покупатель'}</div>
                        <div class="review-date">${new Date(r.created_at).toLocaleDateString('ru-RU')}</div>
                    </div>
                    <div class="review-rating">${'⭐'.repeat(r.rating)}</div>
                </div>
                ${r.comment ? `<div class="review-text">${r.comment}</div>` : ''}
                ${r.product_name ? `<div class="review-product">📦 ${r.product_name}</div>` : ''}
            </div>
        `).join('')
        : '<div class="empty-state"><div class="empty-state-icon">💬</div><p>Пока нет отзывов</p></div>';
    
    container.innerHTML = `<div style="padding: 15px;">${reviewsHtml}</div>`;
}

// ===== Settings Tab =====
function renderShopSettings() {
    const container = document.getElementById('myShopContent');
    
    container.innerHTML = `
        <div style="padding: 15px;">
            <form id="shopSettingsForm">
                <!-- Basic Info -->
                <div class="settings-section">
                    <div class="settings-section-title">Основная информация</div>
                    <div class="settings-item">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label">Название магазина</label>
                            <input type="text" class="form-input" id="settingsName" value="${myShop.name}" required>
                        </div>
                    </div>
                    <div class="settings-item">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label">Описание</label>
                            <textarea class="form-textarea" id="settingsDescription" rows="3">${myShop.description || ''}</textarea>
                        </div>
                    </div>
                </div>
                
                <!-- Contacts -->
                <div class="settings-section">
                    <div class="settings-section-title">Контакты</div>
                    <div class="settings-item">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label">Телефон</label>
                            <input type="tel" class="form-input" id="settingsPhone" value="${myShop.phone || ''}">
                        </div>
                    </div>
                    <div class="settings-item">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-input" id="settingsEmail" value="${myShop.email || ''}">
                        </div>
                    </div>
                    <div class="settings-item">
                        <div class="form-group" style="margin:0;">
                            <label class="form-label">Адрес</label>
                            <input type="text" class="form-input" id="settingsAddress" value="${myShop.address || ''}">
                        </div>
                    </div>
                </div>
                
                <!-- Delivery Settings -->
                <div class="settings-section">
                    <div class="settings-section-title">Настройки доставки</div>
                    <div class="settings-item">
                        <div class="settings-toggle" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0;">
                            <div>
                                <div style="font-weight: 500; margin-bottom: 4px;">Самовывоз</div>
                                <div style="font-size: 0.9em; color: #666;">Разрешить покупателям забирать заказы самостоятельно</div>
                            </div>
                            <label class="toggle-switch" style="position: relative; display: inline-block; width: 50px; height: 28px;">
                                <input type="checkbox" id="settingsPickupEnabled" ${myShop.pickup_enabled !== false ? 'checked' : ''} style="opacity: 0; width: 0; height: 0;">
                                <span class="toggle-slider" style="position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: ${myShop.pickup_enabled !== false ? '#4CAF50' : '#ccc'}; transition: .4s; border-radius: 28px;">
                                    <span class="toggle-slider-thumb" style="position: absolute; content: ''; height: 20px; width: 20px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; ${myShop.pickup_enabled !== false ? 'transform: translateX(22px);' : ''}"></span>
                                </span>
                            </label>
                        </div>
                    </div>
                </div>
                
                <button type="submit" class="btn-primary" style="margin-top:10px;">Сохранить изменения</button>
            </form>
            
            <!-- Danger Zone -->
            <div class="settings-section" style="margin-top:20px;">
                <div class="settings-section-title" style="color:#dbff00;">Опасная зона</div>
                <div class="settings-item">
                    <div class="settings-toggle">
                        <span>Деактивировать магазин</span>
                        <button class="btn-secondary" style="width:auto;padding:8px 16px;color:#dbff00;" onclick="deactivateShop()">Деактивировать</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('shopSettingsForm').addEventListener('submit', handleSaveSettings);
    
    // Обработчик для переключателя самовывоза
    const pickupToggle = document.getElementById('settingsPickupEnabled');
    if (pickupToggle) {
        pickupToggle.addEventListener('change', function() {
            const slider = this.nextElementSibling;
            const thumb = slider.querySelector('.toggle-slider-thumb');
            if (this.checked) {
                slider.style.backgroundColor = '#4CAF50';
                thumb.style.transform = 'translateX(22px)';
            } else {
                slider.style.backgroundColor = '#ccc';
                thumb.style.transform = 'translateX(0)';
            }
        });
    }
}

async function handleSaveSettings(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Сохранение...';
    
    try {
        const pickupEnabledCheckbox = document.getElementById('settingsPickupEnabled');
        const data = {
            name: document.getElementById('settingsName').value,
            description: document.getElementById('settingsDescription').value || null,
            phone: document.getElementById('settingsPhone').value || null,
            email: document.getElementById('settingsEmail').value || null,
            address: document.getElementById('settingsAddress').value || null,
            pickup_enabled: pickupEnabledCheckbox ? pickupEnabledCheckbox.checked : true
        };
        
        myShop = await apiRequest(`/shops/${myShop.id}`, { method: 'PATCH', body: JSON.stringify(data) });
        alert('Настройки сохранены!');
        btn.disabled = false;
        btn.textContent = 'Сохранить изменения';
    } catch (e) {
        alert('Ошибка: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Сохранить изменения';
    }
}

function deactivateShop() {
    if (!confirm('Вы уверены? Магазин будет скрыт от покупателей.')) return;
    alert('Магазин деактивирован (демо)');
}

// ============= ADD PRODUCT =============
function openAddProduct() {
    if (!myShop) {
        alert('Сначала создайте магазин!');
        openMyShop();
        return;
    }
    
    showPage('addProductPage');
    productPhotos = [];
    renderPhotosPreview();
    loadCategoriesSelect();
    
    document.getElementById('productForm').reset();
    document.getElementById('productForm').onsubmit = handleAddProduct;
    document.getElementById('photoInput').onchange = handlePhotoSelect;
}

async function loadCategoriesSelect() {
    try {
        const categories = await apiRequest('/categories/');
        const select = document.getElementById('productCategory');
        select.innerHTML = '<option value="">Выберите категорию</option>';
        categories.forEach(cat => {
            select.innerHTML += `<option value="${cat.id}">${cat.icon || ''} ${cat.name}</option>`;
        });
    } catch (e) {}
}

function handlePhotoSelect(e) {
    const files = Array.from(e.target.files);
    
    files.forEach(file => {
        const reader = new FileReader();
        reader.onload = (event) => {
            productPhotos.push({
                file: file,
                url: event.target.result
            });
            renderPhotosPreview();
        };
        reader.readAsDataURL(file);
    });
    
    e.target.value = '';
}

function renderPhotosPreview() {
    const container = document.getElementById('photosPreview');
    container.innerHTML = productPhotos.map((photo, i) => `
        <div class="photo-preview">
            <img src="${photo.url}">
            <button type="button" class="photo-remove" onclick="removePhoto(${i})">×</button>
        </div>
    `).join('');
}

function removePhoto(index) {
    productPhotos.splice(index, 1);
    renderPhotosPreview();
}

async function handleAddProduct(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Добавление...';
    
    try {
        const media = productPhotos.map((photo, i) => ({
            media_type: 'photo',
            url: photo.url,
            is_primary: i === 0,
            sort_order: i
        }));
        
        const data = {
            name: document.getElementById('productName').value,
            description: document.getElementById('productDescription').value || null,
            price: parseFloat(document.getElementById('productPrice').value),
            discount_price: document.getElementById('productDiscount').value ? parseFloat(document.getElementById('productDiscount').value) : null,
            quantity: parseInt(document.getElementById('productQuantity').value) || 1,
            category_id: document.getElementById('productCategory').value ? parseInt(document.getElementById('productCategory').value) : null,
            is_trending: document.getElementById('productTrending').checked,
            media: media
        };
        
        await apiRequest('/products/', { method: 'POST', body: JSON.stringify(data) });
        alert('Товар добавлен! 🎉');
        openMyShop();
    } catch (e) {
        alert('Ошибка: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Добавить товар';
    }
}

function editProduct(productId) {
    alert('Редактирование товара - в разработке');
}

async function deleteProduct(productId) {
    if (!confirm('Удалить этот товар?')) return;
    
    try {
        await apiRequest(`/products/${productId}`, { method: 'DELETE' });
        await loadMyProducts();
        renderMyShop();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

// ============= SUBSCRIPTION =============
async function openSubscription() {
    showPage('subscriptionPage');
    const container = document.getElementById('subscriptionContent');
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    try {
        const [plans, currentSub] = await Promise.all([
            apiRequest('/subscriptions/plans'),
            apiRequest('/subscriptions/my').catch(() => null)
        ]);
        
        renderSubscription(plans, currentSub);
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">❌</div><p>Ошибка загрузки</p></div>';
    }
}

function renderSubscription(plans, currentSub) {
    const container = document.getElementById('subscriptionContent');
    
    const currentPlanId = currentSub?.plan_id;
    const endDate = currentSub ? new Date(currentSub.end_date).toLocaleDateString('ru-RU') : null;
    
    container.innerHTML = `
        <div style="padding: 20px;">
            ${currentSub ? `
                <div class="subscription-card current">
                    <div class="subscription-header">
                        <div>
                            <div class="subscription-name">Текущая подписка<span class="subscription-badge">Активна</span></div>
                        </div>
                    </div>
                    <div class="subscription-feature">
                        <span>📅</span> Действует до: ${endDate}
                    </div>
                </div>
            ` : `
                <div class="empty-state" style="padding: 20px 0;">
                    <div class="empty-state-icon">⭐</div>
                    <p>У вас нет активной подписки</p>
                </div>
            `}
            
            <div class="section-title">Тарифные планы</div>
            
            ${plans.map(plan => `
                <div class="subscription-card ${plan.id === currentPlanId ? 'active' : ''}" onclick="subscribeToPlan(${plan.id})">
                    <div class="subscription-header">
                        <div class="subscription-name">${plan.name}</div>
                        <div class="subscription-price">
                            <div class="subscription-price-value">${formatPrice(plan.price)}</div>
                            <div class="subscription-price-period">${plan.duration_days} дней</div>
                        </div>
                    </div>
                    <div class="subscription-features">
                        <div class="subscription-feature">
                            <span class="subscription-feature-icon">✓</span>
                            До ${plan.max_products} товаров
                        </div>
                        ${plan.features?.analytics ? '<div class="subscription-feature"><span class="subscription-feature-icon">✓</span> Аналитика</div>' : ''}
                        ${plan.features?.priority_support ? '<div class="subscription-feature"><span class="subscription-feature-icon">✓</span> Приоритетная поддержка</div>' : ''}
                        ${plan.features?.promotions ? `<div class="subscription-feature"><span class="subscription-feature-icon">✓</span> ${plan.features.promotions} промо-акций</div>` : ''}
                    </div>
                    ${plan.id !== currentPlanId ? '<button class="btn-primary" style="margin-top:15px;">Выбрать план</button>' : ''}
                </div>
            `).join('')}
        </div>
    `;
}

async function subscribeToPlan(planId) {
    if (!myShop) {
        alert('Сначала создайте магазин!');
        openMyShop();
        return;
    }
    
    if (!confirm('Подключить этот тариф? (тестовый режим)')) return;
    
    try {
        await apiRequest('/subscriptions/subscribe', { 
            method: 'POST', 
            body: JSON.stringify({ plan_id: planId }) 
        });
        alert('Подписка активирована! 🎉');
        openSubscription();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

// ============= HELPERS =============
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId)?.classList.add('active');
    window.scrollTo(0, 0);
}

// ============= INIT =============
async function init() {
    console.log('🌸 Дарибри App initializing...');
    
    // Category filter
    document.getElementById('categories').addEventListener('click', (e) => {
        const chip = e.target.closest('.category-chip');
        if (!chip) return;
        document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        loadProducts();
    });
    
    // Load initial data
    await loadCategories();
    await loadProducts();
    await initFavorites();
    await initCart();
    
    console.log('✅ App initialized');
}

// Start when DOM ready
document.addEventListener('DOMContentLoaded', init);


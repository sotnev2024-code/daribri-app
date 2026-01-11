/**
 * Product Module - страница товара
 */

(function() {
    'use strict';
    
    const getState = () => window.App?.state;
    const getElements = () => window.App?.elements;
    const getUtils = () => window.App?.utils || {};
    const getApi = () => window.api;
    
    // Состояние галереи
    let currentGallerySlide = 0;
    let gallerySlides = [];
    
    // Открытие страницы товара
    async function openProductPage(productId) {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        const api = getApi();
        if (!state || !elements || !api) return;
        
        try {
            const product = await api.getProduct(productId);
            state.currentProduct = product;
            
            const getMediaUrl = utils.getMediaUrl || window.getMediaUrl || ((url) => url);
            const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
            
            // Заполняем галерею медиа
            const media = product.media || [];
            if (media.length > 0) {
                let galleryHTML = '<div class="product-gallery-slider">';
                galleryHTML += '<div class="gallery-slides-container">';
                media.forEach((item, index) => {
                    const mediaUrl = getMediaUrl(item.url);
                    if (item.media_type === 'video') {
                        galleryHTML += `
                            <div class="gallery-slide" data-index="${index}">
                                <video src="${mediaUrl}" controls></video>
                            </div>
                        `;
                    } else {
                        galleryHTML += `
                            <div class="gallery-slide" data-index="${index}">
                                <img src="${mediaUrl}" alt="${product.name}">
                            </div>
                        `;
                    }
                });
                galleryHTML += '</div>';
                galleryHTML += '</div>';
                
                if (media.length > 1) {
                    galleryHTML += `
                        <div class="gallery-nav">
                            <button class="gallery-nav-btn prev" id="galleryPrev">‹</button>
                            <div class="gallery-dots">
                                ${media.map((_, i) => `<span class="gallery-dot ${i === 0 ? 'active' : ''}" data-index="${i}"></span>`).join('')}
                            </div>
                            <button class="gallery-nav-btn next" id="galleryNext">›</button>
                        </div>
                    `;
                }
                
                elements.productGallery.innerHTML = galleryHTML;
                
                if (media.length > 1) {
                    initGalleryNavigation(media.length);
                } else {
                    const slide = elements.productGallery.querySelector('.gallery-slide');
                    if (slide) slide.classList.add('active');
                }
            } else {
                elements.productGallery.innerHTML = '<div class="product-gallery-placeholder">🌸</div>';
            }
            
            // Основная информация о товаре
            elements.productName.textContent = product.name;
            elements.productDescription.textContent = product.description || 'Описание отсутствует';
            
            // Цена - используем такую же логику, как в каталоге
            const price = parseFloat(product.price) || 0;
            let discountPrice = null;
            if (product.discount_price !== null && product.discount_price !== undefined && product.discount_price !== '') {
                const parsed = parseFloat(product.discount_price);
                if (!isNaN(parsed) && parsed > 0) {
                    discountPrice = parsed;
                }
            }
            const hasDiscount = discountPrice !== null && discountPrice < price;
            elements.productPrice.textContent = formatPrice(hasDiscount ? discountPrice : price);
            elements.productOldPrice.textContent = hasDiscount ? formatPrice(price) : '';
            elements.productOldPrice.hidden = !hasDiscount;
            elements.productDiscount.textContent = hasDiscount 
                ? `-${Math.round((1 - discountPrice / price) * 100)}%` 
                : '';
            elements.productDiscount.hidden = !hasDiscount;
            
            // Количество в наличии
            const stockElement = document.getElementById('productStockValue');
            if (stockElement) {
                if (product.quantity > 10) {
                    stockElement.textContent = '✓ В наличии';
                    stockElement.className = 'stock-value in-stock';
                } else if (product.quantity > 0) {
                    stockElement.textContent = `⚠ Осталось ${product.quantity} шт`;
                    stockElement.className = 'stock-value low-stock';
                } else {
                    stockElement.textContent = '✕ Нет в наличии';
                    stockElement.className = 'stock-value out-of-stock';
                }
            }
            
            // Информация о продавце
            const sellerSection = document.querySelector('.product-seller-section');
            const sellerCard = document.getElementById('productSellerCard');
            const sellerAvatar = document.getElementById('sellerAvatar');
            const sellerName = document.getElementById('sellerName');
            const sellerRating = document.getElementById('sellerRating');
            
            if (sellerCard && sellerName && sellerRating) {
                sellerName.textContent = product.shop_name || 'Магазин';
                
                if (sellerAvatar) {
                    if (product.shop_photo) {
                        const photoUrl = getMediaUrl(product.shop_photo);
                        sellerAvatar.innerHTML = `<img src="${photoUrl}" alt="${product.shop_name}">`;
                    } else {
                        sellerAvatar.textContent = '🏪';
                    }
                }
                
                const rating = product.shop_rating || 0;
                const reviewsCount = product.shop_reviews_count || 0;
                sellerRating.innerHTML = `
                    <span class="rating-stars">${'⭐'.repeat(Math.round(rating))}</span>
                    <span class="rating-value">${rating.toFixed(1)}</span>
                    ${reviewsCount > 0 ? `<span class="rating-count">(${reviewsCount} ${reviewsCount === 1 ? 'отзыв' : reviewsCount < 5 ? 'отзыва' : 'отзывов'})</span>` : ''}
                `;
                
                // Клик на всю секцию магазина
                const clickTarget = sellerSection || sellerCard;
                if (clickTarget && product.shop_id) {
                    clickTarget.style.cursor = 'pointer';
                    clickTarget.onclick = (e) => {
                        e.stopPropagation();
                        if (window.openShopPage) window.openShopPage(product.shop_id);
                    };
                }
            }
            
            // Загружаем товары продавца
            await loadSellerProducts(product.shop_id, product.id);
            
            // Избранное
            const favoritesModule = window.App?.favorites;
            if (favoritesModule?.isProductFavorite && elements.productFavoriteBtn) {
                const isFavorite = favoritesModule.isProductFavorite(product.id);
                elements.productFavoriteBtn.classList.toggle('active', isFavorite);
            }
            
            // Обновляем заголовок страницы
            if (elements.productPageTitle) {
                elements.productPageTitle.textContent = product.name.length > 30 
                    ? product.name.substring(0, 30) + '...' 
                    : product.name;
            }
            
            // Показываем страницу товара
            if (window.navigateTo) window.navigateTo('product');
            
            // Обновляем UI кнопок корзины
            if (window.updateProductPageCartUI) {
                window.updateProductPageCartUI(product.id);
            }
        } catch (error) {
            console.error('Error loading product:', error);
            const utils = getUtils();
            if (utils.showToast) utils.showToast('Не удалось загрузить товар', 'error');
        }
    }
    
    // Инициализация навигации по галерее
    function initGalleryNavigation(mediaCount) {
        gallerySlides = Array.from(document.querySelectorAll('.gallery-slide'));
        const container = document.querySelector('.gallery-slides-container');
        currentGallerySlide = 0;
        
        if (!container || gallerySlides.length === 0) return;
        
        goToGallerySlide(0);
        
        const prevBtn = document.getElementById('galleryPrev');
        const nextBtn = document.getElementById('galleryNext');
        const dots = document.querySelectorAll('.gallery-dot');
        const gallery = document.querySelector('.product-gallery-slider');
        
        if (prevBtn) {
            prevBtn.onclick = () => changeGallerySlide(-1);
        }
        
        if (nextBtn) {
            nextBtn.onclick = () => changeGallerySlide(1);
        }
        
        dots.forEach((dot, index) => {
            dot.onclick = () => goToGallerySlide(index);
        });
        
        // Инициализируем свайп даже если одно медиа (для видео)
        if (gallery && gallerySlides.length >= 1) {
            let startX = 0;
            let currentX = 0;
            let isDragging = false;
            
            const newGallery = gallery.cloneNode(true);
            gallery.parentNode.replaceChild(newGallery, gallery);
            
            const newContainer = newGallery.querySelector('.gallery-slides-container');
            const newSlides = newGallery.querySelectorAll('.gallery-slide');
            
            newGallery.addEventListener('touchstart', (e) => {
                isDragging = true;
                startX = e.touches[0].clientX;
                newContainer.style.transition = 'none';
            }, { passive: true });
            
            newGallery.addEventListener('touchmove', (e) => {
                if (!isDragging) return;
                e.preventDefault();
                currentX = e.touches[0].clientX - startX;
                const offset = -currentGallerySlide * 100 + (currentX / newGallery.offsetWidth) * 100;
                newContainer.style.transform = `translateX(${offset}%)`;
            }, { passive: false });
            
            newGallery.addEventListener('touchend', () => {
                if (!isDragging) return;
                isDragging = false;
                newContainer.style.transition = '';
                
                const threshold = newGallery.offsetWidth * 0.2;
                if (Math.abs(currentX) > threshold) {
                    if (currentX > 0) {
                        changeGallerySlide(-1);
                    } else {
                        changeGallerySlide(1);
                    }
                } else {
                    goToGallerySlide(currentGallerySlide);
                }
                
                currentX = 0;
            }, { passive: true });
            
            let mouseStartX = 0;
            let mouseCurrentX = 0;
            let isMouseDragging = false;
            
            newGallery.addEventListener('mousedown', (e) => {
                isMouseDragging = true;
                mouseStartX = e.clientX;
                newContainer.style.transition = 'none';
                e.preventDefault();
            });
            
            newGallery.addEventListener('mousemove', (e) => {
                if (!isMouseDragging) return;
                mouseCurrentX = e.clientX - mouseStartX;
                const offset = -currentGallerySlide * 100 + (mouseCurrentX / newGallery.offsetWidth) * 100;
                newContainer.style.transform = `translateX(${offset}%)`;
            });
            
            newGallery.addEventListener('mouseup', () => {
                if (!isMouseDragging) return;
                isMouseDragging = false;
                newContainer.style.transition = '';
                
                const threshold = newGallery.offsetWidth * 0.2;
                if (Math.abs(mouseCurrentX) > threshold) {
                    if (mouseCurrentX > 0) {
                        changeGallerySlide(-1);
                    } else {
                        changeGallerySlide(1);
                    }
                } else {
                    goToGallerySlide(currentGallerySlide);
                }
                
                mouseCurrentX = 0;
            });
            
            newGallery.addEventListener('mouseleave', () => {
                if (isMouseDragging) {
                    isMouseDragging = false;
                    newContainer.style.transition = '';
                    goToGallerySlide(currentGallerySlide);
                }
            });
            
            gallerySlides = Array.from(newSlides);
        }
    }
    
    // Изменение слайда галереи
    function changeGallerySlide(direction) {
        currentGallerySlide += direction;
        if (currentGallerySlide < 0) currentGallerySlide = gallerySlides.length - 1;
        if (currentGallerySlide >= gallerySlides.length) currentGallerySlide = 0;
        goToGallerySlide(currentGallerySlide);
    }
    
    // Переход к слайду галереи
    function goToGallerySlide(index) {
        currentGallerySlide = index;
        if (currentGallerySlide < 0) currentGallerySlide = gallerySlides.length - 1;
        if (currentGallerySlide >= gallerySlides.length) currentGallerySlide = 0;
        
        const container = document.querySelector('.gallery-slides-container');
        if (container) {
            container.style.transform = `translateX(-${currentGallerySlide * 100}%)`;
        }
        
        gallerySlides.forEach((slide, i) => {
            slide.classList.toggle('active', i === currentGallerySlide);
        });
        document.querySelectorAll('.gallery-dot').forEach((dot, i) => {
            dot.classList.toggle('active', i === currentGallerySlide);
        });
    }
    
    // Загрузка товаров продавца
    async function loadSellerProducts(shopId, currentProductId) {
        const api = getApi();
        const utils = getUtils();
        if (!shopId || !api) return;
        
        try {
            const products = await api.getShopProducts(shopId, { limit: 8 });
            const sellerProductsSection = document.getElementById('sellerProductsSection');
            const sellerProductsGrid = document.getElementById('sellerProductsGrid');
            
            if (!sellerProductsSection || !sellerProductsGrid) return;
            
            const otherProducts = products.filter(p => p.id !== currentProductId);
            
            if (otherProducts.length === 0) {
                sellerProductsSection.hidden = true;
                return;
            }
            
            sellerProductsSection.hidden = false;
            sellerProductsGrid.innerHTML = '';
            
            const formatPrice = utils.formatPrice || window.formatPrice || ((p) => p);
            
            otherProducts.forEach(product => {
                const card = document.createElement('div');
                card.className = 'seller-product-card';
                card.onclick = () => {
                    if (window.openProductPage) window.openProductPage(product.id);
                };
                
                const hasDiscount = product.discount_price !== null && product.discount_price < product.price;
                const primaryImage = product.primary_image || product.media?.[0]?.url || '';
                
                card.innerHTML = `
                    <div class="seller-product-image">
                        ${primaryImage 
                            ? `<img src="${primaryImage}" alt="${product.name}" loading="lazy">`
                            : '<div class="product-image-placeholder">🌸</div>'
                        }
                    </div>
                    <div class="seller-product-info">
                        <div class="seller-product-name">${product.name}</div>
                        <div class="seller-product-price">
                            <span class="seller-product-current-price">${formatPrice(hasDiscount ? product.discount_price : product.price)}</span>
                            ${hasDiscount ? `<span class="seller-product-old-price">${formatPrice(product.price)}</span>` : ''}
                        </div>
                    </div>
                `;
                
                sellerProductsGrid.appendChild(card);
            });
        } catch (error) {
            console.error('Error loading seller products:', error);
            const sellerProductsSection = document.getElementById('sellerProductsSection');
            if (sellerProductsSection) {
                sellerProductsSection.hidden = true;
            }
        }
    }
    
    // Закрытие страницы товара
    function closeProductPage() {
        if (window.navigateTo) window.navigateTo('catalog');
    }
    
    // Обновление количества товара
    function updateQuantity(delta) {
        const elements = getElements();
        if (!elements?.qtyValue) return;
        
        const current = parseInt(elements.qtyValue.textContent) || 1;
        const newQty = Math.max(1, current + delta);
        elements.qtyValue.textContent = newQty;
    }
    
    // Добавление товара в корзину
    async function addToCart() {
        const state = getState();
        const elements = getElements();
        const utils = getUtils();
        const api = getApi();
        if (!state || !elements || !api) return;
        
        if (!state.currentProduct) return;
        
        const currentProduct = state.currentProduct;
        const quantity = 1; // Всегда добавляем 1 шт
        
        // Проверяем наличие товара
        if (currentProduct.quantity !== undefined && currentProduct.quantity < 1) {
            if (utils.showToast) utils.showToast('Товар закончился', 'error');
            return;
        }
        
        // Проверяем, не превышает ли уже количество в корзине наличие
        const existingCartItem = state.cart.find(item => item.product_id === currentProduct.id);
        if (existingCartItem && currentProduct.quantity && existingCartItem.quantity >= currentProduct.quantity) {
            if (utils.showToast) {
                utils.showToast(`В корзине уже максимальное количество (${currentProduct.quantity} шт.)`, 'warning');
            }
            return;
        }
        
        // Проверяем, есть ли в корзине товары из другого магазина
        if (state.cart && state.cart.length > 0) {
            const cartShopId = state.cart[0].shop_id;
            const newProductShopId = currentProduct.shop_id;
            
            if (cartShopId && newProductShopId && cartShopId !== newProductShopId) {
                // Показываем предупреждение
                const confirmed = await showDifferentShopWarning(currentProduct, quantity);
                if (!confirmed) return;
            }
        }
        
        try {
            await api.addToCart(currentProduct.id, quantity);
            if (utils.showToast) utils.showToast('Товар добавлен в корзину', 'success');
            
            // Перезагружаем корзину
            const cartModule = window.App?.cart;
            if (cartModule?.loadCart) {
                await cartModule.loadCart();
            }
            
            // Обновляем UI - показываем кнопки +/- и "Перейти в корзину"
            if (window.updateProductPageCartUI) {
                window.updateProductPageCartUI(currentProduct.id);
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            if (utils.showToast) utils.showToast('Ошибка добавления в корзину', 'error');
        }
    }
    
    // Показывает предупреждение о товарах из разных магазинов
    async function showDifferentShopWarning(newProduct, quantity) {
        const state = getState();
        const api = getApi();
        const utils = getUtils();
        
        return new Promise((resolve) => {
            // Создаём модальное окно
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.id = 'differentShopModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;';
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 400px; background: var(--bg-secondary, #fff); border-radius: 16px; margin: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
                    <div class="modal-header" style="padding: 20px 20px 10px; text-align: center;">
                        <h2 style="margin: 0; font-size: 18px;">⚠️ Разные магазины</h2>
                    </div>
                    <div class="modal-body" style="padding: 10px 20px 20px; text-align: center;">
                        <p style="margin-bottom: 15px;">В корзине уже есть товары из другого магазина.</p>
                        <p style="color: var(--text-secondary); font-size: 14px; margin: 0;">Вы можете оформить заказ только из одного магазина за раз.</p>
                    </div>
                    <div class="modal-footer" style="display: flex; gap: 10px; padding: 15px 20px 20px;">
                        <button class="btn btn-secondary" id="cancelDifferentShop" style="flex: 1; padding: 12px; border-radius: 12px; border: none; background: var(--bg-tertiary, #f0f0f0); cursor: pointer;">Отмена</button>
                        <button class="btn btn-primary" id="clearCartAndAdd" style="flex: 1; padding: 12px; border-radius: 12px; border: none; background: var(--primary, #007AFF); color: white; cursor: pointer;">Очистить корзину</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Обработчики кнопок
            document.getElementById('cancelDifferentShop').onclick = () => {
                modal.remove();
                resolve(false);
            };
            
            document.getElementById('clearCartAndAdd').onclick = async () => {
                try {
                    // Очищаем корзину
                    await api.clearCart();
                    state.cart = [];
                    
                    // Добавляем новый товар
                    await api.addToCart(newProduct.id, quantity);
                    if (utils.showToast) utils.showToast('Корзина очищена, товар добавлен', 'success');
                    
                    // Перезагружаем корзину
                    const cartModule = window.App?.cart;
                    if (cartModule?.loadCart) {
                        await cartModule.loadCart();
                    }
                    
                    modal.remove();
                    resolve(false); // false, потому что уже добавили товар
                } catch (error) {
                    console.error('Error clearing cart:', error);
                    if (utils.showToast) utils.showToast('Ошибка очистки корзины', 'error');
                    modal.remove();
                    resolve(false);
                }
            };
            
            // Закрытие по клику на фон
            modal.onclick = (e) => {
                if (e.target === modal) {
                    modal.remove();
                    resolve(false);
                }
            };
        });
    }
    
    // Экспортируем функции
    window.App = window.App || {};
    window.App.product = {
        openProductPage,
        closeProductPage,
        loadSellerProducts,
        initGalleryNavigation,
        changeGallerySlide,
        goToGallerySlide,
        updateQuantity,
        addToCart
    };
    
    // Экспортируем как глобальные функции для обратной совместимости
    window.openProductPage = openProductPage;
    window.closeProductPage = closeProductPage;
    window.loadSellerProducts = loadSellerProducts;
    window.initGalleryNavigation = initGalleryNavigation;
    window.changeGallerySlide = changeGallerySlide;
    window.goToGallerySlide = goToGallerySlide;
    window.updateQuantity = updateQuantity;
    window.addToCart = addToCart;
})();

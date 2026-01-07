/**
 * Profile Module - профиль пользователя
 */

import { apiRequest } from './api.js';

export async function loadProfile() {
    try {
        const user = await apiRequest('/users/me');
        document.getElementById('profileName').textContent = user.first_name || 'Пользователь';
        document.getElementById('profileId').textContent = 'ID: ' + user.telegram_id;
    } catch (e) { 
        console.error('Load profile error:', e); 
    }
}

export function openMyShop() { 
    alert('Управление магазином - в разработке'); 
}

export function openAddProduct() { 
    alert('Добавление товара - в разработке'); 
}

export function openSubscription() { 
    alert('Подписка - в разработке'); 
}

// Expose to window
window.openMyShop = openMyShop;
window.openAddProduct = openAddProduct;
window.openSubscription = openSubscription;




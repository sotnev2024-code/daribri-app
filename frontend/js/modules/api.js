/**
 * API Module - работа с сервером
 */

const API_URL = 'http://localhost:8080/api';

export async function apiRequest(endpoint, options = {}) {
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

export function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU').format(price) + ' ₽';
}




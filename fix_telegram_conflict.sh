#!/bin/bash
# Скрипт для исправления конфликта Telegram бота

echo "=== Исправление конфликта Telegram бота ==="
echo ""

# Получаем токен бота из .env
BOT_TOKEN=$(grep BOT_TOKEN /var/www/daribri/.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не найден в .env файле"
    exit 1
fi

echo "1. Проверка webhook бота..."
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
echo "$WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_INFO"
echo ""

# Проверяем, есть ли активный webhook
HAS_WEBHOOK=$(echo "$WEBHOOK_INFO" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)

if [ ! -z "$HAS_WEBHOOK" ] && [ "$HAS_WEBHOOK" != "null" ]; then
    echo "⚠️  Найден активный webhook: $HAS_WEBHOOK"
    echo "2. Удаление webhook..."
    DELETE_RESULT=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
    echo "$DELETE_RESULT" | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESULT"
    echo ""
    
    echo "3. Проверка после удаления..."
    sleep 2
    NEW_WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
    echo "$NEW_WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$NEW_WEBHOOK_INFO"
    echo ""
else
    echo "✅ Webhook не найден или не активен"
    echo ""
fi

echo "4. Остановка сервиса..."
sudo systemctl stop daribri
sleep 2

echo "5. Проверка процессов..."
ps aux | grep -i "run_api.py\|daribri" | grep -v grep
if [ $? -eq 0 ]; then
    echo "   ⚠️  Найдены процессы, принудительно завершаем..."
    sudo pkill -9 -f "run_api.py"
    sudo pkill -9 -f "daribri"
    sleep 1
fi

echo "6. Запуск сервиса..."
sudo systemctl start daribri
sleep 3

echo "7. Проверка статуса..."
sudo systemctl status daribri --no-pager -l | head -15
echo ""

echo "8. Последние логи (10 строк)..."
sudo journalctl -u daribri -n 10 --no-pager
echo ""

echo "=== Готово! ==="
echo "Проверьте логи через несколько секунд:"
echo "  sudo journalctl -u daribri -f"


#!/bin/bash
# Скрипт для детальной проверки конфликта бота

echo "=== Детальная проверка конфликта Telegram бота ==="
echo ""

# Получаем токен бота
BOT_TOKEN=$(grep BOT_TOKEN /var/www/daribri/.env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не найден в .env файле"
    exit 1
fi

echo "1. Проверка webhook через Telegram API..."
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
echo "$WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_INFO"
echo ""

# Проверяем URL webhook
WEBHOOK_URL=$(echo "$WEBHOOK_INFO" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)

if [ ! -z "$WEBHOOK_URL" ] && [ "$WEBHOOK_URL" != "null" ] && [ "$WEBHOOK_URL" != "" ]; then
    echo "⚠️  ВНИМАНИЕ: Найден активный webhook: $WEBHOOK_URL"
    echo ""
    echo "2. Удаление webhook..."
    DELETE_RESULT=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
    echo "$DELETE_RESULT" | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESULT"
    echo ""
    
    echo "3. Повторная проверка webhook..."
    sleep 2
    NEW_WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
    echo "$NEW_WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$NEW_WEBHOOK_INFO"
    echo ""
else
    echo "✅ Webhook не найден или не активен"
    echo ""
fi

echo "4. Проверка процессов на сервере..."
ps aux | grep -i "run_api.py\|daribri\|python.*bot" | grep -v grep
echo ""

echo "5. Проверка процессов по портам..."
sudo lsof -i :8000 2>/dev/null || sudo netstat -tulpn | grep :8000
echo ""

echo "=== Важно ==="
echo "Если webhook был удален, но конфликт продолжается, возможно:"
echo "1. Бот запущен локально на вашем компьютере"
echo "2. Бот запущен на другом сервере"
echo "3. Есть другой процесс, использующий тот же токен"
echo ""
echo "Проверьте:"
echo "- Не запущен ли бот локально (на вашем компьютере)?"
echo "- Не запущен ли бот на другом сервере?"
echo "- Нет ли других скриптов, использующих этот токен?"


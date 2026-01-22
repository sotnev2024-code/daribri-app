#!/bin/bash
# Скрипт для полной проверки сервиса

echo "=== Проверка сервиса daribri ==="
echo ""

# 1. Статус systemd
echo "1. Статус systemd сервиса:"
sudo systemctl status daribri --no-pager -l | head -15
echo ""

# 2. Процессы
echo "2. Запущенные процессы:"
ps aux | grep -i "run_api.py\|daribri" | grep -v grep
echo ""

# 3. Порт 8000
echo "3. Процессы на порту 8000:"
sudo lsof -i :8000 2>/dev/null || sudo netstat -tulpn | grep :8000 || echo "   Порт не используется или команды недоступны"
echo ""

# 4. Последние логи
echo "4. Последние 20 строк логов:"
sudo journalctl -u daribri -n 20 --no-pager
echo ""

# 5. Проверка API
echo "5. Проверка доступности API:"
curl -s http://localhost:8000/api/health 2>/dev/null && echo "" || echo "   API не отвечает"
echo ""

# 6. Проверка ошибок в логах
echo "6. Ошибки в логах (последние 10):"
sudo journalctl -u daribri --since "5 minutes ago" | grep -i error | tail -10 || echo "   Ошибок не найдено"
echo ""

echo "=== Проверка завершена ==="


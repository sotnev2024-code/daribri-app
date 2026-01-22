#!/bin/bash
# Скрипт для проверки запущенных процессов проекта

echo "=== Проверка запущенных процессов проекта ==="
echo ""

# 1. Проверка процессов Python, связанных с проектом
echo "1. Процессы Python, связанные с daribri/run_api.py:"
ps aux | grep -i "run_api.py\|daribri" | grep -v grep
echo ""

# 2. Проверка процессов по имени файла
echo "2. Процессы по PID файлам (если есть):"
if [ -f "/var/run/daribri.pid" ]; then
    PID=$(cat /var/run/daribri.pid)
    echo "   PID из файла: $PID"
    ps -p $PID 2>/dev/null || echo "   Процесс с PID $PID не найден"
else
    echo "   PID файл не найден"
fi
echo ""

# 3. Проверка systemd сервиса
echo "3. Статус systemd сервиса:"
systemctl status daribri --no-pager -l | head -20
echo ""

# 4. Проверка активных процессов по порту
echo "4. Процессы, использующие порт 8000:"
lsof -i :8000 2>/dev/null || netstat -tulpn | grep :8000 || ss -tulpn | grep :8000
echo ""

# 5. Проверка всех процессов Python
echo "5. Все процессы Python:"
ps aux | grep python | grep -v grep
echo ""

# 6. Проверка процессов по рабочей директории
echo "6. Процессы в рабочей директории /var/www/daribri:"
lsof +D /var/www/daribri 2>/dev/null | head -20 || echo "   lsof не доступен или директория не найдена"
echo ""

# 7. Проверка процессов по пользователю www-data
echo "7. Процессы пользователя www-data:"
ps aux | grep www-data | grep -v grep
echo ""

echo "=== Для остановки всех процессов выполните: ==="
echo "sudo systemctl stop daribri"
echo "sudo pkill -f 'run_api.py'"
echo "sudo pkill -f 'daribri'"


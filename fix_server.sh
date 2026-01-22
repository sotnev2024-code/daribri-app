#!/bin/bash
# Скрипт для исправления проблем с сервером

echo "=== Исправление проблем с сервером ==="
echo ""

# 1. Остановить systemd сервис
echo "1. Останавливаем systemd сервис..."
sudo systemctl stop daribri

# 2. Убить все процессы Python, связанные с ботом
echo "2. Останавливаем все процессы Python..."
sudo pkill -f "run_api.py" || true
sudo pkill -f "daribri" || true
sleep 2

# 3. Проверить, что процессы остановлены
echo "3. Проверяем, что процессы остановлены..."
if pgrep -f "run_api.py" > /dev/null; then
    echo "   ВНИМАНИЕ: Процессы все еще запущены, принудительно завершаем..."
    sudo pkill -9 -f "run_api.py" || true
    sleep 1
fi

# 4. Установить зависимости
echo "4. Устанавливаем зависимости..."
cd /var/www/daribri
/var/www/daribri/venv/bin/pip install -r requirements.txt --quiet

# 5. Обновить код из GitHub (если нужно)
echo "5. Обновляем код из GitHub..."
git pull origin main

# 6. Установить права
echo "6. Устанавливаем права доступа..."
sudo chown -R www-data:www-data /var/www/daribri
sudo chmod +x /var/www/daribri/run_api.py

# 7. Перезагрузить systemd
echo "7. Перезагружаем systemd..."
sudo systemctl daemon-reload

# 8. Запустить сервис
echo "8. Запускаем сервис..."
sudo systemctl start daribri

# 9. Подождать немного
sleep 3

# 10. Проверить статус
echo ""
echo "=== Статус сервиса ==="
sudo systemctl status daribri --no-pager -l

echo ""
echo "=== Последние логи (20 строк) ==="
sudo journalctl -u daribri -n 20 --no-pager

echo ""
echo "=== Готово! ==="
echo "Для просмотра логов в реальном времени выполните:"
echo "  sudo journalctl -u daribri -f"


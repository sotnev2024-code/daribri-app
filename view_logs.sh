#!/bin/bash
# Скрипт для просмотра логов сервера

echo "Выберите способ просмотра логов:"
echo "1. Systemd journal (если сервер запущен через systemd)"
echo "2. Gunicorn logs (если используется gunicorn)"
echo "3. Поиск по ключевому слову 'ORDER'"
echo ""
read -p "Введите номер (1-3): " choice

case $choice in
    1)
        echo "Просмотр логов через journalctl..."
        echo "Нажмите Ctrl+C для выхода"
        sudo journalctl -u daribri -f
        ;;
    2)
        echo "Просмотр логов Gunicorn..."
        if [ -f "logs/error.log" ]; then
            tail -f logs/error.log
        elif [ -f "/var/www/daribri/logs/error.log" ]; then
            tail -f /var/www/daribri/logs/error.log
        else
            echo "Файл логов не найден. Проверьте путь к логам."
        fi
        ;;
    3)
        echo "Поиск логов с 'ORDER'..."
        if command -v journalctl &> /dev/null; then
            sudo journalctl -u daribri | grep -i "ORDER" | tail -50
        else
            echo "journalctl не найден. Попробуйте другой способ."
        fi
        ;;
    *)
        echo "Неверный выбор"
        ;;
esac


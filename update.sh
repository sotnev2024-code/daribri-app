#!/bin/bash
# Скрипт для обновления приложения на сервере

set -e

APP_DIR="/var/www/daribri"
SERVICE_NAME="daribri"

echo "=========================================="
echo "  Обновление Telegram Mini App"
echo "=========================================="
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    error "Пожалуйста, запустите скрипт от root (sudo ./update.sh)"
    exit 1
fi

cd $APP_DIR

# 1. Остановка сервиса
info "Остановка сервиса..."
systemctl stop $SERVICE_NAME

# 2. Создание бэкапа базы данных
info "Создание бэкапа базы данных..."
if [ -f "database/miniapp.db" ]; then
    BACKUP_DIR="/var/backups/daribri"
    mkdir -p $BACKUP_DIR
    DATE=$(date +%Y%m%d_%H%M%S)
    cp database/miniapp.db $BACKUP_DIR/miniapp_$DATE.db
    info "Бэкап создан: $BACKUP_DIR/miniapp_$DATE.db"
fi

# 3. Обновление кода (если используется Git)
if [ -d ".git" ]; then
    info "Обновление кода из Git..."
    git pull
else
    warn "Репозиторий Git не найден. Обновите код вручную."
fi

# 4. Обновление зависимостей
info "Обновление зависимостей..."
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --upgrade
fi

# 5. Применение миграций (если есть)
if [ -f "database/init_db.py" ]; then
    info "Проверка миграций..."
    python database/init_db.py
fi

# 6. Настройка прав
info "Настройка прав доступа..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
if [ -f ".env" ]; then
    chmod 600 .env
fi

# 7. Перезапуск сервиса
info "Запуск сервиса..."
systemctl start $SERVICE_NAME
sleep 2

# 8. Проверка статуса
if systemctl is-active --quiet $SERVICE_NAME; then
    info "Сервис успешно запущен!"
    systemctl status $SERVICE_NAME --no-pager -l
else
    error "Ошибка при запуске сервиса!"
    journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi

info "Обновление завершено!"



#!/bin/bash
# Скрипт для исправления проблем с сайтом

set -e

APP_DIR="/var/www/daribri"
SERVICE_NAME="daribri"
DOMAIN="flow.plus-shop.ru"

echo "=========================================="
echo "  Исправление проблем с сайтом"
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
    error "Пожалуйста, запустите скрипт от root (sudo ./fix_website.sh)"
    exit 1
fi

cd $APP_DIR

# 1. Проверка API локально
info "Проверка API локально..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    info "API работает на порту 8000"
else
    error "API не отвечает на порту 8000"
    info "Проверка статуса сервиса..."
    systemctl status $SERVICE_NAME --no-pager -l || true
    info "Попытка перезапуска сервиса..."
    systemctl restart $SERVICE_NAME
    sleep 3
    if curl -s http://localhost:8000/api/health > /dev/null; then
        info "API теперь работает"
    else
        error "API все еще не работает. Проверьте логи: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
fi

# 2. Проверка и обновление конфигурации Nginx
info "Проверка конфигурации Nginx..."

# Создаем правильную конфигурацию
cat > /etc/nginx/sites-available/daribri << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    access_log /var/log/nginx/daribri_access.log;
    error_log /var/log/nginx/daribri_error.log;
}
EOF

info "Конфигурация Nginx обновлена"

# 3. Активация конфигурации
info "Активация конфигурации Nginx..."
ln -sf /etc/nginx/sites-available/daribri /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 4. Проверка синтаксиса
info "Проверка синтаксиса Nginx..."
if nginx -t; then
    info "Синтаксис Nginx корректен"
else
    error "Ошибка в конфигурации Nginx"
    exit 1
fi

# 5. Перезагрузка Nginx
info "Перезагрузка Nginx..."
systemctl reload nginx

# 6. Проверка статуса Nginx
info "Проверка статуса Nginx..."
if systemctl is-active --quiet nginx; then
    info "Nginx работает"
else
    error "Nginx не работает"
    systemctl status nginx --no-pager -l
    exit 1
fi

# 7. Проверка портов
info "Проверка портов..."
if ss -tulpn | grep -q ':80 '; then
    info "Порт 80 слушается"
else
    warn "Порт 80 не слушается"
fi

if ss -tulpn | grep -q ':8000 '; then
    info "Порт 8000 слушается"
else
    error "Порт 8000 не слушается"
    exit 1
fi

# 8. Проверка через curl
info "Проверка через curl..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    info "Сайт отвечает через Nginx"
else
    warn "Сайт не отвечает через Nginx (проверьте логи)"
fi

# 9. Проверка DNS (если доступно)
info "Проверка DNS..."
if command -v nslookup &> /dev/null; then
    if nslookup $DOMAIN | grep -q "Address:"; then
        info "DNS настроен для $DOMAIN"
    else
        warn "DNS может быть не настроен для $DOMAIN"
    fi
fi

echo ""
info "=========================================="
info "  Проверка завершена"
info "=========================================="
echo ""
info "Проверьте сайт:"
info "  - http://$DOMAIN"
info "  - http://$DOMAIN/api/health"
echo ""
info "Если сайт не открывается, проверьте:"
info "  1. Логи Nginx: tail -f /var/log/nginx/error.log"
info "  2. Логи приложения: journalctl -u $SERVICE_NAME -f"
info "  3. Статус сервиса: systemctl status $SERVICE_NAME"
echo ""


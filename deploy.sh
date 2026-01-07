#!/bin/bash
# Скрипт для деплоя на сервер (Git Bash / Linux / Mac)
# Использование: ./deploy.sh

set -e

# Настройки (замените на ваши)
SERVER="root@your-server-ip"  # Замените на ваш IP
APP_DIR="/var/www/daribri"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Начинаем деплой на сервер...${NC}"
echo ""

# Проверка, что мы в Git репозитории
if [ ! -d .git ]; then
    echo -e "${RED}❌ Ошибка: Это не Git репозиторий!${NC}"
    echo -e "${YELLOW}Инициализируйте Git: git init${NC}"
    exit 1
fi

# Проверка изменений
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}📝 Обнаружены изменения:${NC}"
    git status --short
    echo ""
    
    read -p "Хотите закоммитить изменения? (y/n): " commit
    if [ "$commit" = "y" ] || [ "$commit" = "Y" ]; then
        read -p "Введите сообщение коммита: " message
        if [ -z "$message" ]; then
            message="Update: $(date '+%Y-%m-%d %H:%M:%S')"
        fi
        
        echo -e "${YELLOW}📦 Коммитим изменения...${NC}"
        git add .
        git commit -m "$message"
        
        echo -e "${YELLOW}⬆️ Отправляем на GitHub...${NC}"
        git push origin main || {
            echo -e "${YELLOW}⚠️ Предупреждение: Не удалось отправить на GitHub${NC}"
            echo -e "${YELLOW}Продолжаем деплой на сервер...${NC}"
        }
    fi
else
    echo -e "${GREEN}✅ Нет локальных изменений${NC}"
fi

echo ""
echo -e "${YELLOW}🔄 Обновляем сервер...${NC}"

# Выполняем команды на сервере
ssh $SERVER << EOF
set -e
cd $APP_DIR

echo "Остановка сервиса..."
systemctl stop daribri

echo "Обновление кода из GitHub..."
git pull origin main

echo "Обновление зависимостей..."
source venv/bin/activate
pip install -r requirements.txt --upgrade --quiet

echo "Установка прав..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR

echo "Запуск сервиса..."
systemctl start daribri
sleep 2

echo ""
echo "Проверка статуса:"
systemctl status daribri --no-pager -l
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Деплой завершен успешно!${NC}"
else
    echo ""
    echo -e "${RED}❌ Ошибка при деплое!${NC}"
    echo -e "${YELLOW}Проверьте логи на сервере: ssh $SERVER 'journalctl -u daribri -n 50'${NC}"
    exit 1
fi

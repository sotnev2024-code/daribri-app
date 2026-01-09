# Инструкция по обновлению кода на сервере

## Быстрый способ (рекомендуется)

### Вариант 1: Через rsync (с локального компьютера)

Это самый удобный способ для регулярных обновлений.

```bash
# На вашем локальном компьютере (Windows PowerShell или Git Bash)
# Замените your-server-ip на IP вашего сервера

rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.git' --exclude 'database/miniapp.db' \
  --exclude '*.log' ./ root@your-server-ip:/var/www/daribri/
```

**Что делает команда:**
- `-a` - архивный режим (сохраняет права доступа, даты)
- `-v` - подробный вывод
- `-z` - сжатие при передаче
- `--exclude` - исключает ненужные файлы

**После загрузки файлов на сервере:**

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Перейдите в директорию проекта
cd /var/www/daribri

# Остановите сервис
systemctl stop daribri

# Установите права
chown -R www-data:www-data /var/www/daribri
chmod -R 755 /var/www/daribri

# Перезапустите сервис
systemctl start daribri

# Проверьте статус
systemctl status daribri
```

### Вариант 2: Через SCP (с локального компьютера)

```bash
# На вашем локальном компьютере
# Замените your-server-ip на IP вашего сервера

scp -r --exclude='.venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.git' \
  ./ root@your-server-ip:/var/www/daribri/
```

**Примечание:** SCP не поддерживает `--exclude` напрямую. Используйте rsync или создайте `.gitignore` и используйте Git.

### Вариант 3: Через скрипт update.sh (на сервере)

Если у вас уже настроен Git репозиторий:

```bash
# На сервере
cd /var/www/daribri
chmod +x update.sh
sudo ./update.sh
```

## Пошаговая инструкция для текущих изменений

### Шаг 1: Загрузите измененные файлы на сервер

**На вашем локальном компьютере (в директории проекта):**

```bash
# Используйте rsync для загрузки только измененных файлов
rsync -avz \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude 'database/miniapp.db' \
  --exclude '*.log' \
  frontend/css/styles.css \
  frontend/index.html \
  frontend/js/modules/shop.js \
  backend/app/services/telegram_notifier.py \
  root@your-server-ip:/var/www/daribri/
```

**Или загрузите все файлы:**

```bash
rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.git' --exclude 'database/miniapp.db' --exclude '*.log' \
  ./ root@your-server-ip:/var/www/daribri/
```

### Шаг 2: На сервере - обновите приложение

```bash
# Подключитесь к серверу
ssh root@your-server-ip

# Перейдите в директорию проекта
cd /var/www/daribri

# Остановите сервис
systemctl stop daribri

# Установите правильные права доступа
chown -R www-data:www-data /var/www/daribri
chmod -R 755 /var/www/daribri

# Если изменились зависимости Python, обновите их
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Перезапустите сервис
systemctl start daribri

# Проверьте статус
systemctl status daribri

# Проверьте логи (если есть ошибки)
journalctl -u daribri -n 50 --no-pager
```

### Шаг 3: Проверка работы

```bash
# Проверьте, что сервис работает
systemctl status daribri

# Проверьте API
curl http://localhost:8000/api/health

# Проверьте логи в реальном времени
journalctl -u daribri -f
```

## Настройка Git (для будущих обновлений)

Если хотите использовать Git для обновлений:

### 1. На локальном компьютере

```bash
# Инициализируйте Git репозиторий (если еще не сделано)
git init
git add .
git commit -m "Initial commit"

# Создайте репозиторий на GitHub/GitLab и добавьте remote
git remote add origin https://github.com/your-username/your-repo.git
git push -u origin main
```

### 2. На сервере

```bash
# На сервере
cd /var/www/daribri

# Если репозиторий еще не клонирован
git clone https://github.com/your-username/your-repo.git .

# Или если уже есть код, добавьте remote
git remote add origin https://github.com/your-username/your-repo.git
git pull origin main
```

### 3. Обновление через Git

```bash
# На сервере
cd /var/www/daribri
systemctl stop daribri
git pull
chown -R www-data:www-data /var/www/daribri
systemctl start daribri
```

## Автоматизация обновлений

### Создайте скрипт для быстрого обновления

**На локальном компьютере создайте файл `deploy-local.sh`:**

```bash
#!/bin/bash
# Скрипт для загрузки кода на сервер

SERVER="root@your-server-ip"
APP_DIR="/var/www/daribri"

echo "Загрузка файлов на сервер..."
rsync -avz \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude 'database/miniapp.db' \
  --exclude '*.log' \
  ./ $SERVER:$APP_DIR/

echo "Перезапуск сервиса на сервере..."
ssh $SERVER "cd $APP_DIR && systemctl stop daribri && chown -R www-data:www-data $APP_DIR && systemctl start daribri && systemctl status daribri"
```

**Сделайте скрипт исполняемым:**

```bash
chmod +x deploy-local.sh
```

**Использование:**

```bash
./deploy-local.sh
```

## Список измененных файлов для текущего обновления

Файлы, которые нужно обновить на сервере:

1. `frontend/css/styles.css` - изменения цвета и header
2. `frontend/index.html` - обновление версии иконки
3. `frontend/js/modules/shop.js` - исправление карты продавца
4. `backend/app/services/telegram_notifier.py` - убрана кнопка "Открыть приложение"

## Быстрая команда для обновления только этих файлов

```bash
# На локальном компьютере
rsync -avz \
  frontend/css/styles.css \
  frontend/index.html \
  frontend/js/modules/shop.js \
  backend/app/services/telegram_notifier.py \
  root@your-server-ip:/var/www/daribri/

# Затем на сервере
ssh root@your-server-ip "cd /var/www/daribri && systemctl stop daribri && chown -R www-data:www-data /var/www/daribri && systemctl start daribri"
```

## Устранение проблем

### Если сервис не запускается

```bash
# Проверьте логи
journalctl -u daribri -n 100 --no-pager

# Проверьте синтаксис Python файлов
cd /var/www/daribri
source venv/bin/activate
python -m py_compile backend/app/services/telegram_notifier.py

# Проверьте права доступа
ls -la /var/www/daribri
```

### Если изменения не применяются

```bash
# Очистите кэш браузера (для фронтенда)
# Или обновите версию в index.html (уже сделано: v=5)

# Перезапустите Nginx (если нужно)
systemctl reload nginx

# Перезапустите приложение
systemctl restart daribri
```

## Проверка после обновления

1. **Проверьте цвет header** - должен быть желто-зеленый (#dbff00)
2. **Проверьте карту продавца** - должна правильно показывать адрес
3. **Проверьте уведомления** - кнопка "Открыть приложение" должна отсутствовать
4. **Проверьте иконку** - должна быть новая версия

## Готово! 🎉

После выполнения этих шагов все изменения будут применены на сервере.


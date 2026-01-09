# Перемещение проекта в /var/www/daribri

## Шаг 1: Остановите сервис (если запущен)

```bash
systemctl stop daribri
```

## Шаг 2: Создайте директорию назначения

```bash
mkdir -p /var/www/daribri
```

## Шаг 3: Переместите файлы

```bash
# Перемещение всех файлов (сохраняет права)
mv ~/daribri/* /var/www/daribri/
mv ~/daribri/.* /var/www/daribri/ 2>/dev/null || true

# Или если нужно скопировать (оставив оригинал):
# cp -r ~/daribri/* /var/www/daribri/
# cp -r ~/daribri/.* /var/www/daribri/ 2>/dev/null || true
```

**Альтернативный вариант (более безопасный):**

```bash
# Копирование с исключением ненужных файлов
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  ~/daribri/ /var/www/daribri/
```

## Шаг 4: Установите правильные права доступа

```bash
cd /var/www/daribri

# Установка владельца
chown -R www-data:www-data /var/www/daribri

# Установка прав на директории
find /var/www/daribri -type d -exec chmod 755 {} \;

# Установка прав на файлы
find /var/www/daribri -type f -exec chmod 644 {} \;

# Права на исполняемые файлы
chmod +x /var/www/daribri/run_api.py
chmod +x /var/www/daribri/deploy.sh 2>/dev/null || true
chmod +x /var/www/daribri/update.sh 2>/dev/null || true

# Защита .env файла
chmod 600 /var/www/daribri/.env

# Права на директорию базы данных и uploads
chmod 755 /var/www/daribri/database
chmod 755 /var/www/daribri/uploads
chmod 644 /var/www/daribri/database/*.db 2>/dev/null || true
```

## Шаг 5: Обновите пути в systemd сервисе

```bash
nano /etc/systemd/system/daribri.service
```

Убедитесь, что пути правильные:
```
WorkingDirectory=/var/www/daribri
Environment="PATH=/var/www/daribri/venv/bin"
ExecStart=/var/www/daribri/venv/bin/python /var/www/daribri/run_api.py
EnvironmentFile=/var/www/daribri/.env
```

Сохраните и выйдите: `Ctrl+O`, `Enter`, `Ctrl+X`

## Шаг 6: Перезагрузите systemd и запустите сервис

```bash
systemctl daemon-reload
systemctl start daribri
systemctl status daribri
```

## Шаг 7: Проверьте работу

```bash
# Проверка API
curl http://localhost:8000/api/health

# Проверка логов
journalctl -u daribri -f
```

## Шаг 8: Удалите старую директорию (опционально)

```bash
# Только после того, как убедитесь, что все работает!
rm -rf ~/daribri
```

## Быстрая команда (все в одном)

```bash
# Остановка сервиса
systemctl stop daribri

# Создание директории
mkdir -p /var/www/daribri

# Перемещение файлов
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
  ~/daribri/ /var/www/daribri/

# Установка прав
chown -R www-data:www-data /var/www/daribri
find /var/www/daribri -type d -exec chmod 755 {} \;
find /var/www/daribri -type f -exec chmod 644 {} \;
chmod +x /var/www/daribri/run_api.py
chmod 600 /var/www/daribri/.env 2>/dev/null || true

# Обновление systemd
systemctl daemon-reload
systemctl start daribri
systemctl status daribri
```


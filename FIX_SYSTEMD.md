# Исправление systemd сервиса

## Проблема
Ошибка: "Assignment outside of section" означает, что файл сервиса поврежден или имеет неправильный формат.

## Решение

### Шаг 1: Удалите старый файл сервиса

```bash
rm /etc/systemd/system/daribri.service
```

### Шаг 2: Создайте правильный файл сервиса

```bash
nano /etc/systemd/system/daribri.service
```

Скопируйте и вставьте следующее содержимое:

```ini
[Unit]
Description=Дарибри - Telegram Mini App API + Bot
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/daribri
Environment="PATH=/var/www/daribri/venv/bin"
EnvironmentFile=/var/www/daribri/.env
ExecStart=/var/www/daribri/venv/bin/python /var/www/daribri/run_api.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Важно:** 
- Убедитесь, что нет лишних пробелов в начале строк
- Убедитесь, что все секции [Unit], [Service], [Install] присутствуют
- Проверьте, что пути правильные

Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

### Шаг 3: Проверьте синтаксис файла

```bash
systemctl daemon-reload
systemd-analyze verify daribri.service
```

Если есть ошибки, они будут показаны.

### Шаг 4: Запустите сервис

```bash
systemctl enable daribri
systemctl start daribri
systemctl status daribri
```

### Шаг 5: Проверьте логи

```bash
journalctl -u daribri -f
```

## Альтернативный способ (через команду)

```bash
cat > /etc/systemd/system/daribri.service << 'EOF'
[Unit]
Description=Дарибри - Telegram Mini App API + Bot
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/daribri
Environment="PATH=/var/www/daribri/venv/bin"
EnvironmentFile=/var/www/daribri/.env
ExecStart=/var/www/daribri/venv/bin/python /var/www/daribri/run_api.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable daribri
systemctl start daribri
systemctl status daribri
```


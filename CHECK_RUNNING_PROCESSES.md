# Проверка запущенных процессов проекта

## Быстрая проверка

```bash
# Проверить процессы, связанные с проектом
ps aux | grep -i "run_api.py\|daribri" | grep -v grep

# Проверить статус systemd сервиса
sudo systemctl status daribri

# Проверить процессы на порту 8000
sudo lsof -i :8000
# или
sudo netstat -tulpn | grep :8000
# или
sudo ss -tulpn | grep :8000
```

## Детальная проверка

### 1. Процессы Python, связанные с проектом

```bash
# Все процессы, содержащие "run_api" или "daribri"
ps aux | grep -E "run_api|daribri" | grep -v grep

# С подробной информацией
ps auxf | grep -E "run_api|daribri" | grep -v grep
```

### 2. Проверка systemd сервиса

```bash
# Статус сервиса
sudo systemctl status daribri

# Список всех systemd юнитов с "daribri"
systemctl list-units | grep daribri

# Проверка активных процессов сервиса
systemctl show daribri | grep MainPID
```

### 3. Проверка по порту

```bash
# Какие процессы используют порт 8000
sudo lsof -i :8000

# Альтернативные команды
sudo netstat -tulpn | grep :8000
sudo ss -tulpn | grep :8000

# Проверка всех портов Python процессов
sudo lsof -i -P -n | grep python
```

### 4. Проверка по рабочей директории

```bash
# Процессы, использующие файлы в директории проекта
sudo lsof +D /var/www/daribri

# Процессы, использующие конкретный файл
sudo lsof /var/www/daribri/run_api.py
```

### 5. Проверка по пользователю

```bash
# Все процессы пользователя www-data
ps aux | grep www-data | grep -v grep

# Процессы пользователя с деталями
sudo lsof -u www-data | grep -E "python|daribri"
```

### 6. Проверка всех Python процессов

```bash
# Все запущенные Python процессы
ps aux | grep python | grep -v grep

# С деревом процессов
ps auxf | grep python | grep -v grep

# С PID и командой
ps -eo pid,cmd,etime | grep python | grep -v grep
```

## Остановка всех процессов

### Безопасный способ (через systemd)

```bash
# Остановить сервис
sudo systemctl stop daribri

# Проверить, что остановился
sudo systemctl status daribri
```

### Принудительная остановка

```bash
# Остановить все процессы, содержащие "run_api.py"
sudo pkill -f "run_api.py"

# Остановить все процессы, содержащие "daribri"
sudo pkill -f "daribri"

# Принудительное завершение (если не помогает)
sudo pkill -9 -f "run_api.py"
sudo pkill -9 -f "daribri"

# Остановить по PID (если знаете PID)
sudo kill <PID>
# или принудительно
sudo kill -9 <PID>
```

## Проверка конфликта Telegram бота

Если видите ошибку `TelegramConflictError: terminated by other getUpdates request`, это означает, что запущено несколько экземпляров бота:

```bash
# Найти все процессы бота
ps aux | grep -E "bot|telegram|aiogram" | grep -v grep

# Найти процессы по токену (если виден в процессах)
ps aux | grep -i "BOT_TOKEN" | grep -v grep
```

## Автоматическая проверка

Используйте готовый скрипт:

```bash
chmod +x check_running_processes.sh
./check_running_processes.sh
```

## Диагностика проблем

### Если процесс не останавливается:

```bash
# 1. Найти PID процесса
ps aux | grep run_api.py | grep -v grep

# 2. Проверить, что это за процесс
sudo ls -l /proc/<PID>/exe

# 3. Проверить, кто его запустил
ps -o pid,ppid,cmd -p <PID>

# 4. Принудительно завершить
sudo kill -9 <PID>
```

### Если systemd показывает, что сервис запущен, но процесс не работает:

```bash
# Проверить реальный статус
sudo systemctl status daribri

# Перезагрузить systemd
sudo systemctl daemon-reload

# Перезапустить сервис
sudo systemctl restart daribri
```

### Проверка логов для поиска проблем:

```bash
# Логи systemd
sudo journalctl -u daribri -n 50 --no-pager

# Логи с фильтром по ошибкам
sudo journalctl -u daribri | grep -i error

# Логи в реальном времени
sudo journalctl -u daribri -f
```


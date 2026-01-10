# Инструкция по откату версии на сервере

## Быстрый способ (рекомендуется)

### 1. Подключитесь к серверу через SSH

```bash
ssh root@your-server-ip
# или
ssh root@flow.plus-shop.ru
```

### 2. Перейдите в директорию приложения

```bash
cd /var/www/daribri
```

### 3. Остановите сервис

```bash
systemctl stop daribri
```

### 4. Обновите код из GitHub (откат версии)

```bash
git pull origin main
```

Это автоматически обновит код до последней версии (которую мы откатили локально и запушили в репозиторий).

### 5. Запустите сервис

```bash
systemctl start daribri
```

### 6. Проверьте статус

```bash
systemctl status daribri
```

### 7. Проверьте логи (если нужно)

```bash
journalctl -u daribri -n 50 --no-pager
```

---

## Альтернативный способ (с использованием скрипта update.sh)

### 1. Подключитесь к серверу

```bash
ssh root@your-server-ip
cd /var/www/daribri
```

### 2. Запустите скрипт обновления

```bash
sudo ./update.sh
```

Скрипт автоматически:
- Остановит сервис
- Создаст бэкап базы данных
- Обновит код через `git pull`
- Обновит зависимости
- Запустит сервис
- Проверит статус

---

## Проверка версии на сервере

После отката проверьте, что версия откатилась правильно:

```bash
cd /var/www/daribri
git log --oneline -5
```

Вы должны увидеть коммит `2d1fcc9 Add Made by @mnogoprofilnyi credit text at bottom of profile page` в списке последних коммитов.

---

## Если возникли проблемы

### Проблема: "Permission denied"
```bash
# Запустите команды от root
sudo su
cd /var/www/daribri
git pull origin main
```

### Проблема: "Git repository is behind"
```bash
# Принудительно обновите (осторожно!)
git fetch origin
git reset --hard origin/main
systemctl restart daribri
```

### Проблема: Конфликты при git pull
```bash
# Если есть конфликты, сбросьте локальные изменения на сервере
git fetch origin
git reset --hard origin/main
systemctl restart daribri
```

### Проблема: Сервис не запускается
```bash
# Проверьте логи
journalctl -u daribri -n 100 --no-pager

# Проверьте конфигурацию
cat /etc/systemd/system/daribri.service

# Попробуйте запустить вручную для отладки
cd /var/www/daribri
source venv/bin/activate
python run_api.py
```

---

## Важно!

⚠️ **После отката версии выполните жесткую перезагрузку страницы в браузере:**
- **Windows/Linux:** `Ctrl + Shift + R`
- **Mac:** `Cmd + Shift + R`

Это необходимо для очистки кеша браузера и загрузки новых версий JavaScript и CSS файлов.

---

## Готово! ✅

После выполнения этих шагов версия на сервере будет откачена до состояния до выравнивания магазина, и все страницы (Избранное, Корзина, Профиль, Магазин) должны снова работать корректно.


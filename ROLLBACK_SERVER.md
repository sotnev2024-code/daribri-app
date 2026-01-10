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

### 4. Настройте Git (если нужно, только первый раз)

```bash
# Настройте имя и email для Git (можно локально для репозитория)
git config user.email "deploy@daribri.ru"
git config user.name "Deploy Bot"
```

**Или глобально (если нужно для всех репозиториев на сервере):**
```bash
git config --global user.email "deploy@daribri.ru"
git config --global user.name "Deploy Bot"
```

### 5. Обновите код из GitHub (откат версии)

```bash
git pull origin main
```

Это автоматически обновит код до последней версии (которую мы откатили локально и запушили в репозиторий).

### 6. Запустите сервис

```bash
systemctl start daribri
```

### 7. Проверьте статус

```bash
systemctl status daribri
```

### 8. Проверьте логи (если нужно)

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

### Проблема: "Please tell me who you are" (Git identity не настроен)
```bash
# Настройте Git identity локально для репозитория
cd /var/www/daribri
git config user.email "deploy@daribri.ru"
git config user.name "Deploy Bot"

# Затем повторите git pull
git pull origin main
```

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

### Проблема: "Pulling is not possible because you have unmerged files" (Конфликты при git pull)

**Вариант 1: Принудительное обновление (рекомендуется для сервера)**

Если на сервере не должно быть локальных изменений (обычно так и есть для сервера деплоя):

```bash
cd /var/www/daribri
systemctl stop daribri

# Проверьте, какие файлы в конфликте
git status

# Принудительно обновите репозиторий до версии из GitHub
git fetch origin
git reset --hard origin/main

# Запустите сервис
systemctl start daribri
systemctl status daribri
```

**⚠️ Внимание:** `git reset --hard` **удалит все локальные изменения** на сервере. Это нормально, если сервер используется только для деплоя и не содержит важных локальных изменений.

**Вариант 2: Разрешение конфликтов вручную (если нужны локальные изменения)**

Если на сервере есть важные локальные изменения, которые нужно сохранить:

```bash
cd /var/www/daribri

# Проверьте конфликты
git status

# Посмотрите конфликтующие файлы
git diff

# Для каждого конфликтующего файла:
# 1. Откройте файл в редакторе
nano path/to/conflicting/file

# 2. Найдите маркеры конфликтов (<<<<<<, ======, >>>>>>)
# 3. Разрешите конфликты вручную
# 4. Сохраните файл

# После разрешения всех конфликтов:
git add .
git commit -m "Resolve merge conflicts"

# Затем повторите pull
git pull origin main
```

**Рекомендация:** Для сервера деплоя используйте **Вариант 1**, так как все изменения должны приходить через Git из репозитория.

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


# Исправление проблемы с git pull

## Проблема
Git не может выполнить pull из-за локальных изменений в файлах.

## Решение

### Вариант 1: Отменить локальные изменения (рекомендуется для nginx/daribri.conf)

Файл `nginx/daribri.conf` в репозитории - это шаблон. Реальная конфигурация находится в `/etc/nginx/sites-available/daribri`.

```bash
cd /var/www/daribri
git checkout -- nginx/daribri.conf
git pull origin main
```

### Вариант 2: Сохранить изменения временно (stash)

Если вы хотите сохранить локальные изменения:

```bash
cd /var/www/daribri
git stash
git pull origin main
git stash pop  # Применить сохраненные изменения обратно (если нужно)
```

### Вариант 3: Закоммитить изменения

Если изменения важны и их нужно сохранить в репозитории:

```bash
cd /var/www/daribri
git add nginx/daribri.conf
git commit -m "Update nginx config for production"
git pull origin main
# Если будут конфликты, разрешите их вручную
```

## После успешного pull

Выполните диагностику:

```bash
python database/check_data.py
```




# Скрипт для деплоя на сервер (PowerShell)
# Использование: .\deploy.ps1

param(
    [string]$Server = "root@your-server-ip",  # Замените на ваш IP
    [string]$AppDir = "/var/www/daribri"
)

Write-Host "🚀 Начинаем деплой на сервер..." -ForegroundColor Green
Write-Host ""

# Проверка, что мы в Git репозитории
if (-not (Test-Path .git)) {
    Write-Host "❌ Ошибка: Это не Git репозиторий!" -ForegroundColor Red
    Write-Host "Инициализируйте Git: git init" -ForegroundColor Yellow
    exit 1
}

# Проверка изменений
$status = git status --porcelain
if ($status) {
    Write-Host "📝 Обнаружены изменения:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    
    $commit = Read-Host "Хотите закоммитить изменения? (y/n)"
    if ($commit -eq "y" -or $commit -eq "Y") {
        $message = Read-Host "Введите сообщение коммита"
        if ([string]::IsNullOrWhiteSpace($message)) {
            $message = "Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        }
        
        Write-Host "📦 Коммитим изменения..." -ForegroundColor Yellow
        git add .
        git commit -m $message
        
        Write-Host "⬆️ Отправляем на GitHub..." -ForegroundColor Yellow
        git push origin main
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️ Предупреждение: Не удалось отправить на GitHub" -ForegroundColor Yellow
            Write-Host "Продолжаем деплой на сервер..." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "✅ Нет локальных изменений" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔄 Обновляем сервер..." -ForegroundColor Yellow

# Команда для выполнения на сервере
$deployCommand = @"
cd $AppDir && \
echo 'Остановка сервиса...' && \
systemctl stop daribri && \
echo 'Обновление кода из GitHub...' && \
git pull origin main && \
echo 'Обновление зависимостей...' && \
source venv/bin/activate && \
pip install -r requirements.txt --upgrade --quiet && \
echo 'Установка прав...' && \
chown -R www-data:www-data $AppDir && \
chmod -R 755 $AppDir && \
echo 'Запуск сервиса...' && \
systemctl start daribri && \
sleep 2 && \
echo '' && \
echo 'Проверка статуса:' && \
systemctl status daribri --no-pager -l
"@

# Выполняем команду на сервере
ssh $Server $deployCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Деплой завершен успешно!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Ошибка при деплое!" -ForegroundColor Red
    Write-Host "Проверьте логи на сервере: ssh $Server 'journalctl -u daribri -n 50'" -ForegroundColor Yellow
    exit 1
}


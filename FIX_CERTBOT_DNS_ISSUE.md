# Исправление ошибки Certbot: DNS/доступность домена

## Проблема

Certbot не может получить доступ к домену даже в standalone режиме. Ошибка показывает IPv6 адрес и 404.

## Диагностика

### 1. Проверьте DNS записи

```bash
# Проверьте A запись (IPv4)
nslookup daribri.ru
dig daribri.ru A

# Проверьте AAAA запись (IPv6)
nslookup -type=AAAA daribri.ru
dig daribri.ru AAAA

# Проверьте www поддомен
nslookup www.daribri.ru
dig www.daribri.ru A
```

**Что должно быть:**
- A запись должна указывать на IPv4 адрес вашего сервера
- Если IPv6 не настроен, AAAA запись не должна существовать (или должна указывать на правильный IPv6)

### 2. Проверьте IP адрес сервера

```bash
# Узнайте IP адрес сервера
ip addr show
# или
hostname -I

# Проверьте внешний IP
curl ifconfig.me
curl ipv4.icanhazip.com
```

### 3. Проверьте доступность порта 80

```bash
# Проверьте, что порт 80 слушается
sudo netstat -tulpn | grep :80
sudo ss -tulpn | grep :80

# Проверьте firewall
sudo ufw status
sudo iptables -L -n | grep 80

# Если порт закрыт, откройте его
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

### 4. Проверьте доступность домена с сервера

```bash
# Проверьте HTTP доступность
curl -v http://daribri.ru
curl -v http://www.daribri.ru

# Проверьте с внешнего сервиса
# Откройте в браузере: http://daribri.ru
```

---

## Решение 1: Исправление DNS записей

### Если DNS не указывает на правильный IP

1. **Зайдите в панель управления доменом** (у регистратора)
2. **Убедитесь, что A записи правильные:**
   - `daribri.ru` → IPv4 адрес вашего сервера
   - `www.daribri.ru` → IPv4 адрес вашего сервера

3. **Если IPv6 не настроен, удалите AAAA записи** (или не добавляйте их)

4. **Подождите распространения DNS** (5-30 минут, иногда до 24 часов)

5. **Проверьте через разные сервисы:**
   - https://dnschecker.org/
   - https://www.whatsmydns.net/

### Если DNS указывает на неправильный IP

```bash
# Узнайте правильный IP сервера
curl ifconfig.me

# Обновите DNS записи у регистратора на этот IP
```

---

## Решение 2: Временное отключение IPv6 (если проблема в IPv6)

Если проблема в IPv6, можно временно отключить его проверку:

```bash
# Получите сертификат только для IPv4
sudo certbot certonly --standalone -d daribri.ru -d www.daribri.ru --preferred-challenges http --force-renewal
```

Или настройте IPv6 правильно:

```bash
# Проверьте IPv6 адрес сервера
ip -6 addr show

# Если IPv6 настроен, убедитесь, что DNS AAAA запись указывает на правильный IPv6
```

---

## Решение 3: Использование DNS-01 challenge (для продвинутых)

Если HTTP challenge не работает, можно использовать DNS challenge:

```bash
# Установите плагин для вашего DNS провайдера (пример для Cloudflare)
sudo apt install python3-certbot-dns-cloudflare

# Или используйте ручной DNS challenge
sudo certbot certonly --manual --preferred-challenges dns -d daribri.ru -d www.daribri.ru
```

**Во время установки:**
1. Certbot покажет TXT запись
2. Добавьте её в DNS у регистратора
3. Подождите распространения (5-10 минут)
4. Нажмите Enter для продолжения

---

## Решение 4: Проверка доступности с внешних сервисов

Проверьте, доступен ли домен извне:

```bash
# С вашего компьютера
curl -I http://daribri.ru
curl -I http://www.daribri.ru

# Должны вернуть HTTP ответ (не обязательно 200, может быть 301/302)
```

Если не доступен:
1. Проверьте firewall на сервере
2. Проверьте firewall у провайдера (если есть)
3. Проверьте, что порт 80 открыт в панели управления сервером (если VPS)

---

## Решение 5: Использование другого домена для проверки

Если у вас есть другой домен, который работает, попробуйте:

```bash
# Получите сертификат для рабочего домена
sudo certbot certonly --standalone -d working-domain.com

# Если работает, значит проблема именно с daribri.ru
```

---

## Пошаговая диагностика

Выполните команды по порядку:

```bash
# 1. Проверьте IP сервера
echo "IP сервера:"
curl ifconfig.me
echo ""

# 2. Проверьте DNS
echo "DNS A запись:"
dig daribri.ru A +short
echo ""

# 3. Проверьте, что DNS указывает на правильный IP
DNS_IP=$(dig daribri.ru A +short | head -n1)
SERVER_IP=$(curl -s ifconfig.me)
echo "DNS IP: $DNS_IP"
echo "Server IP: $SERVER_IP"
if [ "$DNS_IP" = "$SERVER_IP" ]; then
    echo "✅ DNS указывает на правильный IP"
else
    echo "❌ DNS указывает на неправильный IP!"
    echo "Обновите DNS записи у регистратора"
fi

# 4. Проверьте порт 80
echo ""
echo "Порт 80:"
sudo netstat -tulpn | grep :80 || echo "Порт 80 не слушается"

# 5. Проверьте firewall
echo ""
echo "Firewall:"
sudo ufw status | grep 80 || echo "Порт 80 не открыт в firewall"

# 6. Проверьте доступность
echo ""
echo "Доступность домена:"
curl -I http://daribri.ru 2>&1 | head -n1
```

---

## Быстрое решение (если DNS правильный)

Если DNS правильный, но всё равно не работает:

```bash
# 1. Убедитесь, что порт 80 открыт
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# 2. Убедитесь, что Nginx остановлен
sudo systemctl stop nginx

# 3. Проверьте, что порт 80 свободен
sudo netstat -tulpn | grep :80
# Если что-то слушается на порту 80, остановите это

# 4. Получите сертификат
sudo certbot certonly --standalone -d daribri.ru -d www.daribri.ru

# 5. Запустите Nginx
sudo systemctl start nginx
```

---

## Проверка после исправления

```bash
# 1. Проверьте DNS
nslookup daribri.ru
# Должен вернуть IP вашего сервера

# 2. Проверьте доступность
curl -I http://daribri.ru
# Должен вернуть HTTP ответ

# 3. Проверьте сертификат
sudo certbot certificates
# Должен показать сертификат для daribri.ru

# 4. Проверьте HTTPS
curl -I https://daribri.ru
# Должен вернуть HTTP/2 200
```

---

## Если ничего не помогает

1. **Проверьте логи Certbot:**
   ```bash
   sudo tail -f /var/log/letsencrypt/letsencrypt.log
   ```

2. **Проверьте, не блокирует ли провайдер порт 80:**
   - Некоторые провайдеры блокируют порт 80
   - В этом случае нужно использовать другой порт или связаться с поддержкой

3. **Проверьте, правильно ли настроен домен:**
   - Убедитесь, что домен делегирован на правильные NS серверы
   - Проверьте через `dig NS daribri.ru`

4. **Попробуйте получить сертификат для одного домена:**
   ```bash
   sudo certbot certonly --standalone -d daribri.ru
   # Если работает, добавьте www позже
   ```

---

## Готово! ✅

После исправления DNS и проверки доступности Certbot должен успешно получить сертификат.


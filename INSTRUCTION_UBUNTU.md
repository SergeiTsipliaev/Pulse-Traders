# 🚀 ИНСТРУКЦИЯ: ЗАПУСК PULSE TRADERS НА FORNEX С POSTGRESQL И DOCKER

## 📋 СОДЕРЖАНИЕ
1. Подготовка окружения
2. Локальный запуск (для тестирования)
3. Запуск на сервере Fornex
4. Проверка и troubleshooting

---

## ⚙️ ЧАСТЬ 1: ПОДГОТОВКА ОКРУЖЕНИЯ

### Шаг 1: Установите Docker и Docker Compose на Fornex

**На Ubuntu/Debian:**
```bash
# Обновляем пакеты
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Устанавливаем Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверяем версии
docker --version
docker-compose --version
```

### Шаг 2: Создайте директорию проекта

```bash
# Перейдите в домашнюю директорию
cd /home/username

# Создайте папку для проекта
mkdir pulse-traders
cd pulse-traders

# Удостоверьтесь, что туда загружены файлы:
ls -la
# Должны быть:
# - Dockerfile
# - requirements.txt
# - config.py
# - api/
# - bot/
# - models/
# - static/
# - и другие файлы проекта
```

### Шаг 3: Создайте файл .env с конфигурацией

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте .env
nano .env
```

**Содержимое для Fornex (.env):**
```env
# ==================== DATABASE ====================
# Docker запустит PostgreSQL в контейнере
DB_HOST=postgres
DB_PORT=5432
DB_NAME=pulsetraders
DB_USER=postgres
# ВАЖНО: Измените пароль на БЕЗОПАСНЫЙ!
DB_PASSWORD=ваш_сложный_пароль_123ABC!@#xyz

# ==================== DOCKER PORTS ====================
# На каком порту приложение слушает на сервере
APP_PORT=5000

# ==================== TELEGRAM BOT ====================
# Вставьте ваш реальный токен бота
BOT_TOKEN=123456789:ABCdefghijklmnopqrstuvwxyz1234567890

# ==================== WEB APP ====================
# Измените на домен Fornex
WEB_APP_URL=https://pulse-traders.com

# ==================== SECURITY ====================
# Генерируйте крутой SECRET_KEY (используйте генератор)
SECRET_KEY=super_secret_key_that_nobody_can_guess_89234789234789234_xyz

JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=720

# ==================== ADMIN ====================
# Ваши Telegram ID для администраторского доступа
ADMIN_IDS=123456789,987654321

# ==================== PYTHON ====================
FLASK_ENV=production
PYTHONUNBUFFERED=1
```

---

## 🐳 ЧАСТЬ 2: ЗАПУСК С DOCKER-COMPOSE

### Вариант А: Первый запуск (создание контейнеров)

```bash
# Перейдите в директорию проекта
cd /home/username/pulse-traders

# Постройте образ приложения
docker-compose build

# Запустите контейнеры в фоне
docker-compose up -d

# Проверьте статус
docker-compose ps

# Должно быть:
# NAME              SERVICE   STATUS
# pulse-traders-db  postgres  Up (healthy)
# pulse-traders-app app       Up
```

### Вариант Б: Остановка и перезапуск

```bash
# Остановить все контейнеры
docker-compose down

# Запустить заново
docker-compose up -d

# Только перезагрузить приложение (без БД)
docker-compose restart app

# Просмотреть логи
docker-compose logs -f app     # Логи приложения
docker-compose logs -f postgres # Логи БД
docker-compose logs -f          # Все логи
```

---

## 📊 ЧАСТЬ 3: ПРОВЕРКА POSTGRESQL

### Проверка, что БД запустилась

```bash
# Просмотрите статус контейнеров
docker-compose ps

# Проверьте логи PostgreSQL
docker-compose logs postgres

# Должны увидеть: "database system is ready to accept connections"
```

### Подключение к БД (внутри контейнера)

```bash
# Откройте bash контейнера PostgreSQL
docker-compose exec postgres bash

# Подключитесь к БД
psql -U postgres -d pulsetraders

# Проверьте таблицы
\dt

# Выход из psql
\q

# Выход из контейнера
exit
```

### Удаленное подключение к БД (со своего компьютера)

```bash
# Убедитесь, что в docker-compose.yml открыт порт 5432
# Затем используйте любой PostgreSQL клиент:

psql -h your_fornex_ip -U postgres -d pulsetraders

# Или через DBeaver / pgAdmin
```

---

## 🔍 ЧАСТЬ 4: ПРОВЕРКА ПРИЛОЖЕНИЯ

### Проверка работает ли приложение

```bash
# Проверьте логи приложения
docker-compose logs app

# Должны увидеть что-то вроде:
# INFO: Uvicorn running on 0.0.0.0:5000
# ✅ PostgreSQL пул подключений установлен
# ✅ Все таблицы БД созданы/проверены
```

### Проверка на браузере

```
http://ваш_fornex_ip:5000
или
https://pulse-traders.com
```

### Тестирование API

```bash
# Простой тест здоровья приложения
curl http://your_fornex_ip:5000/health

# Если вернет что-то, значит приложение работает
```

---

## 📝 ЧАСТЬ 5: ОБНОВЛЕНИЕ КОДА

Если вы изменили файлы проекта на сервере:

```bash
cd /home/username/pulse-traders

# Пересоберите образ
docker-compose build

# Перезапустите контейнеры
docker-compose up -d

# Или просто переложите новые файлы и пересоберите:
docker-compose down
docker-compose up -d --build
```

---

## 🛡️ ЧАСТЬ 6: BACKUP БАЗЫ ДАННЫХ

### Экспорт данных БД

```bash
# Резервная копия полной БД
docker-compose exec postgres pg_dump -U postgres pulsetraders > backup.sql

# Восстановление из backup
docker-compose exec -T postgres psql -U postgres pulsetraders < backup.sql
```

### Автоматический backup (cron)

```bash
# Отредактируйте crontab
crontab -e

# Добавьте строку для ежедневного backup в 3:00 ночи
0 3 * * * cd /home/username/pulse-traders && docker-compose exec -T postgres pg_dump -U postgres pulsetraders > backups/backup_$(date +\%Y\%m\%d).sql
```

---

## ⚠️ ЧАСТЬ 7: ВАЖНЫЕ ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

Вам нужно изменить в своем проекте:

### 1. Замените config.py на config_updated.py
```bash
cp config_updated.py config.py
```

### 2. Добавьте docker-compose.yml в корень проекта
Скопируйте предоставленный docker-compose.yml в корень

### 3. Создайте .env файл
```bash
cp .env.example .env
nano .env  # Отредактируйте с вашими данными
```

### 4. Убедитесь, что Dockerfile присутствует
Он должен быть в корне проекта (он уже есть в вашем репо)

---

## 🔗 ЧАСТЬ 8: NGINX REVERSE PROXY (опционально для Fornex)

Если вы хотите запустить на 80/443 порту:

```bash
# Создайте nginx конфиг /etc/nginx/sites-available/pulse-traders

server {
    listen 80;
    server_name pulse-traders.com www.pulse-traders.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}

# Включите конфиг
sudo ln -s /etc/nginx/sites-available/pulse-traders /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Для HTTPS используйте Certbot:
sudo certbot --nginx -d pulse-traders.com -d www.pulse-traders.com
```

---

## 🆘 TROUBLESHOOTING

### Проблема: "Cannot connect to database"
```bash
# Проверьте статус БД
docker-compose logs postgres

# Переинициализируйте БД
docker-compose down -v  # -v удаляет volumes
docker-compose up -d
```

### Проблема: "Port 5000 already in use"
```bash
# Измените PORT в docker-compose.yml или .env
# Или остановите процесс на этом порту
lsof -i :5000
kill -9 <PID>
```

### Проблема: "БД создалась, но таблицы не видны"
```bash
# Проверьте логи приложения
docker-compose logs app

# Если ошибка в create_tables, проверьте database.py
# Иногда нужно перезагрузить контейнер
docker-compose restart app
```

### Просмотрите все логи
```bash
docker-compose logs --tail=100  # Последние 100 строк
docker-compose logs -f          # Следить за логами в реальном времени
```

---

## ✅ ФИНАЛЬНЫЙ CHECKLIST

- [ ] Docker установлен на Fornex
- [ ] Файлы проекта загружены в /home/username/pulse-traders
- [ ] Создан и отредактирован .env файл
- [ ] config.py заменен на config_updated.py
- [ ] docker-compose.yml находится в корне проекта
- [ ] Запущен `docker-compose up -d`
- [ ] `docker-compose ps` показывает оба контейнера (Up)
- [ ] Приложение доступно на http://ip:5000
- [ ] БД доступна на порту 5432
- [ ] Telegram бот получает BOT_TOKEN в .env
- [ ] Домен pulse-traders.com настроен (A record на IP Fornex)
- [ ] Создан nginx конфиг (если нужен)
- [ ] Резервные копии БД сохраняются

---

## 🚀 КОМАНДЫ ДЛЯ БЫСТРОГО СТАРТА

```bash
# Все в одной строке для быстрого старта:
cd /home/username/pulse-traders && docker-compose down && docker-compose up -d --build

# Просмотр статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f app
```

---

**Готово!** 🎉 Ваш Pulse Traders работает на Fornex с PostgreSQL в Docker!
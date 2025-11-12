# Проверьте, установлен ли Homebrew
brew --version

# Если нет, установите
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Вариант 1: Через Homebrew (рекомендуется)
brew install --cask docker

# Вариант 2: Загрузите .dmg файл вручную
# Перейдите на https://www.docker.com/products/docker-desktop/
# Скачайте версию для вашего Mac (Intel или Apple Silicon)
# Запустите установщик

# Проверьте установку
docker --version
docker-compose --version

# На Mac Docker Desktop автоматически запускается при загрузке

# Откройте Applications → Docker.app
# Или через command line:
open /Applications/Docker.app

# Дождитесь, пока Docker будет готов (значок в меню)
# Проверьте статус:
docker info


# Перейдите в домашнюю директорию
cd ~

# Создайте папку для проекта
mkdir pulse-traders
cd pulse-traders

# Скопируйте файлы проекта (git clone или вручную)
git clone https://github.com/SergeiTsipliaev/Pulse-Traders.git .

# Проверьте содержимое
ls -la

# Отредактируйте .env для локальной разработки
nano .env

# Перейдите в директорию проекта
cd ~/pulse-traders

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

# Просмотрите логи app
docker-compose logs -f app

# Должны увидеть:
# ✅ PostgreSQL подключено
# ✅ Таблицы созданы
# INFO: Uvicorn running on 0.0.0.0:5000

# Нажмите Ctrl+C для выхода из логов

# Создайте пользователя trader и БД
docker-compose exec -T postgres psql -U postgres -c "CREATE USER trader WITH PASSWORD 'your_secure_password_123';"
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE pulse_traders OWNER trader;"
docker-compose exec -T postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE pulse_traders TO trader;"

# Проверьте
docker-compose exec -T postgres psql -U postgres -c "SELECT usename FROM pg_user;"

# Откройте браузер и перейдите на:
http://localhost:5000

# Или используйте IP вашего Mac в локальной сети:
# Узнайте IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# Используйте IP вместо localhost (если нужен доступ с других устройств)
http://192.168.1.100:5000

# Проверьте здоровье приложения
curl http://localhost:5000/api/health

# Должен вернуть JSON:
# {"status":"ok","database":"connected",...}



# Способ 1: Через Docker контейнер
docker-compose exec postgres psql -U postgres -d pulsetraders

# Способ 2: Если PostgreSQL установлен локально на Mac
psql -h localhost -U postgres -d pulsetraders

# Полезные команды psql:
# \dt              - показать все таблицы
# \du              - показать всех пользователей
# SELECT * FROM users;  - просмотр данных
# \q               - выход

# Установите PostgreSQL через Homebrew (для локальной разработки)
brew install postgresql@15

# Запустите:
brew services start postgresql@15

# Подключитесь к локальной БД:
psql -U $(whoami)

# Установите DBeaver через Homebrew
brew install --cask dbeaver-community

# Или используйте pgAdmin в браузере
docker run -p 5050:80 \
  -e PGADMIN_DEFAULT_EMAIL=admin@example.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin \
  dpage/pgadmin4

# Откройте http://localhost:5050
# Email: admin@example.com
# Password: admin




# Остановить все контейнеры (сохранит данные)
docker-compose down

# Остановить и удалить всё включая БД (осторожно!)
docker-compose down -v

# Перезагрузить приложение
docker-compose restart app

# Перезагрузить БД
docker-compose restart postgres

# Просмотреть логи (все)
docker-compose logs -f

# Просмотреть логи только app
docker-compose logs -f app

# Просмотреть последние 50 строк логов
docker-compose logs --tail=50

# Зайти внутрь контейнера bash
docker-compose exec app bash

# Выполнить команду в контейнере
docker-compose exec app python -m pytest

# Способ 1: Пересобрать образ и перезагрузить
docker-compose down
docker-compose up -d --build

# Способ 2: Если изменили только Python файлы (без зависимостей)
docker-compose restart app

# Способ 3: С git pull
cd ~/pulse-traders
git pull origin main
docker-compose up -d --build


# Экспортируйте БД в SQL файл
docker-compose exec postgres pg_dump -U postgres pulsetraders > ~/backup_$(date +%Y%m%d).sql

# Проверьте размер файла
ls -lh ~/backup_*.sql


# Восстановите БД из файла
docker-compose exec -T postgres psql -U postgres pulsetraders < ~/backup_20231115.sql


# Отредактируйте crontab
crontab -e

# Добавьте строку для ежедневного backup в 3:00 ночи:
0 3 * * * cd ~/pulse-traders && docker-compose exec -T postgres pg_dump -U postgres pulsetraders > ~/backups/backup_$(date +\%Y\%m\%d).sql

# Создайте папку для backups
mkdir -p ~/backups


# С логами в реальном времени
docker-compose up

# Нажмите Ctrl+C для остановки

# Перестраивается при каждом запуске для отладки
docker-compose up --build

# Отредактируйте файлы в ~/pulse-traders
# Docker автоматически не перезагружает при изменении Python файлов

# Для изменений в Python коде:
docker-compose restart app

# Для изменений в requirements.txt:
docker-compose down
docker-compose up -d --build

# Для изменений в SQL/models:
docker-compose restart app



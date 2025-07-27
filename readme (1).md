# Система скоринга потенциальных банкротов

Автоматизированная система для выявления перспективных клиентов по банкротству физических лиц.

## Возможности

- 🔍 Нормализация данных из различных CSV источников
- 🌐 Обогащение данными из внешних источников (ФССП, Федресурс, Росреестр, суды, налоговая)
- 📊 Расчет скоринга по алгоритму с настраиваемыми правилами
- 🖥️ Веб-интерфейс для запуска и мониторинга процессов
- 📈 Фильтрация и экспорт результатов в CSV
- 🔄 Устойчивость к сбоям внешних источников
- 🔍 Система прокси для обхода блокировок

## Технологический стек

- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **Frontend**: HTML/CSS/JS с Bootstrap 5
- **База данных**: PostgreSQL
- **Кэш**: Redis
- **Парсинг**: aiohttp, Playwright, BeautifulSoup
- **Контейнеризация**: Docker, Docker Compose

## Быстрый старт

### Запуск через Docker Compose (рекомендуется)

```bash
# Клонирование репозитория
git clone https://github.com/AlexAvdeev1986/bankruptcy_scoring.git
cd bankruptcy_scoring

# Создание .env файла
cp .env.example .env
# Отредактируйте .env согласно своим настройкам

# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f app
```

Система будет доступна по адресу: http://localhost

### Запуск через Podman

```bash
# Установка Podman (Fedora)
sudo dnf install podman podman-compose

# Замена docker-compose на podman-compose
sed -i 's/docker-compose/podman-compose/g' Makefile

# Запуск
podman-compose up -d
```

### Локальная разработка

#### Создание виртуального окружения

```bash
# Python 3.11 или выше
python3.11 -m venv bankruptcy_env

# Активация окружения
source bankruptcy_env/bin/activate  # Linux/Mac
# или
bankruptcy_env\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

#### Установка браузеров для Playwright

```bash
# Установка Chromium
playwright install chromium

# Или Firefox
playwright install firefox

# Установка системных зависимостей
playwright install-deps
```

#### Настройка базы данных

```bash
# Установка PostgreSQL (Fedora 42)
sudo dnf install postgresql postgresql-server postgresql-contrib

# Инициализация БД
sudo postgresql-setup --initdb

# Запуск сервиса
sudo systemctl enable --now postgresql

# Создание пользователя и БД
sudo -u postgres psql
CREATE USER bankruptcy_user WITH PASSWORD 'bankruptcy_password';
CREATE DATABASE bankruptcy_scoring OWNER bankruptcy_user;
GRANT ALL PRIVILEGES ON DATABASE bankruptcy_scoring TO bankruptcy_user;
\q
```

#### Настройка Redis

```bash
# Установка Redis (Fedora 42)
sudo dnf install redis

# Запуск сервиса
sudo systemctl enable --now redis
```

#### Настройка переменных окружения

```bash
# Создание .env файла
cp .env.example .env

# Редактирование конфигурации
nano .env
```

Пример `.env`:
```env
DATABASE_URL=postgresql://bankruptcy_user:bankruptcy_password@localhost:5432/bankruptcy_scoring
DATABASE_URL_SYNC=postgresql://bankruptcy_user:bankruptcy_password@localhost:5432/bankruptcy_scoring
REDIS_URL=redis://localhost:6379/0
DEBUG=True
USE_PROXY=True
```

#### Выполнение миграций

```bash
# Создание миграции
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

#### Запуск приложения

```bash
# Запуск веб-сервера
python run.py

# Или через uvicorn напрямую
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Установка на Fedora 42

### Системные зависимости

```bash
# Обновление системы
sudo dnf update -y

# Установка Python и зависимостей
sudo dnf install -y python3.11 python3.11-pip python3.11-venv \
                    postgresql postgresql-server postgresql-contrib \
                    redis git gcc gcc-c++ make \
                    libpq-devel python3.11-devel

# Установка Docker (опционально)
sudo dnf install -y docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

### Инициализация PostgreSQL

```bash
# Инициализация кластера БД
sudo postgresql-setup --initdb

# Настройка аутентификации
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /var/lib/pgsql/data/postgresql.conf
sudo sed -i "s/ident/md5/" /var/lib/pgsql/data/pg_hba.conf

# Запуск сервисов
sudo systemctl enable --now postgresql redis

# Создание БД и пользователя
sudo -u postgres createuser -P bankruptcy_user
sudo -u postgres createdb -O bankruptcy_user bankruptcy_scoring
```

### Настройка Playwright

```bash
# Активация окружения
source bankruptcy_env/bin/activate

# Установка браузеров
playwright install chromium firefox

# Установка системных зависимостей для браузеров
sudo playwright install-deps
```

### Настройка файрвола

```bash
# Открытие портов
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

## Миграции базы данных

### Инициализация Alembic

```bash
# Первоначальная настройка (уже сделано)
alembic init migrations

# Настройка alembic.ini
# sqlalchemy.url = postgresql://bankruptcy_user:bankruptcy_password@localhost:5432/bankruptcy_scoring
```

### Создание и применение миграций

```bash
# Создание новой миграции
alembic revision --autogenerate -m "Описание изменений"

# Просмотр текущей версии
alembic current

# Просмотр истории миграций
alembic history

# Применение всех миграций
alembic upgrade head

# Откат к предыдущей версии
alembic downgrade -1

# Откат к конкретной версии
alembic downgrade <revision_id>

# Применение конкретной миграции
alembic upgrade <revision_id>
```

### Создание
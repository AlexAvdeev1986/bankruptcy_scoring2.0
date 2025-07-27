# Bankruptcy Scoring System

Система для оценки потенциальных банкротов с возможностью обработки больших объемов данных (до 150 млн строк).

## 🚀 Возможности

- Пакетная обработка данных (батчи по 10,000 записей)
- Асинхронные запросы к внешним API (ФССП, Федресурс, Росреестр)
- Ротация прокси для обхода ограничений
- Автоматическое определение источника данных по имени файла
- Поддержка больших объемов данных (до 150 млн строк)
- Логирование ошибок в базу данных
- Экспорт результатов в CSV с потоковой выгрузкой
- Веб-интерфейс с отслеживанием прогресса в реальном времени

## 📋 Системные требования

- **Python:** 3.11+
- **PostgreSQL:** 15+
- **RAM:** минимум 8GB (рекомендуется 16GB для больших объемов данных)
- **Disk:** 50GB свободного места
- **OS:** Linux (рекомендуется), Windows, macOS

## 🐧 Установка на Fedora 42

### 1. Обновление системы
```bash
sudo dnf update -y
```

### 2. Установка зависимостей системы
```bash
# Установка Python 3.11 и инструментов разработки
sudo dnf install -y python3.11 python3.11-pip python3.11-venv python3.11-devel
sudo dnf install -y gcc gcc-c++ make git curl wget

# Установка PostgreSQL 15
sudo dnf install -y postgresql postgresql-server postgresql-contrib postgresql-devel
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Установка Podman (если не установлен)
sudo dnf install -y podman podman-compose

# Установка дополнительных пакетов для Playwright
sudo dnf install -y \
    alsa-lib-devel \
    at-spi2-atk-devel \
    atk-devel \
    cairo-devel \
    cups-devel \
    dbus-glib-devel \
    fontconfig-devel \
    gdk-pixbuf2-devel \
    glib2-devel \
    gtk3-devel \
    libdrm-devel \
    libX11-devel \
    libXcomposite-devel \
    libXdamage-devel \
    libXext-devel \
    libXfixes-devel \
    libXrandr-devel \
    libXScrnSaver-devel \
    libxkbcommon-devel \
    mesa-libgbm-devel \
    nspr-devel \
    nss-devel \
    pango-devel
```

### 3. Настройка PostgreSQL
```bash
# Переключение на пользователя postgres
sudo -u postgres psql

# В psql создание базы данных и пользователя
CREATE DATABASE bankruptcy_db;
CREATE USER bankruptcy_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE bankruptcy_db TO bankruptcy_user;
ALTER USER bankruptcy_user CREATEDB;
\q

# Настройка аутентификации PostgreSQL
sudo nano /var/lib/pgsql/data/pg_hba.conf
# Измените строку для local connections:
# local   all             all                                     peer
# на:
# local   all             all                                     md5

# Перезапуск PostgreSQL
sudo systemctl restart postgresql
```

## 🔧 Локальная установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/AlexAvdeev1986/bankruptcy_scoring.git
cd bankruptcy_scoring
```

### 2. Создание виртуального окружения

#### Для Linux/macOS:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

#### Для Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Установка Python зависимостей
```bash
# Обновление pip
pip install --upgrade pip

# Установка зависимостей
pip install -r requirements.txt

# Установка Playwright браузеров
playwright install

# Для Fedora - установка только нужного браузера
playwright install chromium
# ИЛИ
playwright install firefox
```

### 4. Создание конфигурационного файла
```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

Содержимое файла `.env`:
```bash
# База данных
DATABASE_URL=postgresql://bankruptcy_user:your_secure_password_here@localhost/bankruptcy_db

# Пути к данным
INPUT_DATA_PATH=./data/input
OUTPUT_DATA_PATH=./data/output
LOGS_PATH=./data/logs

# Настройки обработки
BATCH_SIZE=10000
MAX_WORKERS=4

# Настройки внешних API
FSSP_API_URL=https://api-ip.fssprus.ru
FEDRESURS_API_URL=https://fedresurs.ru/api
ROSREESTR_API_URL=https://rosreestr.ru/api

# Прокси настройки (опционально)
USE_PROXY=false
PROXY_LIST=[]

# Playwright настройки
BROWSER_TYPE=chromium
HEADLESS=true

# Настройки приложения
DEBUG=false
LOG_LEVEL=INFO
```

### 5. Создание структуры папок
```bash
mkdir -p data/input data/output data/logs
```

## 🗄️ Миграции базы данных

### 1. Инициализация Alembic
```bash
# Если миграции еще не инициализированы
alembic init migrations

# Если уже инициализированы, пропустите этот шаг
```

### 2. Создание первой миграции
```bash
# Создание миграции на основе моделей
alembic revision --autogenerate -m "Initial migration"
```

### 3. Применение миграций
```bash
# Применение всех миграций
alembic upgrade head

# Проверка текущей версии
alembic current

# Просмотр истории миграций
alembic history
```

### 4. Создание дополнительных миграций (при изменении моделей)
```bash
# После изменения моделей в app/models/
alembic revision --autogenerate -m "Add new fields to company model"
alembic upgrade head
```

### 5. Откат миграций (если нужно)
```bash
# Откат на одну версию назад
alembic downgrade -1

# Откат до конкретной версии
alembic downgrade <revision_id>

# Откат до начального состояния
alembic downgrade base
```

## 🚀 Запуск приложения

### Локальный запуск
```bash
# Активация виртуального окружения
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Запуск приложения
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Приложение будет доступно по адресу: http://localhost:8000
```

### Запуск в production режиме
```bash
# Без автоперезагрузки
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# С Gunicorn (рекомендуется для production)
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🐳 Запуск через Podman

### 1. Сборка образа
```bash
podman build -t bankruptcy-scoring .
```

### 2. Создание сети
```bash
podman network create scoring-network
```

### 3. Запуск PostgreSQL контейнера
```bash
podman run -d --name postgres-db \
  --network scoring-network \
  -e POSTGRES_DB=bankruptcy_db \
  -e POSTGRES_USER=bankruptcy_user \
  -e POSTGRES_PASSWORD=your_secure_password_here \
  -v postgres-data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15
```

### 4. Ожидание готовности базы данных
```bash
# Проверка готовности PostgreSQL
podman exec postgres-db pg_isready -U bankruptcy_user -d bankruptcy_db
```

### 5. Запуск приложения
```bash
podman run -d --name bankruptcy-app \
  --network scoring-network \
  -e DATABASE_URL=postgresql://bankruptcy_user:your_secure_password_here@postgres-db/bankruptcy_db \
  -v ./data:/app/data:Z \
  -v ./logs:/app/logs:Z \
  -p 8000:8000 \
  bankruptcy-scoring
```

### 6. Применение миграций в контейнере
```bash
# Выполнение миграций в контейнере
podman exec bankruptcy-app alembic upgrade head
```

### 7. Проверка логов
```bash
# Просмотр логов приложения
podman logs -f bankruptcy-app

# Просмотр логов базы данных
podman logs -f postgres-db
```

## 🐳 Запуск через Docker Compose

### 1. Создание docker-compose.yml (уже включен в проект)
```bash
# Запуск всех сервисов
docker-compose up --build -d

# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down

# Остановка с удалением volumes
docker-compose down -v
```

## 🎭 Настройка Playwright

### Выбор браузера для Fedora 42

#### Chromium (рекомендуется):
```bash
playwright install chromium

# Установка дополнительных системных зависимостей для Chromium
sudo dnf install -y \
    liberation-fonts \
    google-noto-emoji-fonts \
    chromium
```

#### Firefox:
```bash
playwright install firefox

# Установка Firefox системно (если нужно)
sudo dnf install -y firefox
```

#### Webkit (Safari engine):
```bash
playwright install webkit
```

### Настройка окружения для Playwright на Fedora
```bash
# Установка дополнительных шрифтов
sudo dnf install -y \
    dejavu-fonts-all \
    liberation-fonts \
    google-noto-fonts-common \
    google-noto-emoji-fonts

# Настройка переменных окружения для headless режима
export DISPLAY=:99
export PLAYWRIGHT_BROWSERS_PATH=/home/$USER/.cache/ms-playwright

# Для системного уровня (опционально)
echo 'export PLAYWRIGHT_BROWSERS_PATH=/home/$USER/.cache/ms-playwright' >> ~/.bashrc
source ~/.bashrc
```

### Тестирование Playwright
```bash
# Активация виртуального окружения
source venv/bin/activate

# Тестовый скрипт
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        print(f'Page title: {title}')
        await browser.close()

asyncio.run(test_browser())
"
```

## 📊 Использование системы

### 1. Подготовка данных
```bash
# Поместите CSV файлы в папку data/input/
# Поддерживаемые форматы полей:
# - name (название компании)
# - inn (ИНН)
# - kpp (КПП, опционально)
# - ogrn (ОГРН, опционально)
# - address (адрес)
# - region (регион)
# - debt_amount (сумма долга)
# - revenue (выручка, опционально)
```

### 2. Запуск обработки
1. Откройте браузер: http://localhost:8000
2. Настройте фильтры:
   - Выберите регионы
   - Укажите минимальную сумму долга
   - Настройте дополнительные параметры
3. Нажмите "Запустить скоринг"
4. Отслеживайте прогресс в реальном времени

### 3. Получение результатов
- Скачайте CSV файл с результатами
- Просмотрите статистику обработки
- Проверьте логи ошибок

## 🔧 Настройка производительности

### Оптимизация для больших данных
```bash
# В .env файле настройте:
BATCH_SIZE=10000          # Размер батча (уменьшите при недостатке RAM)
MAX_WORKERS=4             # Количество параллельных задач
DATABASE_POOL_SIZE=20     # Размер пула соединений с БД
```

### Настройка PostgreSQL для больших данных
```bash
sudo nano /var/lib/pgsql/data/postgresql.conf

# Рекомендуемые настройки:
shared_buffers = 2GB                    # 25% от RAM
work_mem = 256MB                        # Для сортировки
maintenance_work_mem = 1GB              # Для индексации
effective_cache_size = 6GB              # 75% от RAM
max_connections = 100
```

## 🐛 Диагностика проблем

### Проверка состояния системы
```bash
# Проверка PostgreSQL
sudo systemctl status postgresql
psql -U bankruptcy_user -d bankruptcy_db -c "SELECT version();"

# Проверка Python зависимостей
pip list | grep -E "(playwright|fastapi|sqlalchemy)"

# Проверка Playwright браузеров
playwright install --dry-run

# Тест подключения к базе данных
python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection: OK')
"
```

### Типичные проблемы и решения

#### 1. Ошибка подключения к PostgreSQL
```bash
# Проверка статуса службы
sudo systemctl status postgresql

# Перезапуск службы
sudo systemctl restart postgresql

# Проверка настроек аутентификации
sudo cat /var/lib/pgsql/data/pg_hba.conf
```

#### 2. Playwright не может запустить браузер
```bash
# Переустановка браузеров
playwright uninstall
playwright install chromium

# Проверка системных зависимостей
ldd ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome
```

#### 3. Недостаток памяти при обработке
```bash
# Уменьшение размера батча в .env
BATCH_SIZE=5000

# Мониторинг использования памяти
htop
# или
free -h
```

## 📝 Логирование и мониторинг

### Просмотр логов
```bash
# Логи приложения
tail -f data/logs/app.log

# Логи ошибок
tail -f data/logs/error.log

# Логи Podman контейнера
podman logs -f bankruptcy-app
```

### Мониторинг производительности
```bash
# Статистика базы данных
curl http://localhost:8000/api/stats

# Статистика внешних API
curl http://localhost:8000/api/api-stats

# Список загруженных файлов
curl http://localhost:8000/api/files
```

## 🔐 Безопасность

### Настройка файрвола (опционально)
```bash
# Открытие порта 8000 для приложения
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# Ограничение доступа только с локальной сети
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port protocol="tcp" port="8000" accept'
```

### Настройка SSL (для production)
```bash
# Установка certbot для Let's Encrypt
sudo dnf install -y certbot

# Получение сертификата
sudo certbot certonly --standalone -d your-domain.com

# Настройка nginx как reverse proxy
sudo dnf install -y nginx
```

## 📚 Дополнительные ресурсы

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи приложения в `data/logs/`
2. Убедитесь в правильности настроек в `.env`
3. Проверьте доступность внешних API
4. Создайте issue в репозитории с описанием проблемы
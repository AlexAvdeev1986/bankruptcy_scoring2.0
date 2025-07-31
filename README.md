# bankruptcy_scoring2.0
 bankruptcy_scoring2.0

bankruptcy_scoring/
├── app.py                      # Основное приложение
├── config.py                   # Конфигурация
├── data_processing/            # Обработка данных
│   ├── __init__.py
│   ├── data_loader.py          # Загрузка данных
│   ├── data_normalizer.py      # Нормализация данных
│   └── deduplicator.py         # Удаление дубликатов
├── enrichment/                 # Обогащение данных
│   ├── __init__.py
│   ├── enricher.py             # Основной класс обогащения
│   ├── fssp_service.py         # Сервис ФССП
│   ├── fedresurs_service.py    # Сервис Федресурс
│   ├── rosreestr_service.py    # Сервис Росреестра
│   ├── court_service.py        # Сервис судов
│   └── tax_service.py          # Сервис налоговой
├── scoring/                    # Расчет скоринга
│   ├── __init__.py
│   ├── rule_based_scorer.py    # Rule-based скоринг
│   └── ml_scorer.py            # ML-based скоринг
├── utils/                      # Вспомогательные утилиты
│   ├── __init__.py
│   ├── logger.py               # Логирование
│   ├── proxy_rotator.py        # Ротация прокси
│   └── file_utils.py           # Работа с файлами
├── templates/                  # Шаблоны HTML
│   ├── index.html              # Главная страница
│   └── logs.html               # Страница логов
├── static/                     # Статические файлы
│   └── styles.css              # CSS стили
├── requirements.txt            # Зависимости
├── Dockerfile                  # Для контейнеризации
└── README.md                   # Инструкции


7. Полный запуск на Fedora 42
# 1. Установка системных пакетов
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip python3.11-venv \
                    postgresql postgresql-server postgresql-contrib \
                    redis git gcc gcc-c++ make libpq-devel \
                    python3.11-devel nodejs npm

# 4. Клонирование и настройка проекта
git clone https://github.com/AlexAvdeev1986/bankruptcy_scoring2.0.git
cd bankruptcy_scoring

# 5. Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# 6. Установка зависимостей
pip install -r requirements.txt
playwright install chromium firefox
playwright install-deps

# 2. Настройка PostgreSQL
sudo -u postgres psql

```bash
CREATE USER user WITH PASSWORD 'password';
CREATE DATABASE bankruptcy_db;
GRANT ALL PRIVILEGES ON DATABASE bankruptcy_db TO user;
GRANT ALL PRIVILEGES ON SCHEMA public TO "user";
GRANT CREATE ON SCHEMA public TO "user";
GRANT USAGE ON SCHEMA public TO "user";
REVOKE ALL ON SCHEMA public FROM "user";
GRANT ALL ON SCHEMA public TO "user";
CREATE TABLE test_table(id INT);
```
Проверьте, что нет ограничений на уровне таблиц:```
```bash
\dn+ public
```

Для fedora
sudo dnf install -y postgresql-devel python3-devel
pip install psycopg2-binary
4. Проверка установки
python3 -c "import psycopg2; print(psycopg2.__version__)"
# 3. Настройка Redis
sudo systemctl enable --now redis

# 7. Настройка конфигурации
cp .env.example .env
# Отредактируйте .env

# 8. Выполнение миграций
alembic upgrade head

# Рекомендации по запуску:
Установите зависимости:

bash
pip install -r requirements.txt
Запустите веб-приложение:

bash
python app.py
Откройте в браузере:

text
http://localhost:5000
Для обучения ML-модели:

bash
python ml_model/train.py

Для Fedora 42 может потребоваться установка дополнительных зависимостей:

bash
sudo dnf install gcc python3-devel postgresql-devel

Инструкции по запуску
1. Настройка PostgreSQL на Fedora
# Установка PostgreSQL
sudo dnf install postgresql-server postgresql-contrib

# Инициализация БД
sudo postgresql-setup --initdb

# Запуск службы
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Настройка пользователя и базы данных
sudo -u postgres psql <<EOF
CREATE USER "user" WITH PASSWORD 'password';
CREATE DATABASE bankruptcy_db;
GRANT ALL PRIVILEGES ON DATABASE bankruptcy_db TO "user";
ALTER DATABASE bankruptcy_db OWNER TO "user";
GRANT ALL ON SCHEMA public TO "user";
EOF

# Настройка аутентификации
sudo nano /var/lib/pgsql/data/pg_hba.conf

# Изменить строки:
# local   all             all                                     trust
# host    all             all             127.0.0.1/32            trust
# host    all             all             ::1/128                 trust

# Перезапуск PostgreSQL
sudo systemctl restart postgresql

2. Запуск локально (с виртуальным окружением)
# Установка Python и зависимостей
sudo dnf install python3.11 python3.11-venv

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
cp .env.example .env
nano .env  # Редактируем параметры

# Инициализация базы данных
python scripts/init_db.py

# Запуск миграций
python scripts/run_migrations.py

# Обучение ML-модели (опционально)
python ml_model/train.py

# Запуск приложения
python app.py

Приложение будет доступно по адресу: http://localhost:5000

3. Запуск через Podman

# Установка Podman
sudo dnf install podman

# Сборка образа
podman build -t bankruptcy-scoring .

# Создание сети
podman network create scoring-network

# Запуск PostgreSQL
podman run -d --name scoring-db \
  --network scoring-network \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=bankruptcy_db \
  -v pgdata:/var/lib/postgresql/data \
  docker.io/postgres:14

# Запуск приложения
podman run -d --name scoring-app \
  --network scoring-network \
  -p 5000:5000 \
  -e DB_HOST=scoring-db \
  -e DB_NAME=bankruptcy_db \
  -e DB_USER=user \
  -e DB_PASSWORD=password \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  localhost/bankruptcy-scoring

# Проверка работы
podman logs scoring-app

5. Инициализация базы данных
bash
# Для локального запуска
python scripts/init_db.py

# Для Docker/Podman
podman exec scoring-app python scripts/init_db.py

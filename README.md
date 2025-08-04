# bankruptcy_scoring2.0
 bankruptcy_scoring2.0

bankruptcy_scoring/
├── app.py                      # Основное приложение
├── config.py                   # Конфигурация
├── database/                   # Работа с базой данных
│   ├── database.py
│   └── migrations/
│       ├── 001_initial.sql
│       └── 002_add_ml_features.sql
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
├── ml_model/                   # Модели машинного обучения
│   ├── model.pkl               # Обученная модель
│   ├── train.py                # Обучение модели
│   └── predict.py              # Прогнозирование
├── templates/                  # Шаблоны HTML
│   ├── index.html              # Главная страница
│   └── logs.html               # Страница логов
├── static/                     # Статические файлы
│   └── styles.css              # CSS стили
└── scripts/                    # Скрипты для управления
    ├── init_db.py
    └── run_migrations.py
├── requirements.txt            # Зависимости
├── Dockerfile                  # Для контейнеризации
├── docker-compose.yml          # Для запуска с PostgreSQL
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

sudo -u postgres createdb bankruptcy_db

# Создайте необходимые директории
mkdir -p database/migrations
mkdir -p data/uploads data/results logs/errors


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

# Настройка аутентификации
sudo nano /var/lib/pgsql/data/pg_hba.conf

# Изменить строки:
# "local" is for Unix domain socket connections only
local   all             postgres                                peer
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
host    all             all             0.0.0.0/0               md5
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5

# Перезапуск PostgreSQL
sudo systemctl restart postgresql


# Установите пароль для пользователя postgres
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'secure_password';"

# Настройка пользователя и базы данных

sudo -u postgres psql <<EOF
CREATE USER scoring_user WITH PASSWORD 'secure_password';
CREATE DATABASE bankruptcy_scoring;
GRANT ALL PRIVILEGES ON DATABASE bankruptcy_scoring TO scoring_user;
ALTER DATABASE bankruptcy_scoring OWNER TO scoring_user;
GRANT ALL ON SCHEMA public TO scoring_user;
EOF


Проверка прав доступа:

sudo -u postgres psql -d bankruptcy_db -c "\dn+ public"

# Удаление существующей базы (если она не нужна):
sudo -u postgres psql -c "DROP DATABASE bankruptcy_db;"

sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS bankruptcy_db;
DROP USER IF EXISTS "user";
EOF

# Перезапуск PostgreSQL
sudo systemctl restart postgresql

# Проверка работы базы данных:
psql -h localhost -U scoring_user -d bankruptcy_db -c "SELECT * FROM leads LIMIT 5;"

python -m scripts.run_migrations


# Инициализация базы данных
python scripts/init_db.py

# Запуск миграций
python scripts/run_migrations.py

# Обучение ML-модели (опционально)
python ml_model/train.py

# Запуск приложения
python app.py

Приложение будет доступно по адресу: http://localhost:5000


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
ALTER SCHEMA public OWNER TO postgres;
DROP USER "user";
CREATE TABLE test_table(id INT);
```
Проверьте, что нет ограничений на уровне таблиц:```
```bash
sudo -u postgres psql -d bankruptcy_db -c "\dn+ public"```
```

Для fedora
sudo dnf install -y postgresql-devel python3-devel
pip install psycopg2-binary

Установите необходимые зависимости:
sudo dnf install python3.11 python3.11-venv postgresql-server postgresql-contrib podman podman-compose

4. Проверка установки
python3 -c "import psycopg2; print(psycopg2.__version__)"
# 3. Настройка Redis
sudo systemctl enable --now redis

# 7. Настройка конфигурации
cp .env.example .env
# Отредактируйте .env





3. Запуск через Podman

# Установка Podman
sudo dnf install podman podman-compose

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


Запуск системы
Настройка окружения:

bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Создание .env файла:

env
DB_NAME=bankruptcy_db
DB_USER=user
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
SECRET_KEY=secret
UPLOAD_FOLDER=./data/uploads
RESULT_FOLDER=./data/results
ERROR_LOG_FOLDER=./logs/errors
LOG_FILE=./logs/app.log
PROXY_LIST="http://proxy1:port,http://proxy2:port"
Инициализация БД:

bash
python scripts/init_db.py
Запуск миграций:

bash
python scripts/run_migrations.py
Обучение модели (опционально):

bash
python ml_model/train.py
Запуск приложения:

bash
python app.py
Система будет доступна по адресу: http://localhost:5000

Запуск через Podman
bash
# Сборка образа
podman build -t bankruptcy-scoring .

# Запуск с PostgreSQL
podman-compose up
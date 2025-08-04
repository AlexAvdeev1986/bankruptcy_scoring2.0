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

graph TD
    A[Веб-интерфейс] --> B[Загрузка CSV]
    B --> C[Нормализация данных]
    C --> D[Дедупликация]
    D --> E[Обогащение данных]
    E --> F[Скоринг]
    F --> G[Сохранение в БД]
    G --> H[Выгрузка результатов]
    
    subgraph Обогащение
        E1[ФССП] --> E
        E2[Федресурс] --> E
        E3[Росреестр] --> E
        E4[Суды] --> E
        E5[Налоговая] --> E
    end
    
    subgraph Скоринг
        F1[Rule-Based] --> F
        F2[ML Model] --> F
    end
    
    H --> I[Скачивание CSV]
    G --> J[Статистика]
    G --> K[Логи ошибок]


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


# Перейдите в режим администратора PostgreSQL:

bash
sudo -u postgres psql
В интерактивном режиме psql выполните:

sql
ALTER USER scoring_user WITH PASSWORD 'new_password';

# Настройка пользователя и базы данных

sudo -u postgres psql <<EOF
CREATE USER scoring_user WITH PASSWORD 'secure_password';
CREATE DATABASE bankruptcy_scoring;
GRANT ALL PRIVILEGES ON DATABASE bankruptcy_scoring TO scoring_user;
ALTER DATABASE bankruptcy_scoring OWNER TO scoring_user;
GRANT ALL ON SCHEMA public TO scoring_user;
EOF

# Перезапуск PostgreSQL
sudo systemctl restart postgresql
Проверка прав доступа:

sudo -u postgres psql -d bankruptcy_db -c "\dn+ public"

# (если нужно) Удаление существующей базы (если нужно):
sudo -u postgres psql -c "DROP DATABASE bankruptcy_db;"

sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS bankruptcy_db;
DROP USER IF EXISTS "user";
EOF

# Применение миграций вручную
Шаг 1: Применение начальной миграции (001_initial.sql)
bash
sudo -u postgres psql -d bankruptcy_scoring -f database/migrations/001_initial.sql
Шаг 2: Применение миграции для ML-фич (002_add_ml_features.sql)
bash
sudo -u postgres psql -d bankruptcy_scoring -f database/migrations/002_add_ml_features.sql
Шаг 3: Проверка созданных таблиц
bash
sudo -u postgres psql -d bankruptcy_scoring -c "\dt"

Теперь вы должны увидеть:

text
           List of relations
 Schema |     Name      | Type  |    Owner    
--------+---------------+-------+-------------
 public | error_logs    | table | scoring_user
 public | leads         | table | scoring_user
 public | scoring_history | table | scoring_user

Проверка прав доступа
Убедимся, что пользователь scoring_user имеет права на таблицы:

bash
sudo -u postgres psql -d bankruptcy_scoring -c "
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scoring_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scoring_user;
"

Проверка данных в БД:

sudo -u postgres psql -d bankruptcy_scoring -c "SELECT * FROM scoring_history;"


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


# Важные директории проекта
Директория	Назначение
data/uploads/	Загружаем CSV-файлы
data/results/	Результаты скоринга (CSV)
logs/errors/	Логи ошибок
ml_model/	ML-модели
database/migrations/	SQL-скрипты миграций

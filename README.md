# bankruptcy_scoring2.0
 bankruptcy_scoring2.0

bankruptcy_scoring/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI приложение
│   ├── config.py              # Конфигурация
│   ├── database.py            # База данных
│   ├── models.py              # SQLAlchemy модели
│   ├── schemas.py             # Pydantic схемы
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py       # API эндпоинты
│   ├── core/
│   │   ├── __init__.py
│   │   ├── normalization.py   # Нормализация данных
│   │   ├── scoring.py         # Логика скоринга
│   │   └── enrichment.py      # Обогащение данными
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py           # Базовый парсер
│   │   ├── fssp.py           # ФССП парсер
│   │   ├── fedresurs.py      # Федресурс парсер
│   │   ├── rosreestr.py      # Росреестр парсер
│   │   ├── courts.py         # Суды парсер
│   │   └── nalog.py          # Налоговая парсер
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── proxy.py          # Управление прокси
│   │   ├── logger.py         # Логирование
│   │   └── validators.py     # Валидация данных
│   └── templates/
│       ├── index.html        # Главная страница
│       └── logs.html         # Страница логов
├── data/
│   ├── input/                # Входящие CSV файлы
│   ├── output/               # Результаты скоринга
│   └── logs/                 # Логи
├── migrations/               # Миграции базы данных
├── tests/                   # Тесты
├── docker-compose.yml       # Docker композ
├── Dockerfile              # Docker образ
├── requirements.txt        # Зависимости Python
├── README.md              # Документация
├── .env.example           # Пример конфигурации
└── run.py                 # Точка входа


7. Полный запуск на Fedora 42
# 1. Установка системных пакетов
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip python3.11-venv \
                    postgresql postgresql-server postgresql-contrib \
                    redis git gcc gcc-c++ make libpq-devel \
                    python3.11-devel nodejs npm

# 2. Настройка PostgreSQL
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo -u postgres createuser -P bankruptcy_user
sudo -u postgres createdb -O bankruptcy_user bankruptcy_scoring2.0

# 3. Настройка Redis
sudo systemctl enable --now redis

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

# 7. Настройка конфигурации
cp .env.example .env
# Отредактируйте .env

# 8. Выполнение миграций
alembic upgrade head

# 9. Запуск
python run.py
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

# 9. Запуск
python run.py
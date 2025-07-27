# Подробное руководство по миграциям базы данных

## 🗄️ Настройка Alembic

### 1. Инициализация Alembic (первый запуск)

```bash
# Переход в корневую папку проекта
cd bankruptcy_scoring

# Активация виртуального окружения
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Инициализация Alembic
alembic init migrations
```

### 2. Конфигурация alembic.ini

Создайте или отредактируйте файл `alembic.ini`:

```ini
# alembic.ini
[alembic]
# Путь к папке с миграциями
script_location = migrations

# Шаблон для создания файлов миграций
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# Настройки подключения к базе данных
# sqlalchemy.url будет взят из переменной окружения или env.py

# Настройки логирования
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_
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

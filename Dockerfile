FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
RUN apt-get update && \
    apt-get install -y gcc libpq-dev && \
    apt-get clean

# Копирование зависимостей и установка
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p /app/data/uploads /app/data/results /app/logs/errors

# Запуск приложения
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]

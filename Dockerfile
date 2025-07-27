FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    unzip \
    git \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка Node.js для Playwright
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузеров для Playwright
RUN playwright install chromium firefox
RUN playwright install-deps

# Копирование исходного кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p data/input data/output data/logs

# Создание пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Экспорт порта
EXPOSE 8000

# Команда запуска
CMD ["python", "run.py"]
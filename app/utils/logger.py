import logging
import logging.handlers
import os
from typing import Optional
from app.config import settings

def setup_logging() -> None:
    """Настройка системы логирования"""
    
    # Создаем директорию для логов если не существует
    os.makedirs(settings.LOGS_DIR, exist_ok=True)
    
    # Основной лог файл
    log_file = os.path.join(settings.LOGS_DIR, "app.log")
    
    # Настройка форматирования
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Удаляем существующие хендлеры
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Файловый хендлер с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Отдельный лог для ошибок
    error_log_file = os.path.join(settings.LOGS_DIR, "errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Настройка логгеров библиотек
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Логгер для парсеров
    parser_log_file = os.path.join(settings.LOGS_DIR, "parsers.log")
    parser_handler = logging.handlers.RotatingFileHandler(
        parser_log_file,
        maxBytes=20*1024*1024,  # 20MB
        backupCount=5,
        encoding='utf-8'
    )
    parser_handler.setFormatter(formatter)
    
    parser_logger = logging.getLogger("parsers")
    parser_logger.addHandler(parser_handler)
    parser_logger.setLevel(logging.DEBUG)

def get_logger(name: str) -> logging.Logger:
    """Получение логгера по имени"""
    return logging.getLogger(name)

# Инициализация при импорте
setup_logging()
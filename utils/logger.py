# utils/logger.py
import logging
import sys
import os
from datetime import datetime

def setup_logger(name: str = "bankruptcy_scoring", log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Настройка логгера приложения
    
    :param name: Имя логгера
    :param log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param log_dir: Директория для сохранения логов
    :return: Объект логгера
    """
    # Создаем директорию для логов, если её нет
    os.makedirs(log_dir, exist_ok=True)
    
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик (ротация по дням)
    log_file = os.path.join(
        log_dir, 
        f"bankruptcy_scoring_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Пример использования
if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Тест логгера: успешно!")
    logger.error("Тест ошибки")
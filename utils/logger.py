import logging
import sys
import os
from datetime import datetime

def setup_logger(name: str = "bankruptcy_scoring", 
                log_level: str = "INFO", 
                log_file: str = None) -> logging.Logger:
    """
    Настройка логгера приложения
    
    :param name: Имя логгера
    :param log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param log_file: Полный путь к файлу лога (опционально)
    :return: Объект логгера
    """
    # Создаем логгер
    logger = logging.getLogger(name)
    
    try:
        # Преобразуем строковый уровень в числовой
        level = getattr(logging, log_level.upper())
        logger.setLevel(level)
    except AttributeError:
        logger.setLevel(logging.INFO)
        logger.warning(f"Неизвестный уровень логирования: {log_level}. Используется INFO")
    
    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик (если указан файл)
    if log_file:
        try:
            # Создаем директорию, если её нет
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"Файловый логгер настроен: {log_file}")
        except Exception as e:
            logger.error(f"Ошибка настройки файлового логгера: {str(e)}")
    
    return logger

# Пример использования
if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Тест логгера: успешно!")
    logger.error("Тест ошибки")
    
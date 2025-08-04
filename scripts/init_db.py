# scripts/init_db.py
import os
import sys
import logging
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DBInitializer')

def main():
    try:
        # Загрузка переменных окружения
        load_dotenv()
        
        # Импорт модуля базы данных после настройки пути
        from database.database import db_instance
        
        logger.info("Инициализация подключения к БД")
        db_instance.initialize()
        
        logger.info("Создание структуры БД")
        db_instance.initialize_db()
        
        logger.info("База данных успешно инициализирована")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
    
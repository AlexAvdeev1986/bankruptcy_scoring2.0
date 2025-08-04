import os
import logging
import psycopg2
from psycopg2 import sql

# Добавляем путь к проекту
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database import db_instance

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('Migrations')
    
    # Инициализация подключения к БД
    db_instance.initialize()
    
    # Путь к директории с миграциями
    migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations')
    
    # Получение списка файлов миграций
    migrations = sorted(
        [f for f in os.listdir(migrations_dir) if f.endswith('.sql')],
        key=lambda x: int(x.split('_')[0])
    )
    
    logger.info(f"Найдено {len(migrations)} миграций")
    
    # Применение миграций с обработкой ошибок
    for migration in migrations:
        migration_path = os.path.join(migrations_dir, migration)
        logger.info(f"Применение миграции: {migration}")
        
        try:
            with open(migration_path, 'r') as f:
                sql_script = f.read()
            
            with db_instance.conn.cursor() as cursor:
                try:
                    cursor.execute(sql_script)
                    db_instance.conn.commit()
                    logger.info(f"Миграция {migration} успешно применена")
                except psycopg2.errors.DuplicateTable as e:
                    db_instance.conn.rollback()
                    logger.warning(f"Таблица уже существует: {migration}. Пропускаем.")
                except psycopg2.errors.DuplicateObject as e:
                    db_instance.conn.rollback()
                    logger.warning(f"Объект уже существует: {migration}. Пропускаем.")
                except Exception as e:
                    db_instance.conn.rollback()
                    logger.error(f"Ошибка применения миграции {migration}: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Ошибка чтения миграции {migration}: {str(e)}")
            raise

if __name__ == '__main__':
    main()
    
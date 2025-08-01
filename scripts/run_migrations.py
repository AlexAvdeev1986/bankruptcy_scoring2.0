import os
import logging
from database.database import db_instance

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('Migrations')
    
    # Путь к директории с миграциями
    migrations_dir = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations')
    
    # Получение списка файлов миграций
    migrations = sorted(
        [f for f in os.listdir(migrations_dir) if f.endswith('.sql')],
        key=lambda x: int(x.split('_')[0])
    )
    
    logger.info(f"Найдено {len(migrations)} миграций")
    
    # Применение миграций
    for migration in migrations:
        migration_path = os.path.join(migrations_dir, migration)
        logger.info(f"Применение миграции: {migration}")
        try:
            db_instance.execute_script(migration_path)
            logger.info(f"Миграция {migration} успешно применена")
        except Exception as e:
            logger.error(f"Ошибка применения миграции {migration}: {str(e)}")
            raise

if __name__ == '__main__':
    main()
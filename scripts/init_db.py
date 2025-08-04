import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DBInitializer')

def main():
    # Добавляем путь к проекту для корректного импорта модулей
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(project_root)
    
    load_dotenv()  # Загрузка переменных окружения
    
    # Параметры подключения из .env
    admin_params = {
        'dbname': 'postgres',
        'user': os.getenv('DB_ADMIN_USER', 'postgres'),
        'password': os.getenv('DB_ADMIN_PASSWORD', 'secure_password'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432')
    }
    
    app_db_name = os.getenv('DB_NAME', 'bankruptcy_scoring')
    app_user = os.getenv('DB_USER', 'scoring_user')
    app_password = os.getenv('DB_PASSWORD', 'secure_password')
    
    try:
        # Подключение к БД с правами администратора
        with psycopg2.connect(**admin_params) as admin_conn:
            admin_conn.autocommit = True
            with admin_conn.cursor() as cursor:
                # 1. Создание пользователя (если не существует)
                cursor.execute(
                    sql.SQL("SELECT 1 FROM pg_roles WHERE rolname = {}")
                    .format(sql.Literal(app_user)))
                if not cursor.fetchone():
                    cursor.execute(
                        sql.SQL("CREATE USER {} WITH PASSWORD {}")
                        .format(sql.Identifier(app_user), 
                                sql.Literal(app_password)))
                    logger.info(f"Создан пользователь БД: {app_user}")
                else:
                    logger.info(f"Пользователь {app_user} уже существует")
                
                # 2. Создание базы данных (если не существует)
                cursor.execute(
                    sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}")
                    .format(sql.Literal(app_db_name)))
                if not cursor.fetchone():
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {}")
                        .format(sql.Identifier(app_db_name),
                                sql.Identifier(app_user)))
                    logger.info(f"Создана БД: {app_db_name}")
                else:
                    # Если БД уже существует, назначаем владельца
                    cursor.execute(
                        sql.SQL("ALTER DATABASE {} OWNER TO {}")
                        .format(sql.Identifier(app_db_name),
                                sql.Identifier(app_user)))
                    logger.info(f"Обновлен владелец БД: {app_db_name} -> {app_user}")
        
        # 3. Подключение к приложению как администратор для назначения прав
        app_params = admin_params.copy()
        app_params['dbname'] = app_db_name
        with psycopg2.connect(**app_params) as app_conn:
            app_conn.autocommit = True
            with app_conn.cursor() as cursor:
                # Даем пользователю все права на схему public
                cursor.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON SCHEMA public TO {}")
                    .format(sql.Identifier(app_user)))
                
                # Для всех существующих таблиц меняем владельца
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(
                            sql.SQL("ALTER TABLE {} OWNER TO {}")
                            .format(sql.Identifier(table),
                                    sql.Identifier(app_user)))
                        logger.info(f"Изменен владелец таблицы {table} -> {app_user}")
                    except Exception as e:
                        logger.warning(f"Ошибка изменения владельца таблицы {table}: {str(e)}")
                
                # Для всех существующих последовательностей меняем владельца
                cursor.execute("""
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_schema = 'public'
                """)
                sequences = [row[0] for row in cursor.fetchall()]
                
                for sequence in sequences:
                    try:
                        cursor.execute(
                            sql.SQL("ALTER SEQUENCE {} OWNER TO {}")
                            .format(sql.Identifier(sequence),
                                    sql.Identifier(app_user)))
                        logger.info(f"Изменен владелец последовательности {sequence} -> {app_user}")
                    except Exception as e:
                        logger.warning(f"Ошибка изменения владельца последовательности {sequence}: {str(e)}")
                
                # Даем права на все таблицы
                cursor.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {}")
                    .format(sql.Identifier(app_user)))
                
                # Даем права на все последовательности
                cursor.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {}")
                    .format(sql.Identifier(app_user)))
                
                # Устанавливаем права по умолчанию
                cursor.execute(
                    sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO {}")
                    .format(sql.Identifier(app_user)))
                
                cursor.execute(
                    sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO {}")
                    .format(sql.Identifier(app_user)))
                
                logger.info(f"Права пользователя {app_user} установлены")
        
        # 4. Теперь инициализируем структуру БД через приложение
        from database.database import db_instance
        
        # Используем учетные данные приложения
        os.environ['DB_USER'] = app_user
        os.environ['DB_PASSWORD'] = app_password
        
        db_instance.initialize()
        db_instance.initialize_db()
        logger.info("База данных успешно инициализирована")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
    
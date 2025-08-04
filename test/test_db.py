import os
import psycopg2
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

def test_connection():
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'bankruptcy_scoring'),
            user=os.getenv('DB_USER', 'scoring_user'),
            password=os.getenv('DB_PASSWORD', 'secure_password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        
        # Выполняем тестовый запрос
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS test")
            result = cursor.fetchone()
            print("Database connection test:", result)
            return True
    except Exception as e:
        print("Database connection failed:", str(e))
        return False
    finally:
        # Закрываем соединение
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if test_connection():
        print("Database connection successful!")
    else:
        print("Database connection failed!")
        
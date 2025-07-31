import os
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.conn = None
        self.logger = logging.getLogger('Database')
        self.connect()
        self.initialize_db()

    def connect(self):
        """Установка соединения с БД"""
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'bankruptcy_scoring'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432')
            )
            self.logger.info("Успешное подключение к БД")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к БД: {str(e)}")
            raise

    def initialize_db(self):
        """Инициализация структуры БД"""
        try:
            with self.conn.cursor() as cursor:
                # Таблица лидов
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS leads (
                        lead_id SERIAL PRIMARY KEY,
                        fio VARCHAR(255) NOT NULL,
                        phone VARCHAR(20) NOT NULL,
                        inn VARCHAR(12),
                        dob DATE,
                        address TEXT,
                        source VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tags VARCHAR(50),
                        email VARCHAR(100),
                        normalized BOOLEAN DEFAULT FALSE
                    );
                """)
                
                # Таблица истории скоринга
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scoring_history (
                        history_id SERIAL PRIMARY KEY,
                        lead_id INTEGER REFERENCES leads(lead_id),
                        scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        score INTEGER NOT NULL,
                        group_name VARCHAR(50) NOT NULL,
                        reason_1 TEXT,
                        reason_2 TEXT,
                        reason_3 TEXT
                    );
                """)
                
                # Таблица ошибок
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS error_logs (
                        error_id SERIAL PRIMARY KEY,
                        fio VARCHAR(255),
                        inn VARCHAR(12),
                        error TEXT NOT NULL,
                        service VARCHAR(50) NOT NULL,
                        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Индексы для ускорения поиска
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_inn ON leads(inn);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_lead ON scoring_history(lead_id);")
                
            self.conn.commit()
            self.logger.info("База данных инициализирована")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка инициализации БД: {str(e)}")
            raise

    def save_leads(self, leads: list):
        """Сохранение нормализованных лидов в БД"""
        try:
            with self.conn.cursor() as cursor:
                for lead in leads:
                    cursor.execute("""
                        INSERT INTO leads (
                            fio, phone, inn, dob, address, source, tags, email, normalized
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        ON CONFLICT (phone, inn) DO NOTHING;
                    """, (
                        lead.get('fio'),
                        lead.get('phone'),
                        lead.get('inn'),
                        lead.get('dob'),
                        lead.get('address'),
                        lead.get('source'),
                        lead.get('tags'),
                        lead.get('email')
                    ))
            self.conn.commit()
            self.logger.info(f"Сохранено {len(leads)} лидов в БД")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка сохранения лидов: {str(e)}")
            raise

    def save_scoring_history(self, scoring_results: list):
        """Сохранение результатов скоринга"""
        try:
            with self.conn.cursor() as cursor:
                for result in scoring_results:
                    # Находим lead_id по телефону
                    cursor.execute("""
                        SELECT lead_id FROM leads WHERE phone = %s LIMIT 1;
                    """, (result['phone'],))
                    lead_row = cursor.fetchone()
                    
                    if lead_row:
                        lead_id = lead_row[0]
                        cursor.execute("""
                            INSERT INTO scoring_history (
                                lead_id, score, group_name, reason_1, reason_2, reason_3
                            ) VALUES (%s, %s, %s, %s, %s, %s);
                        """, (
                            lead_id,
                            result['score'],
                            result['group'],
                            result['reason_1'],
                            result['reason_2'],
                            result['reason_3']
                        ))
            self.conn.commit()
            self.logger.info(f"Сохранено {len(scoring_results)} записей истории скоринга")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка сохранения истории скоринга: {str(e)}")
            raise

    def save_error_log(self, error: dict, service: str):
        """Сохранение ошибки в лог"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO error_logs (
                        fio, inn, error, service
                    ) VALUES (%s, %s, %s, %s);
                """, (
                    error.get('fio'),
                    error.get('inn'),
                    error.get('error'),
                    service
                ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения лога: {str(e)}")

    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
            self.logger.info("Соединение с БД закрыто")

# Синглтон для доступа к БД
db_instance = Database()
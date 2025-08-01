import os
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
import json

load_dotenv()

class Database:
    def __init__(self):
        self.conn = None
        self.logger = logging.getLogger('Database')
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT')
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
                
                # Индексы
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_inn ON leads(inn);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_lead ON scoring_history(lead_id);")
                
            self.conn.commit()
            self.logger.info("База данных инициализирована")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка инициализации БД: {str(e)}")
            raise

    def save_leads(self, leads):
        """Сохранение лидов в базу данных"""
        try:
            with self.conn.cursor() as cursor:
                for lead in leads:
                    cursor.execute("""
                        INSERT INTO leads (
                            fio, phone, inn, dob, address, source, tags, email, normalized
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        ON CONFLICT (phone) DO NOTHING;
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
    
    def save_scoring_history(self, results):
        """Сохранение результатов скоринга в историю"""
        try:
            with self.conn.cursor() as cursor:
                for result in results:
                    # Находим lead_id по телефону
                    cursor.execute("SELECT lead_id FROM leads WHERE phone = %s", (result['phone'],))
                    lead_row = cursor.fetchone()
                    lead_id = lead_row[0] if lead_row else None
                    
                    if lead_id:
                        cursor.execute("""
                            INSERT INTO scoring_history (
                                lead_id, score, group_name, reason_1, reason_2, reason_3
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            lead_id,
                            result['score'],
                            result['group'],
                            result['reason_1'],
                            result['reason_2'],
                            result['reason_3']
                        ))
            self.conn.commit()
            self.logger.info(f"Сохранено {len(results)} записей в историю скоринга")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка сохранения истории: {str(e)}")
            raise
    
    def save_error_log(self, error, service):
        """Сохранение ошибки в лог"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO error_logs (fio, inn, error, service)
                    VALUES (%s, %s, %s, %s)
                """, (
                    error.get('fio'),
                    error.get('inn'),
                    error.get('error'),
                    service
                ))
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения лога: {str(e)}")
    
    def get_recent_errors(self, limit=20):
        """Получение последних ошибок"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT fio, inn, error, service, occurred_at
                    FROM error_logs
                    ORDER BY occurred_at DESC
                    LIMIT %s
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Ошибка получения ошибок: {str(e)}")
            return []
    
    def get_group_stats(self):
        """Статистика по группам"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT group_name, COUNT(*) as count
                    FROM scoring_history
                    WHERE scored_at > CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY group_name
                """)
                return [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {str(e)}")
            return []

# Синглтон для доступа к БД
db_instance = Database()
import os
import logging
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor, execute_values
from datetime import datetime
from dotenv import load_dotenv

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        self.conn = None
        self.logger = logging.getLogger('Database')
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'bankruptcy_scoring'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'secure_password'),
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
                        phone VARCHAR(20) NOT NULL UNIQUE,
                        inn VARCHAR(12),
                        dob DATE,
                        address TEXT,
                        source VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tags VARCHAR(50),
                        email VARCHAR(100),
                        debt_amount NUMERIC DEFAULT 0,
                        debt_count INTEGER DEFAULT 0,
                        has_property BOOLEAN DEFAULT FALSE,
                        has_court_order BOOLEAN DEFAULT FALSE,
                        is_inn_active BOOLEAN DEFAULT TRUE,
                        is_bankrupt BOOLEAN DEFAULT FALSE,
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_scored_at ON scoring_history(scored_at);")
            
            self.conn.commit()
            self.logger.info("База данных инициализирована")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка инициализации БД: {str(e)}")
            raise

    def save_leads(self, leads):
        """Сохранение лидов в базу данных"""
        if not leads:
            return
            
        try:
            with self.conn.cursor() as cursor:
                data = [(
                    lead.get('fio'),
                    lead.get('phone'),
                    lead.get('inn'),
                    lead.get('dob'),
                    lead.get('address'),
                    lead.get('source'),
                    lead.get('tags'),
                    lead.get('email'),
                    lead.get('debt_amount', 0),
                    lead.get('debt_count', 0),
                    lead.get('has_property', False),
                    lead.get('has_court_order', False),
                    lead.get('is_inn_active', True),
                    lead.get('is_bankrupt', False),
                    True
                ) for lead in leads]
                
                query = """
                    INSERT INTO leads (
                        fio, phone, inn, dob, address, source, tags, email, 
                        debt_amount, debt_count, has_property, has_court_order, 
                        is_inn_active, is_bankrupt, normalized
                    ) VALUES %s
                    ON CONFLICT (phone) DO UPDATE SET
                        fio = EXCLUDED.fio,
                        inn = EXCLUDED.inn,
                        dob = EXCLUDED.dob,
                        address = EXCLUDED.address,
                        source = EXCLUDED.source,
                        tags = EXCLUDED.tags,
                        email = EXCLUDED.email,
                        debt_amount = EXCLUDED.debt_amount,
                        debt_count = EXCLUDED.debt_count,
                        has_property = EXCLUDED.has_property,
                        has_court_order = EXCLUDED.has_court_order,
                        is_inn_active = EXCLUDED.is_inn_active,
                        is_bankrupt = EXCLUDED.is_bankrupt,
                        normalized = EXCLUDED.normalized
                """
                
                execute_values(cursor, query, data)
                
            self.conn.commit()
            self.logger.info(f"Сохранено {len(leads)} лидов в БД")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка сохранения лидов: {str(e)}")
            raise
    
    def save_scoring_history(self, results):
        """Сохранение результатов скоринга в историю"""
        if not results:
            return
            
        try:
            with self.conn.cursor() as cursor:
                # Получаем lead_id для всех телефонов
                phones = [result['phone'] for result in results]
                placeholders = ','.join(['%s'] * len(phones))
                
                cursor.execute(
                    f"SELECT phone, lead_id FROM leads WHERE phone IN ({placeholders})",
                    phones
                )
                phone_to_id = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Подготавливаем данные для вставки
                data = []
                for result in results:
                    lead_id = phone_to_id.get(result['phone'])
                    if lead_id:
                        data.append((
                            lead_id,
                            result['score'],
                            result['group'],
                            result.get('reason_1', ''),
                            result.get('reason_2', ''),
                            result.get('reason_3', '')
                        ))
                
                if not data:
                    return
                
                # Пакетная вставка
                execute_values(
                    cursor,
                    """INSERT INTO scoring_history 
                    (lead_id, score, group_name, reason_1, reason_2, reason_3) 
                    VALUES %s""",
                    data
                )
                
            self.conn.commit()
            self.logger.info(f"Сохранено {len(data)} записей в историю скоринга")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Ошибка сохранения истории: {str(e)}")
            raise
    
    def save_error_log(self, error):
        """Сохранение ошибки в лог"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO error_logs (fio, inn, error, service)
                    VALUES (%s, %s, %s, %s)""",
                    (
                        error.get('fio', ''),
                        error.get('inn', ''),
                        error.get('error', ''),
                        error.get('service', 'Unknown')
                    )
                )
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения лога: {str(e)}")
    
    def get_recent_errors(self, limit=20):
        """Получение последних ошибок"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    """SELECT fio, inn, error, service, occurred_at
                    FROM error_logs
                    ORDER BY occurred_at DESC
                    LIMIT %s""",
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка получения ошибок: {str(e)}")
            return []
    
    def get_group_stats(self):
        """Статистика по группам"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """SELECT group_name, COUNT(*) as count
                    FROM scoring_history
                    WHERE scored_at > CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY group_name
                    ORDER BY count DESC"""
                )
                return [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {str(e)}")
            return []

# Синглтон для доступа к БД
db_instance = Database()

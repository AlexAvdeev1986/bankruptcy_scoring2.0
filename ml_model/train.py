import os
import sys
import logging
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
import joblib

# Добавляем корень проекта в путь
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.database import db_instance

# Настройка логгера
logger = logging.getLogger('train_model')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

def fetch_training_data():
    """Получение данных для обучения из базы данных"""
    try:
        # Инициализация подключения
        db_instance.initialize()
        
        with db_instance.conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    debt_amount,
                    debt_count,
                    has_property::int AS has_property,
                    has_court_order::int AS has_court_order,
                    is_inn_active::int AS is_inn_active,
                    is_bankrupt::int AS is_bankrupt,
                    (score >= 50)::int AS target
                FROM leads
                JOIN scoring_history ON leads.lead_id = scoring_history.lead_id
                WHERE score IS NOT NULL
            """)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
        
        return pd.DataFrame(data, columns=columns)
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {str(e)}")
        return pd.DataFrame()
    finally:
        if db_instance.conn:
            db_instance.conn.close()

def train_model():
    """Обучение модели машинного обучения"""
    try:
        # Получение данных
        df = fetch_training_data()
        
        if df.empty:
            logger.error("Нет данных для обучения модели")
            return False
        
        # Проверка качества данных
        if df.isnull().sum().sum() > 0:
            logger.warning("Обнаружены пропущенные значения в данных")
            df = df.fillna(0)
            
        # Подготовка данных
        X = df.drop('target', axis=1)
        y = df['target']
        
        # Разделение на обучающую и тестовую выборки
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Обучение модели
        model = CatBoostClassifier(
            iterations=500,
            learning_rate=0.05,
            depth=6,
            verbose=True
        )
        
        model.fit(
            X_train, y_train,
            eval_set=(X_test, y_test),
            early_stopping_rounds=20
        )
        
        # Сохранение модели
        model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
        joblib.dump(model, model_path)
        logger.info(f"Модель сохранена в {model_path}. Точность: {model.score(X_test, y_test):.4f}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при обучении модели: {str(e)}")
        return False

if __name__ == '__main__':
    train_model()
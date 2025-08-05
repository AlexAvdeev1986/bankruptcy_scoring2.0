import joblib
import pandas as pd
from datetime import datetime
import logging
import os
from config import Config

# Настройка логгера
logger = logging.getLogger('MLScorer')

# Стандартный порядок признаков
ML_FEATURES = [
    'debt_amount',
    'debt_count',
    'has_property',
    'has_court_order',
    'is_inn_active',
    'is_bankrupt'
]

model = None

def load_model():
    global model
    if model is None:
        model_path = Config.ML_MODEL_PATH
        try:
            if os.path.exists(model_path) and os.path.getsize(model_path) > 1024:
                model = joblib.load(model_path)
                logger.info("ML модель успешно загружена")
            else:
                logger.error(f"Файл модели не найден или пуст: {model_path}")
                model = None
        except Exception as e:
            logger.error(f"Ошибка загрузки ML модели: {str(e)}")
            model = None
    return model

def predict_proba(lead):
    """Прогнозирование с использованием ML-модели"""
    model = load_model()
    if model is None:
        logger.warning("Используется fallback-оценка (50)")
        return 50
    
    try:
        # Расчет возраста
        def calculate_age(dob):
            if not dob:
                return 40
            if isinstance(dob, str):
                try:
                    dob = datetime.strptime(dob, "%Y-%m-%d")
                except ValueError:
                    return 40
            today = datetime.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Подготовка признаков в правильном порядке
        feature_data = {
            'debt_amount': lead.get('debt_amount', 0),
            'debt_count': lead.get('debt_count', 0),
            'has_property': 1 if lead.get('has_property') else 0,
            'has_court_order': 1 if lead.get('has_court_order') else 0,
            'is_inn_active': 1 if lead.get('is_inn_active') else 0,
            'is_bankrupt': 1 if lead.get('is_bankrupt') else 0
        }
        
        # Создание DataFrame с фиксированным порядком столбцов
        features = pd.DataFrame([feature_data], columns=ML_FEATURES)
        
        # Предсказание
        probability = model.predict_proba(features)[0][1]
        return int(probability * 100)
    except Exception as e:
        logger.error(f"Ошибка предсказания: {str(e)}")
        return 50  # Нейтральное значение при ошибке

# Попытка загрузки модели при импорте
try:
    load_model()
    if model:
        logger.info("ML модель успешно загружена при инициализации")
    else:
        logger.warning("Модель не загружена")
except Exception as e:
    logger.error(f"Ошибка при загрузке модели: {str(e)}")
    
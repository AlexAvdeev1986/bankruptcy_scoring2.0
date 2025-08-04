import joblib
import pandas as pd
from datetime import datetime  # Добавлен импорт
import numpy as np
import logging
import os
from config import Config

# Настройка логгера
logger = logging.getLogger('MLScorer')

model = None

def load_model():
    global model
    if model is None:
        try:
            model = joblib.load(Config.ML_MODEL_PATH)
            logger.info("ML модель успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки ML модели: {str(e)}")
            model = None
    return model

def predict_proba(lead: dict) -> int:
    """Прогнозирование с использованием ML-модели"""
    # Fallback если модель не загружена
    if load_model() is None:
        logger.warning("Используется fallback-оценка (50)")
        return 50
    
    try:
        # Расчет возраста
        def calculate_age(dob):
            if not dob:
                return 40
            if isinstance(dob, str):
                dob = datetime.strptime(dob, "%Y-%m-%d")
            today = datetime.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Подготовка признаков
        features = pd.DataFrame([{
            'debt_amount': lead.get('debt_amount', 0),
            'debt_count': lead.get('debt_count', 0),
            'has_property': 1 if lead.get('has_property') else 0,
            'is_inn_active': 1 if lead.get('is_inn_active') else 0,
            'has_court_order': 1 if lead.get('has_court_order') else 0,
            'age': calculate_age(lead.get('dob'))
        }])
        
        # Предсказание
        probability = model.predict_proba(features)[0][1]
        return int(probability * 100)
    except Exception as e:
        logger.error(f"Ошибка предсказания: {str(e)}")
        return 50  # Нейтральное значение при ошибке

# Загрузка модели при импорте
model_path = Config.ML_MODEL_PATH
if os.path.exists(model_path):
    model = joblib.load(model_path)
else:
    model = None
    print(f"Предупреждение: ML модель не найдена по пути {model_path}")

def predict_proba(lead: dict) -> int:
    """
    Предсказание вероятности банкротства с помощью ML-модели
    :param lead: словарь с данными лида
    :return: оценка от 0 до 100
    """
    if model is None:
        return 50  # Нейтральное значение если модель не загружена
    
    try:
        # Подготовка признаков для модели
        features = pd.DataFrame([{
            'debt_amount': lead.get('debt_amount', 0),
            'debt_count': lead.get('debt_count', 0),
            'has_property': 1 if lead.get('has_property', False) else 0,
            'is_inn_active': 1 if lead.get('is_inn_active', True) else 0,
            'has_court_order': 1 if lead.get('has_court_order', False) else 0,
            'age': calculate_age(lead.get('dob'))
        }])
        
        # Предсказание
        probability = model.predict_proba(features)[0][1]
        return int(probability * 100)
    except Exception as e:
        print(f"Ошибка предсказания ML-модели: {e}")
        return 50

def calculate_age(dob):
    """Расчет возраста по дате рождения"""
    if not dob:
        return 40  # Среднее значение по умолчанию
    
    today = datetime.today()
    birth_date = dob if isinstance(dob, datetime) else datetime.strptime(dob, "%Y-%m-%d")
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

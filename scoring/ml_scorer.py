import joblib
import pandas as pd
import numpy as np
import os
from config import Config

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

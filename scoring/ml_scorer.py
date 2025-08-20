import joblib
import pandas as pd
import logging
import os
from config import Config
from scoring.rule_based_scorer import calculate_score

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
                
                # Проверка валидности модели
                test_features = pd.DataFrame([{
                    'debt_amount': 100000,
                    'debt_count': 2,
                    'has_property': 1,
                    'has_court_order': 0,
                    'is_inn_active': 1,
                    'is_bankrupt': 0
                }], columns=ML_FEATURES)
                
                try:
                    test_pred = model.predict_proba(test_features)
                    logger.info("Модель прошла валидацию")
                except Exception as e:
                    logger.error(f"Модель не прошла валидацию: {str(e)}")
                    model = None
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
    
    # Fallback на rule-based scoring при проблемах с моделью
    if model is None:
        logger.warning("Используется rule-based оценка из-за проблем с ML моделью")
        score, _ = calculate_score(lead, 250000)  # Используем стандартный min_debt
        return score
    
    try:
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
        ml_score = int(probability * 100)
        
        logger.debug(f"ML оценка: {ml_score}")
        return ml_score
        
    except Exception as e:
        logger.error(f"Ошибка предсказания: {str(e)}")
        # Fallback на rule-based scoring при ошибке
        score, _ = calculate_score(lead, 250000)
        return score

# Попытка загрузки модели при импорте
try:
    load_model()
    if model:
        logger.info("ML модель успешно загружена при инициализации")
    else:
        logger.warning("Модель не загружена, будет использоваться rule-based fallback")
except Exception as e:
    logger.error(f"Ошибка при загрузке модели: {str(e)}")
    
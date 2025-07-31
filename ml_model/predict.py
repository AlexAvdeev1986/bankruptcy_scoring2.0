import joblib
import pandas as pd

model = None

def load_model():
    global model
    if model is None:
        model = joblib.load('ml_model/model.pkl')
    return model

def predict_proba(lead):
    """Прогнозирование с использованием ML-модели"""
    model = load_model()
    
    features = pd.DataFrame([{
        'debt_amount': lead.get('debt_amount', 0),
        'debt_count': lead.get('debt_count', 0),
        'has_property': 1 if lead.get('has_property') else 0,
        'has_court_order': 1 if lead.get('has_court_order') else 0,
        'is_inn_active': 1 if lead.get('is_inn_active') else 0,
        'is_bankrupt': 1 if lead.get('is_bankrupt') else 0
    }])
    
    probability = model.predict_proba(features)[0][1]
    return int(probability * 100)
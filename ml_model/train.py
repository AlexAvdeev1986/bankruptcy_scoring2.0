import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
import joblib
from database.database import db_instance

def fetch_training_data():
    """Получение данных для обучения из базы данных"""
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

def train_model():
    """Обучение модели машинного обучения"""
    # Получение данных
    df = fetch_training_data()
    
    if df.empty:
        raise ValueError("Нет данных для обучения модели")
    
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
    joblib.dump(model, 'ml_model/model.pkl')
    print(f"Модель сохранена. Точность: {model.score(X_test, y_test):.4f}")

if __name__ == '__main__':
    train_model()
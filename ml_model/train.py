import os
import sys
import logging
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
import joblib
import traceback
import shutil

# Настройка логгера
logger = logging.getLogger('model_trainer')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s'
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'model_training.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

def fetch_training_data():
    """Получение реальных данных для обучения из БД"""
    logger.info("Начало получения данных для обучения из БД")
    
    try:
        from database.database import db_instance
        
        # Получение данных из БД
        training_data = db_instance.get_training_data(limit=10000)
        
        if not training_data:
            logger.warning("Нет данных для обучения в БД. Используются демо-данные.")
            return generate_demo_data()
        
        df = pd.DataFrame(training_data)
        logger.info(f"Получено {len(df)} записей для обучения из БД")
        
        # Проверка баланса классов
        target_distribution = df['target'].value_counts(normalize=True)
        logger.info(f"Распределение целевой переменной:\n{target_distribution}")
        
        return df
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {str(e)}")
        logger.debug(traceback.format_exc())
        return generate_demo_data()

def generate_demo_data():
    """Генерация демо-данных только при отсутствии реальных"""
    logger.info("Генерация демо-данных для обучения")
    
    n_samples = 1000
    np.random.seed(42)
    
    # Более реалистичные демо-данные
    data = {
        'debt_amount': np.random.exponential(scale=300000, size=n_samples),
        'debt_count': np.random.poisson(lam=3, size=n_samples),
        'has_property': np.random.binomial(1, 0.6, size=n_samples),
        'has_court_order': np.random.binomial(1, 0.4, size=n_samples),
        'is_inn_active': np.random.binomial(1, 0.8, size=n_samples),
        'is_bankrupt': np.random.binomial(1, 0.2, size=n_samples),
    }
    
    # Создание целевой переменной на основе логики
    bankruptcy_risk = (
        0.3 * (data['debt_amount'] > 500000) +
        0.2 * (data['debt_count'] > 5) +
        0.1 * (data['has_property'] == 0) +
        0.2 * (data['has_court_order'] == 1) +
        0.1 * (data['is_inn_active'] == 0) +
        0.1 * (data['is_bankrupt'] == 1) +
        np.random.normal(0, 0.1, n_samples)
    )
    
    data['target'] = (bankruptcy_risk > 0.5).astype(int)
    
    df = pd.DataFrame(data)
    logger.info(f"Сгенерировано {len(df)} демо-записей")
    
    return df

def preprocess_data(df):
    """Предварительная обработка данных с балансировкой классов"""
    logger.info("Начало предобработки данных")
    
    # Проверка наличия данных
    if df.empty:
        logger.error("Получен пустой DataFrame")
        return None, None, None, None
    
    # Проверка пропущенных значений
    missing_values = df.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Обнаружено {missing_values} пропущенных значений")
        df = df.fillna(0)
    
    # Балансировка классов
    if df['target'].nunique() == 1:
        logger.warning("Все образцы принадлежат одному классу. Добавляем разнообразие.")
        # Добавляем противоположные примеры
        opposite = df.copy()
        opposite['target'] = 1 - opposite['target']
        opposite['debt_amount'] = opposite['debt_amount'] * 0.5
        opposite['debt_count'] = opposite['debt_count'] // 2
        df = pd.concat([df, opposite])
    
    # Проверка баланса классов
    target_distribution = df['target'].value_counts(normalize=True)
    logger.info(f"Распределение целевой переменной:\n{target_distribution}")
    
    # Разделение на признаки и целевую переменную
    X = df.drop('target', axis=1)
    y = df['target']
    
    # Разделение на обучающую и тестовую выборки
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=0.2, 
        random_state=42,
        stratify=y
    )
    
    logger.info(f"Размеры выборок: train={len(X_train)}, test={len(X_test)}")
    return X_train, X_test, y_train, y_test

def train_and_save_model(X_train, X_test, y_train, y_test):
    """Обучение модели с улучшенной обработкой ошибок"""
    logger.info("Начало обучения модели")
    
    try:
        # Параметры модели
        model_params = {
            'iterations': 100,
            'learning_rate': 0.1,
            'depth': 6,
            'eval_metric': 'AUC',
            'random_seed': 42,
            'verbose': False,
            'early_stopping_rounds': 10
        }
        
        # Создание и обучение модели
        model = CatBoostClassifier(**model_params)
        model.fit(X_train, y_train, eval_set=(X_test, y_test))
        
        # Оценка качества модели
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)
        
        train_accuracy = accuracy_score(y_train, train_pred)
        test_accuracy = accuracy_score(y_test, test_pred)
        
        train_auc = roc_auc_score(y_train, model.predict_proba(X_train)[:, 1])
        test_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        
        logger.info(f"Точность модели: train={train_accuracy:.4f}, test={test_accuracy:.4f}")
        logger.info(f"AUC модели: train={train_auc:.4f}, test={test_auc:.4f}")
        
        # Проверка на переобучение
        if train_accuracy - test_accuracy > 0.15:
            logger.warning("Возможно переобучение модели!")
        
        # Сохранение модели
        model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
        
        # Создаем временный файл
        temp_path = model_path + '.tmp'
        joblib.dump(model, temp_path)
            
        # Перемещаем временный файл в окончательное место
        shutil.move(temp_path, model_path)
            
        logger.info(f"Модель успешно сохранена в {model_path}")
        logger.info(f"Размер файла модели: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обучении модели: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def main():
    """Основной рабочий процесс с улучшенной обработкой ошибок"""
    logger.info("=" * 80)
    logger.info("Запуск процесса обучения модели")
    
    try:
        # Шаг 1: Получение данных
        df = fetch_training_data()
        
        # Шаг 2: Предобработка данных
        X_train, X_test, y_train, y_test = preprocess_data(df)
        
        if X_train is None:
            logger.error("Ошибка предобработки данных. Процесс остановлен.")
            return False
        
        # Шаг 3: Обучение и сохранение модели
        success = train_and_save_model(X_train, X_test, y_train, y_test)
        
        if success:
            logger.info("Обучение модели успешно завершено!")
            return True
        else:
            logger.error("Обучение модели завершено с ошибками")
            return False
    except Exception as e:
        logger.critical(f"Критическая ошибка в основном процессе: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

if __name__ == '__main__':
    # Создаем необходимые директории
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'ml_model'), exist_ok=True)
    
    # Запуск процесса
    success = main()
    
    # Возвращаем соответствующий код выхода
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
        
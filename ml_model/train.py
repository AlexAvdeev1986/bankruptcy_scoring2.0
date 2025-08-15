import os
import sys
import logging
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
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
    """Получение данных для обучения с улучшенным запросом"""
    logger.info("Начало получения данных для обучения")
    df = pd.DataFrame()
    
    try:
        # Имитация подключения к БД
        # В реальной реализации здесь будет запрос к базе
        logger.debug("Подключение к БД установлено")
        
        # Генерация разнообразных тестовых данных
        n_samples = 200
        np.random.seed(42)
        
        data = {
            'debt_amount': np.random.exponential(scale=300000, size=n_samples),
            'debt_count': np.random.randint(1, 10, size=n_samples),
            'has_property': np.random.randint(0, 2, size=n_samples),
            'has_court_order': np.random.randint(0, 2, size=n_samples),
            'is_inn_active': np.random.randint(0, 2, size=n_samples),
            'is_bankrupt': np.random.randint(0, 2, size=n_samples),
            'target': np.random.randint(0, 2, size=n_samples)
        }
        df = pd.DataFrame(data)
        logger.info(f"Сгенерировано {len(df)} тестовых записей")
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {str(e)}")
        logger.debug(traceback.format_exc())
    
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
        # Упрощенные параметры для тестовой модели
        model_params = {
            'iterations': 50,
            'learning_rate': 0.1,
            'depth': 4,
            'eval_metric': 'AUC',
            'random_seed': 42,
            'verbose': False
        }
        
        # Создание и обучение модели
        model = CatBoostClassifier(**model_params)
        model.fit(X_train, y_train)
        
        # Оценка качества модели
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        logger.info(f"Точность модели: train={train_score:.4f}, test={test_score:.4f}")
        
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
        
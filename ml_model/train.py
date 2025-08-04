import os
import sys
import logging
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
import joblib
import traceback
import numpy as np

# Добавляем корень проекта в путь для корректного импорта модулей
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# Настройка логгера
logger = logging.getLogger('model_trainer')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s'
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

log_file = os.path.join(PROJECT_ROOT, 'logs', 'model_training.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

try:
    from database.database import db_instance
    logger.info("Импорт модуля базы данных выполнен успешно")
except ImportError as e:
    logger.critical(f"Ошибка импорта модуля базы данных: {str(e)}")
    sys.exit(1)

def fetch_training_data():
    """
    Получение данных для обучения из базы данных
    Возвращает DataFrame с признаками и целевой переменной
    """
    logger.info("Начало получения данных для обучения")
    df = pd.DataFrame()
    
    try:
        # Инициализация подключения к БД
        db_instance.initialize()
        logger.debug("Подключение к БД установлено")
        
        # SQL-запрос для получения данных
        query = """
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
        """
        
        # Выполняем запрос и преобразуем результат в DataFrame
        with db_instance.conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
            logger.info(f"Получено {len(df)} записей из БД")
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {str(e)}")
        logger.debug(traceback.format_exc())
    finally:
        # Всегда закрываем соединение с БД
        if db_instance.conn:
            db_instance.conn.close()
            logger.debug("Соединение с БД закрыто")
    
    return df

def generate_sample_data():
    """Генерация синтетических данных для обучения"""
    logger.info("Генерация синтетических данных")
    n_samples = 1000
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
    return pd.DataFrame(data)

def preprocess_data(df):
    """
    Предварительная обработка данных:
    - Проверка на пропущенные значения
    - Заполнение пропусков
    - Проверка баланса классов
    """
    logger.info("Начало предобработки данных")
    
    # Проверка наличия данных
    if df.empty:
        logger.error("Получен пустой DataFrame")
        return None, None, None, None
    
    # Проверка пропущенных значений
    missing_values = df.isnull().sum().sum()
    if missing_values > 0:
        logger.warning(f"Обнаружено {missing_values} пропущенных значений")
        # Заполняем пропуски
        df = df.fillna({
            'debt_amount': 0,
            'debt_count': 0,
            'has_property': 0,
            'has_court_order': 0,
            'is_inn_active': 1,  # По умолчанию считаем ИНН активным
            'is_bankrupt': 0,
            'target': 0
        })
    
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
        stratify=y  # Сохраняем распределение классов
    )
    
    logger.info(f"Размеры выборок: train={len(X_train)}, test={len(X_test)}")
    return X_train, X_test, y_train, y_test

def train_and_save_model(X_train, X_test, y_train, y_test):
    """
    Обучение модели CatBoost и сохранение в файл
    """
    logger.info("Начало обучения модели")
    
    try:
        # Параметры модели
        model_params = {
            'iterations': 1000,
            'learning_rate': 0.05,
            'depth': 8,
            'l2_leaf_reg': 3,
            'eval_metric': 'AUC',
            'early_stopping_rounds': 50,
            'verbose': 100,
            'random_seed': 42,
            'task_type': 'CPU'  # Можно изменить на GPU, если доступно
        }
        
        # Создание и обучение модели
        model = CatBoostClassifier(**model_params)
        model.fit(
            X_train, y_train,
            eval_set=(X_test, y_test),
            use_best_model=True
        )
        
        # Оценка качества модели
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        logger.info(f"Точность модели: train={train_score:.4f}, test={test_score:.4f}")
        
        # Сохранение модели
        model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
        
        # Используем контекстный менеджер для безопасного сохранения
        with open(model_path, 'wb') as model_file:
            joblib.dump(model, model_file, protocol=4)  # protocol=4 для совместимости
            
        logger.info(f"Модель успешно сохранена в {model_path}")
        logger.info(f"Размер файла модели: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обучении модели: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def main():
    """Основной рабочий процесс"""
    logger.info("=" * 80)
    logger.info("Запуск процесса обучения модели")
    logger.info(f"Рабочая директория: {os.getcwd()}")
    logger.info(f"Python версия: {sys.version}")
    
    try:
        # Шаг 1: Получение данных
        df = fetch_training_data()
        
        # Если данных нет, используем синтетические
        if df.empty:
            logger.warning("Реальных данных нет. Используются синтетические данные.")
            df = generate_sample_data()
        
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
    os.makedirs(os.path.join(PROJECT_ROOT, 'logs'), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, 'ml_model'), exist_ok=True)
    
    # Запуск процесса
    success = main()
    
    # Возвращаем соответствующий код выхода
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
        
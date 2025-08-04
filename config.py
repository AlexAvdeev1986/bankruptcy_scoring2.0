import os

class Config:
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'secret_key')
    
    # Директории
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
    RESULT_FOLDER = os.path.join(BASE_DIR, 'data', 'results')
    ERROR_LOG_FOLDER = os.path.join(BASE_DIR, 'logs', 'errors')
    HISTORY_FOLDER = os.path.join(BASE_DIR, 'data', 'history')
    
    # Файл логов
    LOG_FILE = os.path.join(BASE_DIR, 'logs', 'scoring_system.log')
    
    # Максимальный размер файла (50MB)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    
    # Регионы
    REGIONS = [
        'Москва', 'Санкт-Петербург', 'Татарстан', 'Саратов', 'Калуга',
        'Московская область', 'Краснодарский край', 'Свердловская область'
    ]
    
    # Прокси (в реальности нужно брать из внешнего источника)
    PROXY_LIST = os.environ.get('PROXY_LIST', '').split(',') or [
        'http://user:pass@192.168.1.1:8080',
        'http://user:pass@192.168.1.2:8080',
        # ... минимум 300 прокси
    ]
    
    # Настройки внешних сервисов
    FSSP_URL = 'https://fssp.gov.ru/api/search'
    FEDRESURS_URL = 'https://fedresurs.ru/api/public/company'
    ROSREESTR_URL = 'https://rosreestr.gov.ru/api/online/fir_object'
    TAX_SERVICE_URL = 'https://service.nalog.ru/inn-proc.do'
    COURT_URL = 'https://sudrf.ru/index.php'
    
    # Настройки ML модели
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'ml_model', 'model.pkl')
    
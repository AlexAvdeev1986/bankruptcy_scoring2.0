import os
import csv
import sys
import logging
import pandas as pd
import concurrent.futures
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename, safe_join

# Импорты для обработки данных
from data_processing.data_loader import DataLoader
from data_processing.data_normalizer import DataNormalizer
from data_processing.deduplicator import Deduplicator

# Импорты для обогащения данных
from enrichment.enricher import DataEnricher
from enrichment.fedresurs_service import FedresursService
from enrichment.fssp_service import FSSPService
from enrichment.tax_service import TaxService
from enrichment.rosreestr_service import RosreestrService
from enrichment.court_service import CourtService

# Импорты для скоринга
from scoring.rule_based_scorer import calculate_score, assign_group
from scoring.ml_scorer import predict_proba

# Утилиты
from utils.logger import setup_logger
from utils.proxy_rotator import ProxyRotator
from utils.file_utils import save_errors, prepare_output, save_results

# База данных
from database.database import db_instance

# Инициализация приложения
app = Flask(__name__)
app.config.from_object('config.Config')

# Настройка логгера
logger = setup_logger(
    name='scoring_system',
    log_level=app.config['LOG_LEVEL'],  # Используем новый параметр
    log_file=app.config['LOG_FILE']     # Путь к файлу лога
)
logger = logging.getLogger('scoring_system')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Инициализация компонентов
proxy_rotator = ProxyRotator(app.config['PROXY_LIST'])
data_enricher = DataEnricher(proxy_rotator, app.config)

@app.route('/')
def index():
    """Главная страница веб-интерфейса"""
    regions = app.config['REGIONS']
    return render_template('index.html', regions=regions)

@app.route('/start-scoring', methods=['POST'])
def start_scoring():
    """Запуск процесса скоринга"""
    try:
        # Получение параметров из формы
        params = {
            'regions': request.form.getlist('regions'),
            'min_debt': int(request.form.get('min_debt', 250000)),
            'exclude_bankrupt': 'exclude_bankrupt' in request.form,
            'exclude_no_debt': 'exclude_no_debt' in request.form,
            'only_with_property': 'only_with_property' in request.form,
            'only_bank_mfo_debts': 'only_bank_mfo_debts' in request.form,
            'only_recent_court_orders': 'only_recent_court_orders' in request.form,
            'only_active_inn': 'only_active_inn' in request.form,
            'use_ml_model': 'use_ml_model' in request.form
        }
        
        # Сохранение загруженных файлов
        file_paths = []
        for file in request.files.getlist('lead_files'):
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = safe_join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_paths.append(file_path)
                logger.info(f"Файл {filename} успешно загружен")
        
        if not file_paths:
            return jsonify({'status': 'error', 'message': 'Не загружены файлы с данными'}), 400
        
        try:
            # Запуск процесса скоринга
            result_file = process_scoring(file_paths, params)
        except Exception as e:
            logger.error(f"Ошибка обработки данных: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Ошибка в данных: {str(e)}'
            }), 400
        
        return jsonify({
            'status': 'success',
            'message': 'Скоринг успешно завершен',
            'result_file': result_file
        })
    
    except Exception as e:
        logger.error(f"Ошибка запуска скоринга: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Ошибка при запуске скоринга: {str(e)}'
        }), 500

def process_scoring(file_paths, params):
    """Основной процесс скоринга"""
    # Шаг 1: Загрузка и нормализация данных
    logger.info("Начало обработки данных")
    data_loader = DataLoader()
    df = data_loader.load_data(file_paths)
    
    normalizer = DataNormalizer()
    df = normalizer.normalize(df)
    
    deduplicator = Deduplicator()
    df = deduplicator.deduplicate(df)
    
    # Фильтрация по регионам
    if params['regions']:
        df = df[df['region'].isin(params['regions'])]
    
    # Конвертация в список словарей для дальнейшей обработки
    leads = df.to_dict('records')
    
    # Шаг 2: Обогащение данных (параллельная обработка)
    logger.info(f"Начато обогащение данных для {len(leads)} лидов")
    enriched_data = []
    errors = []
    
    def enrich_lead(lead):
        try:
            return data_enricher.enrich(lead)
        except Exception as e:
            errors.append({
                'fio': lead.get('fio', ''),
                'inn': lead.get('inn', ''),
                'error': str(e),
                'service': 'DataEnrichment'
            })
            logger.error(f"Ошибка обогащения: {lead.get('fio', '')} - {str(e)}")
            return lead
    
    # Параллельная обработка с ограничением потоков
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(enrich_lead, leads)
        enriched_data = [result for result in results if result is not None]
    
    # Сохранение ошибок в БД
    for error in errors:
        db_instance.save_error_log(error)
    
    # Шаг 3: Расчет скоринга
    logger.info("Расчет скоринга")
    scoring_results = []
    for lead in enriched_data:
        try:
            score, reasons = calculate_score(lead, params['min_debt'])
            
            # Применение ML-модели если выбрано
            if params['use_ml_model']:
                ml_score = predict_proba(lead)
                # Комбинируем rule-based и ML оценки
                final_score = (score * 0.7) + (ml_score * 0.3)
                lead['ml_score'] = ml_score
                reasons.append(f"ML-оценка: {ml_score:.0f}")
                score = final_score
            
            lead['score'] = min(100, max(0, int(score)))
            lead['reasons'] = reasons
            lead['is_target'] = 1 if score >= 50 else 0
            lead['group'] = assign_group(lead)
            
            # Применение фильтров
            if should_exclude_lead(lead, params):
                continue
                
            scoring_results.append(lead)
        except Exception as e:
            logger.error(f"Ошибка скоринга для лида {lead.get('fio', '')}: {str(e)}")
    
    # Сортировка по убыванию скоринга
    scoring_results.sort(key=lambda x: x['score'], reverse=True)
    
    # Шаг 4: Формирование результата
    logger.info(f"Формирование результата, найдено {len(scoring_results)} целевых лидов")
    output_data = prepare_output(scoring_results)
    result_file = save_results(output_data, app.config['RESULT_FOLDER'])
    
    # Сохранение в БД
    db_instance.save_leads(scoring_results)
    db_instance.save_scoring_history(output_data)
    
    return result_file

def should_exclude_lead(lead, params):
    """Проверка исключения лида по фильтрам"""
    if params['exclude_bankrupt'] and lead.get('is_bankrupt'):
        return True
    if params['exclude_no_debt'] and lead.get('debt_amount', 0) == 0:
        return True
    if params['only_with_property'] and not lead.get('has_property'):
        return True
    if params['only_bank_mfo_debts'] and not lead.get('has_bank_mfo_debt'):
        return True
    if params['only_recent_court_orders'] and not lead.get('has_recent_court_order'):
        return True
    if params['only_active_inn'] and not lead.get('is_inn_active'):
        return True
    return False

@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание результата"""
    safe_filename = secure_filename(filename)
    file_path = safe_join(app.config['RESULT_FOLDER'], safe_filename)
    
    if not os.path.exists(file_path):
        return "Файл не найден", 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name='scoring_ready.csv'
    )

@app.route('/logs')
def view_logs():
    """Просмотр логов ошибок"""
    log_files = [f for f in os.listdir(app.config['ERROR_LOG_FOLDER']) 
                 if f.startswith('errors_') and f.endswith('.csv')]
    
    # Получаем последние ошибки из БД
    recent_errors = db_instance.get_recent_errors(limit=50)
    
    return render_template('logs.html', log_files=log_files, recent_errors=recent_errors)

@app.route('/logs/<filename>')
def download_log(filename):
    """Скачивание файла лога"""
    safe_filename = secure_filename(filename)
    file_path = safe_join(app.config['ERROR_LOG_FOLDER'], safe_filename)
    
    if not os.path.exists(file_path):
        return "Файл не найден", 404
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=safe_filename
    )

@app.route('/group-stats')
def group_stats():
    """Статистика по группам"""
    stats = db_instance.get_group_stats()
    return jsonify(stats)

if __name__ == '__main__':
    # Создание необходимых директорий
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['ERROR_LOG_FOLDER'], exist_ok=True)
    
    # Инициализация базы данных
    db_instance.initialize()
    db_instance.initialize_db()
    
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
    
import os
import csv
from datetime import datetime

def save_errors(errors: list, log_folder: str):
    """Сохранение ошибок в файл"""
    if errors:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_filename = f"errors_{timestamp}.csv"
        error_path = os.path.join(log_folder, error_filename)
        
        os.makedirs(log_folder, exist_ok=True)
        
        with open(error_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['fio', 'inn', 'error', 'service']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(errors)

def prepare_output(scoring_results: list) -> list:
    """Подготовка данных для выгрузки"""
    output_data = []
    for lead in scoring_results:
        output_data.append({
            'phone': lead['phone'],
            'fio': lead['fio'],
            'score': lead['score'],
            'reason_1': lead['reasons'][0] if len(lead['reasons']) > 0 else '',
            'reason_2': lead['reasons'][1] if len(lead['reasons']) > 1 else '',
            'reason_3': lead['reasons'][2] if len(lead['reasons']) > 2 else '',
            'is_target': lead['is_target'],
            'group': lead['group']
        })
    return output_data

def save_results(output_data: list, result_folder: str) -> str:
    """Сохранение результатов в CSV"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_filename = f"scoring_ready_{timestamp}.csv"
    result_path = os.path.join(result_folder, result_filename)
    
    os.makedirs(result_folder, exist_ok=True)
    
    with open(result_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_data[0].keys())
        writer.writeheader()
        writer.writerows(output_data)
    
    return result_filename

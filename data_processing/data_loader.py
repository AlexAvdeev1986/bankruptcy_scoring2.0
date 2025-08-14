import pandas as pd
import os
import re
from typing import List

class DataLoader:
    def __init__(self):
        self.column_mapping = {
            'full_name': 'fio',
            'name': 'fio',
            'фио': 'fio',
            'телефон': 'phone',
            'mobile': 'phone',
            'телефонный номер': 'phone',
            'date_of_birth': 'dob',
            'дата рождения': 'dob',
            'город': 'city',
            'улица': 'street',
            'дом': 'house',
            'квартира': 'apartment'
        }
    
    def load_data(self, file_paths: List[str]) -> pd.DataFrame:
        """Загрузка данных из нескольких CSV-файлов"""
        dfs = []
        for file_path in file_paths:
            try:
                # Загрузка файла
                df = pd.read_csv(file_path)
                df['source_file'] = os.path.basename(file_path)
                
                # Автоматическое переименование столбцов
                df.rename(columns=lambda x: self.column_mapping.get(
                    re.sub(r'\s+', '', x.lower()), x), inplace=True)
                
                # Проверка обязательных полей
                required = ['fio', 'phone']
                if not all(col in df.columns for col in required):
                    missing = [col for col in required if col not in df.columns]
                    raise ValueError(f"Отсутствуют обязательные столбцы: {', '.join(missing)}")
                
                # Создаем столбец address из city, street, house, apartment
                df['address'] = df.apply(
                    lambda row: ', '.join(
                        filter(None, [
                            str(row.get('city', '')),
                            str(row.get('street', '')),
                            str(row.get('house', '')),
                            str(row.get('apartment', ''))
                        ])
                    ), 
                    axis=1
                )
                
                dfs.append(df)
            except Exception as e:
                raise Exception(f"Ошибка загрузки файла {file_path}: {str(e)}")
        
        if not dfs:
            raise ValueError("Не удалось загрузить данные из файлов")
        
        return pd.concat(dfs, ignore_index=True)
    
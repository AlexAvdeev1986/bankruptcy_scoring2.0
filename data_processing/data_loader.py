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
            'phone_number': 'phone',
            'номер телефона': 'phone',
            'date_of_birth': 'dob',
            'дата рождения': 'dob',
            'город': 'city',
            'улица': 'street',
            'дом': 'house',
            'квартира': 'apartment',
            'property': 'has_property'
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
                
                # Проверка обязательных полей (только phone)
                if 'phone' not in df.columns:
                    raise ValueError("Отсутствует обязательный столбец phone")
                
                # Создаем столбец address из city, street, house, apartment (если есть)
                address_components = ['city', 'street', 'house', 'apartment']
                if any(comp in df.columns for comp in address_components):
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
                
                # Обработка булевых полей
                for bool_col in ['has_property', 'has_court_order', 'is_inn_active', 'is_bankrupt']:
                    if bool_col in df.columns:
                        # Преобразуем строковые значения в булевы
                        df[bool_col] = df[bool_col].apply(
                            lambda x: str(x).lower() in ['true', '1', 'yes', 'да'] if pd.notnull(x) else False
                        )
                
                dfs.append(df)
            except Exception as e:
                raise Exception(f"Ошибка загрузки файла {file_path}: {str(e)}")
        
        if not dfs:
            raise ValueError("Не удалось загрузить данные из файлов")
        
        return pd.concat(dfs, ignore_index=True)
    
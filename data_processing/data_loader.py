import pandas as pd
import os
import re
from typing import List, Generator

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
        """Загрузка данных из нескольких CSV-файлов с пагинацией"""
        dfs = []
        for file_path in file_paths:
            try:
                # Проверка размера файла
                file_size = os.path.getsize(file_path)
                if file_size > 100 * 1024 * 1024:  # 100MB
                    logger.warning(f"Большой файл {file_path} ({file_size/1024/1024:.2f} MB). Будет обрабатываться частями.")
                    
                    # Обработка больших файлов по частям
                    chunk_dfs = []
                    for chunk in self.load_data_chunked(file_path, chunksize=10000):
                        chunk_dfs.append(self.process_chunk(chunk, file_path))
                    
                    if chunk_dfs:
                        df = pd.concat(chunk_dfs, ignore_index=True)
                        dfs.append(df)
                else:
                    # Обычная обработка для небольших файлов
                    df = pd.read_csv(file_path)
                    df = self.process_chunk(df, file_path)
                    dfs.append(df)
                    
            except Exception as e:
                raise Exception(f"Ошибка загрузки файла {file_path}: {str(e)}")
        
        if not dfs:
            raise ValueError("Не удалось загрузить данные из файлов")
        
        return pd.concat(dfs, ignore_index=True)
    
    def load_data_chunked(self, file_path: str, chunksize: int = 10000) -> Generator[pd.DataFrame, None, None]:
        """Загрузка данных частями для больших файлов"""
        try:
            for chunk in pd.read_csv(file_path, chunksize=chunksize):
                yield chunk
        except Exception as e:
            raise Exception(f"Ошибка потоковой загрузки файла {file_path}: {str(e)}")
    
    def process_chunk(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """Обработка части данных"""
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
        
        return df
    
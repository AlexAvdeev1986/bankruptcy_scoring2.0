import pandas as pd
import os
from typing import List

class DataLoader:
    def load_data(self, file_paths: List[str]) -> pd.DataFrame:
        """Загрузка данных из нескольких CSV-файлов"""
        dfs = []
        for file_path in file_paths:
            try:
                df = pd.read_csv(file_path)
                df['source_file'] = os.path.basename(file_path)
                dfs.append(df)
            except Exception as e:
                raise Exception(f"Ошибка загрузки файла {file_path}: {str(e)}")
        
        if not dfs:
            raise ValueError("Не удалось загрузить данные из файлов")
        
        return pd.concat(dfs, ignore_index=True)
    
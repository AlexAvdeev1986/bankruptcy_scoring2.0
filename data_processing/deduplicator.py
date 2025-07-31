import pandas as pd

class Deduplicator:
    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Удаление дубликатов по ИНН или комбинации ФИО и даты рождения"""
        # Удаление полных дубликатов
        df = df.drop_duplicates()
        
        # Удаление по ИНН
        if 'inn' in df.columns:
            df = df.drop_duplicates(subset=['inn'], keep='first')
        
        # Удаление по ФИО и дате рождения
        if 'fio' in df.columns and 'dob' in df.columns:
            df = df.drop_duplicates(subset=['fio', 'dob'], keep='first')
        
        return df
    
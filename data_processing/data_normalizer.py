import re
import phonenumbers
import pandas as pd
from datetime import datetime

class DataNormalizer:
    def __init__(self):
        self.region_mapping = {
            'москва': 'Москва',
            'санкт-петербург': 'Санкт-Петербург',
            'татарстан': 'Татарстан',
            'саратов': 'Саратов',
            'калуга': 'Калуга',
            'московская область': 'Московская область',
            'краснодарский край': 'Краснодарский край',
            'свердловская область': 'Свердловская область'
        }
    
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализация данных в DataFrame"""
        # Применение функций нормализации к каждому столбцу
        if 'phone' in df.columns:
            df['phone'] = df['phone'].apply(self.normalize_phone)
        
        if 'fio' in df.columns:
            df['fio'] = df['fio'].apply(self.normalize_fio)
        
        if 'dob' in df.columns:
            df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
        
        if 'address' in df.columns:
            df['region'] = df['address'].apply(self.extract_region)
        
        if 'source_file' in df.columns:
            df['source'] = df['source_file'].apply(self.detect_source)
            df['tags'] = df['source'].apply(self.get_tags)
        
        return df.dropna(subset=['fio', 'phone'])

    def normalize_phone(self, phone: str) -> str:
        """Нормализация телефона в формат +7XXXXXXXXXX"""
        if pd.isna(phone) or not phone:
            return None
        
        try:
            # Удаление всех нецифровых символов, кроме плюса
            phone = re.sub(r'[^\d+]', '', str(phone))
            
            # Обработка российских номеров
            if phone.startswith('8') and len(phone) == 11:
                return '+7' + phone[1:]
            elif phone.startswith('7') and len(phone) == 11:
                return '+' + phone
            elif len(phone) == 10:
                return '+7' + phone
            elif phone.startswith('+7') and len(phone) == 12:
                return phone
            
            # Попытка парсинга библиотекой
            parsed = phonenumbers.parse(phone, "RU")
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, 
                    phonenumbers.PhoneNumberFormat.E164
                )
            
            return None
        except:
            return None

    def normalize_fio(self, fio: str) -> str:
        """Нормализация ФИО: приведение к верхнему регистру и удаление лишних пробелов"""
        if pd.isna(fio) or not fio:
            return None
        
        # Удаление лишних пробелов и приведение к верхнему регистру
        fio = ' '.join(str(fio).strip().split()).upper()
        
        # Удаление некириллических символов (кроме пробела и дефиса)
        fio = re.sub(r'[^А-ЯЁ\s-]', '', fio)
        
        return fio if len(fio) > 2 else None

    def extract_region(self, address: str) -> str:
        """Извлечение региона из адреса"""
        if pd.isna(address) or not address or address == 'nan':
            return None
        
        address_lower = str(address).lower()
        
        # Поиск региона в адресе
        for region_pattern, region_name in self.region_mapping.items():
            if region_pattern in address_lower:
                return region_name
        
        return None

    def detect_source(self, filename: str) -> str:
        """Определение источника по имени файла"""
        if pd.isna(filename) or not filename:
            return 'Другое'
        
        filename_lower = filename.lower()
        
        if 'fns' in filename_lower or 'налог' in filename_lower:
            return 'ФНС'
        elif 'gosuslugi' in filename_lower or 'госуслуги' in filename_lower:
            return 'Госуслуги'
        elif 'food' in filename_lower or 'еда' in filename_lower or 'доставка' in filename_lower:
            return 'Доставка еды'
        else:
            return 'Другое'

    def get_tags(self, source: str) -> str:
        """Получение тегов на основе источника"""
        if source == 'ФНС':
            return 'налоговая'
        elif source == 'Госуслуги':
            return 'госуслуги'
        elif source == 'Доставка еды':
            return 'еда'
        else:
            return 'другое'
        
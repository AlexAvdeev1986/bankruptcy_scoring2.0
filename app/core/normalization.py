import pandas as pd
import re
import phonenumbers
from typing import List, Dict, Optional, Tuple
from unidecode import unidecode
from fuzzywuzzy import fuzz, process
import hashlib
import uuid
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

class DataNormalizer:
    """Класс для нормализации и объединения данных из разных CSV файлов"""
    
    def __init__(self):
        self.normalized_data = pd.DataFrame()
        self.duplicates_removed = 0
        self.errors = []
    
    def normalize_csv_files(self, csv_files: List[str]) -> pd.DataFrame:
        """Основной метод нормализации CSV файлов"""
        all_dataframes = []
        
        for csv_file in csv_files:
            try:
                df = self._load_and_normalize_csv(csv_file)
                if not df.empty:
                    all_dataframes.append(df)
                    logger.info(f"Загружен файл {csv_file}, записей: {len(df)}")
            except Exception as e:
                error_msg = f"Ошибка при обработке файла {csv_file}: {str(e)}"
                self.errors.append(error_msg)
                logger.error(error_msg)
        
        if not all_dataframes:
            logger.error("Не удалось загрузить ни одного файла")
            return pd.DataFrame()
        
        # Объединяем все данные
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"Объединено записей: {len(combined_df)}")
        
        # Удаляем дубликаты
        deduplicated_df = self._remove_duplicates(combined_df)
        logger.info(f"После удаления дубликатов: {len(deduplicated_df)}")
        
        # Финальная нормализация
        self.normalized_data = self._final_normalization(deduplicated_df)
        
        return self.normalized_data
    
    def _load_and_normalize_csv(self, csv_file: str) -> pd.DataFrame:
        """Загрузка и нормализация одного CSV файла"""
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'cp1251', 'latin1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(csv_file, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise Exception("Не удалось определить кодировку файла")
            
            # Определяем тип источника по имени файла или структуре
            source_type = self._detect_source_type(csv_file, df.columns.tolist())
            
            # Нормализуем данные в зависимости от источника
            normalized_df = self._normalize_by_source_type(df, source_type)
            
            return normalized_df
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке {csv_file}: {str(e)}")
            raise
    
    def _detect_source_type(self, filename: str, columns: List[str]) -> str:
        """Определение типа источника данных"""
        filename_lower = filename.lower()
        columns_lower = [col.lower() for col in columns]
        
        if 'фнс' in filename_lower or 'fns' in filename_lower:
            return 'fns'
        elif 'госуслуги' in filename_lower or 'gosuslugi' in filename_lower:
            return 'gosuslugi'
        elif 'доставка' in filename_lower or 'delivery' in filename_lower or 'еда' in filename_lower:
            return 'delivery'
        elif any('инн' in col for col in columns_lower):
            return 'inn_based'
        elif any('телефон' in col or 'phone' in col for col in columns_lower):
            return 'phone_based'
        else:
            return 'generic'
    
    def _normalize_by_source_type(self, df: pd.DataFrame, source_type: str) -> pd.DataFrame:
        """Нормализация данных в зависимости от типа источника"""
        
        # Словари соответствия колонок для разных источников
        column_mappings = {
            'fns': {
                'инн': 'inn',
                'фио': 'fio', 
                'фамилия имя отчество': 'fio',
                'телефон': 'phone',
                'phone': 'phone'
            },
            'gosuslugi': {
                'инн': 'inn',
                'фио': 'fio',
                'адрес': 'address',
                'телефон': 'phone',
                'email': 'email'
            },
            'delivery': {
                'телефон': 'phone',
                'phone': 'phone',
                'адрес': 'address', 
                'address': 'address'
            },
            'generic': {
                'фио': 'fio',
                'fio': 'fio',
                'имя': 'fio',
                'name': 'fio',
                'телефон': 'phone',
                'phone': 'phone',
                'инн': 'inn',
                'inn': 'inn',
                'адрес': 'address',
                'address': 'address',
                'email': 'email',
                'дата_рождения': 'dob',
                'date_birth': 'dob'
            }
        }
        
        # Получаем маппинг для текущего источника
        mapping = column_mappings.get(source_type, column_mappings['generic'])
        
        # Создаем нормализованный DataFrame
        normalized_columns = {
            'lead_id': '',
            'fio': '',
            'phone': '',
            'inn': '',
            'dob': '',
            'address': '',
            'source': source_type,
            'tags': source_type,
            'email': '',
            'created_at': pd.Timestamp.now()
        }
        
        result_df = pd.DataFrame(columns=normalized_columns.keys())
        
        # Заполняем данные
        for i, row in df.iterrows():
            normalized_row = normalized_columns.copy()
            
            # Маппинг колонок
            for original_col, normalized_col in mapping.items():
                for col in df.columns:
                    if original_col.lower() in col.lower():
                        value = row[col]
                        if pd.notna(value):
                            if normalized_col == 'phone':
                                normalized_row[normalized_col] = self._normalize_phone(str(value))
                            elif normalized_col == 'fio':
                                normalized_row[normalized_col] = self._normalize_fio(str(value))
                            elif normalized_col == 'inn':
                                normalized_row[normalized_col] = self._normalize_inn(str(value))
                            else:
                                normalized_row[normalized_col] = str(value).strip()
                        break
            
            # Генерируем lead_id
            normalized_row['lead_id'] = self._generate_lead_id(normalized_row)
            
            result_df = pd.concat([result_df, pd.DataFrame([normalized_row])], ignore_index=True)
        
        return result_df
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализация телефона в формат +7XXXXXXXXXX"""
        if not phone or phone == 'nan':
            return ''
        
        # Убираем все не-цифры
        digits = re.sub(r'\D', '', str(phone))
        
        if not digits:
            return ''
        
        # Приводим к формату +7XXXXXXXXXX
        if len(digits) == 11 and digits.startswith('8'):
            return '+7' + digits[1:]
        elif len(digits) == 11 and digits.startswith('7'):
            return '+' + digits
        elif len(digits) == 10:
            return '+7' + digits
        elif len(digits) == 11 and digits.startswith('7'):
            return '+' + digits
        
        # Валидация через phonenumbers
        try:
            parsed = phonenumbers.parse(phone, 'RU')
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            pass
        
        return ''
    
    def _normalize_fio(self, fio: str) -> str:
        """Нормализация ФИО"""
        if not fio or fio == 'nan':
            return ''
        
        # Убираем лишние пробелы и приводим к единому регистру
        fio = ' '.join(str(fio).strip().split())
        fio = fio.title()
        
        # Убираем спецсимволы
        fio = re.sub(r'[^\w\s\-]', '', fio, flags=re.UNICODE)
        
        return fio
    
    def _normalize_inn(self, inn: str) -> str:
        """Нормализация ИНН"""
        if not inn or inn == 'nan':
            return ''
        
        # Убираем все не-цифры
        inn = re.sub(r'\D', '', str(inn))
        
        # Проверяем длину (для физлиц должно быть 12 цифр)
        if len(inn) == 12:
            return inn
        elif len(inn) == 10:  # ИНН юрлица, может быть у ИП
            return inn
        
        return ''
    
    def _generate_lead_id(self, row: Dict) -> str:
        """Генерация уникального ID для лида"""
        # Используем комбинацию ФИО + телефон + ИНН для уникальности
        unique_string = f"{row.get('fio', '')}{row.get('phone', '')}{row.get('inn', '')}"
        
        if unique_string.strip():
            # Создаем hash от строки
            hash_object = hashlib.md5(unique_string.encode())
            return hash_object.hexdigest()[:16]
        else:
            # Если нет данных для hash, генерируем случайный UUID
            return str(uuid.uuid4())[:16]
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Удаление дубликатов по ФИО+дата рождения или по ИНН"""
        initial_count = len(df)
        
        # Сначала удаляем точные дубликаты по lead_id
        df_dedup = df.drop_duplicates(subset=['lead_id'], keep='first')
        
        # Затем удаляем дубликаты по ИНН (если есть)
        df_inn = df_dedup[df_dedup['inn'].notna() & (df_dedup['inn'] != '')]
        df_no_inn = df_dedup[df_dedup['inn'].isna() | (df_dedup['inn'] == '')]
        
        if not df_inn.empty:
            df_inn = df_inn.drop_duplicates(subset=['inn'], keep='first')
        
        # Для записей без ИНН удаляем дубликаты по ФИО + дата рождения
        if not df_no_inn.empty:
            # Создаем составной ключ для поиска дубликатов
            df_no_inn['dup_key'] = df_no_inn['fio'].fillna('') + '|' + df_no_inn['dob'].fillna('')
            df_no_inn = df_no_inn.drop_duplicates(subset=['dup_key'], keep='first')
            df_no_inn = df_no_inn.drop(['dup_key'], axis=1)
        
        # Объединяем обратно
        result_df = pd.concat([df_inn, df_no_inn], ignore_index=True)
        
        self.duplicates_removed = initial_count - len(result_df)
        logger.info(f"Удалено дубликатов: {self.duplicates_removed}")
        
        return result_df
    
    def _final_normalization(self, df: pd.DataFrame) -> pd.DataFrame:
        """Финальная нормализация данных"""
        # Заполняем пустые значения
        df['fio'] = df['fio'].fillna('')
        df['phone'] = df['phone'].fillna('')
        df['inn'] = df['inn'].fillna('')
        df['address'] = df['address'].fillna('')
        df['email'] = df['email'].fillna('')
        df['dob'] = df['dob'].fillna('')
        
        # Удаляем записи без ключевых данных (ни ФИО, ни телефона, ни ИНН)
        df = df[
            (df['fio'] != '') | 
            (df['phone'] != '') | 
            (df['inn'] != '')
        ]
        
        # Определяем регион по адресу или телефону
        df['region'] = df.apply(self._extract_region, axis=1)
        
        # Сортируем по дате создания
        df = df.sort_values('created_at')
        
        logger.info(f"Финальная нормализация завершена. Записей: {len(df)}")
        
        return df
    
    def _extract_region(self, row: pd.Series) -> str:
        """Извлечение региона из адреса или телефона"""
        address = str(row.get('address', '')).lower()
        phone = str(row.get('phone', ''))
        
        # Словарь регионов и их идентификаторов
        regions_map = {
            'москва': 'Москва',
            'moscow': 'Москва', 
            'санкт-петербург': 'Санкт-Петербург',
            'спб': 'Санкт-Петербург',
            'петербург': 'Санкт-Петербург',
            'татарстан': 'Татарстан',
            'казань': 'Татарстан',
            'саратов': 'Саратов',
            'калуга': 'Калуга',
            'краснодар': 'Краснодар',
            'екатеринбург': 'Екатеринбург',
            'новосибирск': 'Новосибирск'
        }
        
        # Поиск по адресу
        for key, region in regions_map.items():
            if key in address:
                return region
        
        # Определение региона по коду телефона (примеры)
        phone_regions = {
            '+7495': 'Москва',
            '+7499': 'Москва', 
            '+7812': 'Санкт-Петербург',
            '+7843': 'Татарстан',
            '+7845': 'Саратов',
            '+7484': 'Калуга',
            '+7861': 'Краснодар',
            '+7343': 'Екатеринбург',
            '+7383': 'Новосибирск'
        }
        
        for code, region in phone_regions.items():
            if phone.startswith(code):
                return region
        
        return 'Не определен'
    
    def get_statistics(self) -> Dict:
        """Получение статистики по нормализации"""
        if self.normalized_data.empty:
            return {}
        
        stats = {
            'total_records': len(self.normalized_data),
            'duplicates_removed': self.duplicates_removed,
            'errors_count': len(self.errors),
            'regions_distribution': self.normalized_data['region'].value_counts().to_dict(),
            'sources_distribution': self.normalized_data['source'].value_counts().to_dict(),
            'phone_coverage': (self.normalized_data['phone'] != '').sum(),
            'inn_coverage': (self.normalized_data['inn'] != '').sum(),
            'email_coverage': (self.normalized_data['email'] != '').sum(),
            'errors': self.errors
        }
        
        return stats
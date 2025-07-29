"""
Парсер для работы с Росреестром (Федеральная служба государственной регистрации,
кадастра и картографии)
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseParser


class RosreestrParser(BaseParser):
    """Парсер для получения данных из Росреестра"""
    
    def __init__(self, proxy_manager=None, delay: float = 2.0):
        super().__init__(proxy_manager, delay)
        self.base_url = "https://rosreestr.gov.ru"
        self.api_url = "https://rosreestr.gov.ru/api"
        self.search_url = "https://rosreestr.gov.ru/api/online/fir_obj/"
        self.logger = logging.getLogger(__name__)

    async def search_by_cadastral_number(self, cadastral_number: str) -> Optional[Dict[str, Any]]:
        """
        Поиск объекта недвижимости по кадастровому номеру
        
        Args:
            cadastral_number: Кадастровый номер объекта
            
        Returns:
            Информация об объекте недвижимости
        """
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://rosreestr.gov.ru/',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Форматирование кадастрового номера
            formatted_number = self._format_cadastral_number(cadastral_number)
            
            search_url = f"{self.search_url}{formatted_number}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_cadastral_info(data, cadastral_number)
                    else:
                        self.logger.error(f"Ошибка поиска в Росреестр: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Ошибка при поиске по кадастровому номеру {cadastral_number}: {e}")
            return None

    async def search_property_by_owner(self, owner_name: str, region: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Поиск недвижимости по владельцу (ограниченный функционал через публичную кадастровую карту)
        
        Args:
            owner_name: Имя владельца
            region: Регион поиска
            
        Returns:
            Список найденных объектов недвижимости
        """
        try:
            # Примечание: Полноценный поиск по владельцу требует специального доступа
            # Здесь реализован базовый функционал через публичные источники
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://rosreestr.gov.ru/'
            }
            
            # Поиск через публичную кадастровую карту (ограниченный функционал)
            map_url = "https://pkk.rosreestr.ru/"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    map_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        # Здесь должна быть логика поиска через карту
                        # В реальном проекте может потребоваться использование специальных API
                        self.logger.warning("Поиск по владельцу через публичные источники ограничен")
                        return []
                    else:
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка при поиске по владельцу {owner_name}: {e}")
            return []

    async def get_property_details(self, cadastral_number: str) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации об объекте недвижимости
        
        Args:
            cadastral_number: Кадастровый номер
            
        Returns:
            Детальная информация об объекте
        """
        basic_info = await self.search_by_cadastral_number(cadastral_number)
        
        if not basic_info:
            return None
            
        # Дополнительные запросы для получения истории и других данных
        try:
            details = basic_info.copy()
            
            # Получение дополнительной информации
            additional_info = await self._get_additional_property_info(cadastral_number)
            if additional_info:
                details.update(additional_info)
            
            return details
            
        except Exception as e:
            self.logger.error(f"Ошибка получения деталей объекта {cadastral_number}: {e}")
            return basic_info

    async def get_property_history(self, cadastral_number: str) -> List[Dict[str, Any]]:
        """
        Получение истории изменений объекта недвижимости
        
        Args:
            cadastral_number: Кадастровый номер
            
        Returns:
            История изменений объекта
        """
        try:
            # Примечание: История доступна через специальные запросы
            history_url = f"{self.api_url}/online/fir_obj/{cadastral_number}/history"
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json',
                'Referer': 'https://rosreestr.gov.ru/'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    history_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_property_history(data)
                    else:
                        self.logger.warning(f"История недоступна для объекта {cadastral_number}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка получения истории объекта {cadastral_number}: {e}")
            return []

    async def check_encumbrances(self, cadastral_number: str) -> List[Dict[str, Any]]:
        """
        Проверка обременений объекта недвижимости
        
        Args:
            cadastral_number: Кадастровый номер
            
        Returns:
            Список обременений
        """
        try:
            encumbrance_url = f"{self.api_url}/online/fir_obj/{cadastral_number}/encumbrance"
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json',
                'Referer': 'https://rosreestr.gov.ru/'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    encumbrance_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_encumbrances(data)
                    else:
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка проверки обременений объекта {cadastral_number}: {e}")
            return []

    def _format_cadastral_number(self, cadastral_number: str) -> str:
        """Форматирование кадастрового номера"""
        # Удаляем все кроме цифр и двоеточий
        formatted = re.sub(r'[^\d:]', '', cadastral_number)
        return formatted

    async def _process_cadastral_info(self, data: Dict, cadastral_number: str) -> Dict[str, Any]:
        """Обработка информации об объекте недвижимости"""
        try:
            processed = {
                'cadastral_number': cadastral_number,
                'object_type': data.get('objectType'),
                'purpose': data.get('purpose'),
                'address': data.get('address'),
                'area': data.get('area'),
                'cadastral_cost': data.get('cadastralCost'),
                'registration_date': data.get('registrationDate'),
                'status': data.get('status'),
                'rights': [],
                'encumbrances': [],
                'coordinates': data.get('coordinates'),
                'source': 'rosreestr'
            }
            
            # Обработка прав
            if 'rights' in data:
                for right in data['rights']:
                    processed['rights'].append({
                        'type': right.get('type'),
                        'owner': right.get('owner'),
                        'registration_date': right.get('registrationDate'),
                        'registration_number': right.get('registrationNumber'),
                        'share': right.get('share')
                    })
            
            # Обработка обременений
            if 'encumbrances' in data:
                for encumbrance in data['encumbrances']:
                    processed['encumbrances'].append({
                        'type': encumbrance.get('type'),
                        'holder': encumbrance.get('holder'),
                        'registration_date': encumbrance.get('registrationDate'),
                        'registration_number': encumbrance.get('registrationNumber'),
                        'description': encumbrance.get('description')
                    })
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки кадастровой информации: {e}")
            return {
                'cadastral_number': cadastral_number,
                'error': str(e),
                'source': 'rosreestr'
            }

    async def _get_additional_property_info(self, cadastral_number: str) -> Optional[Dict[str, Any]]:
        """Получение дополнительной информации об объекте"""
        try:
            # Запрос технических характеристик
            tech_url = f"{self.api_url}/online/fir_obj/{cadastral_number}/tech"
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json',
                'Referer': 'https://rosreestr.gov.ru/'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    tech_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'technical_info': data,
                            'building_year': data.get('buildingYear'),
                            'material': data.get('material'),
                            'floors': data.get('floors'),
                            'condition': data.get('condition')
                        }
                    else:
                        return None
                        
        except Exception as e:
            self.logger.error(f"Ошибка получения дополнительной информации: {e}")
            return None

    async def _process_property_history(self, data: Dict) -> List[Dict[str, Any]]:
        """Обработка истории изменений объекта"""
        history = []
        
        try:
            if 'history' in data:
                for record in data['history']:
                    history_item = {
                        'date': record.get('date'),
                        'operation_type': record.get('operationType'),
                        'description': record.get('description'),
                        'document_type': record.get('documentType'),
                        'document_number': record.get('documentNumber'),
                        'previous_owner': record.get('previousOwner'),
                        'new_owner': record.get('newOwner'),
                        'source': 'rosreestr'
                    }
                    history.append(history_item)
                    
        except Exception as e:
            self.logger.error(f"Ошибка обработки истории объекта: {e}")
            
        return history

    async def _process_encumbrances(self, data: Dict) -> List[Dict[str, Any]]:
        """Обработка обременений объекта"""
        encumbrances = []
        
        try:
            if 'encumbrances' in data:
                for encumbrance in data['encumbrances']:
                    encumbrance_item = {
                        'type': encumbrance.get('type'),
                        'holder': encumbrance.get('holder'),
                        'registration_date': encumbrance.get('registrationDate'),
                        'registration_number': encumbrance.get('registrationNumber'),
                        'description': encumbrance.get('description'),
                        'document_info': encumbrance.get('documentInfo'),
                        'is_active': encumbrance.get('isActive', True),
                        'source': 'rosreestr'
                    }
                    encumbrances.append(encumbrance_item)
                    
        except Exception as e:
            self.logger.error(f"Ошибка обработки обременений: {e}")
            
        return encumbrances

    async def get_analytics_data(self, cadastral_numbers: List[str]) -> Dict[str, Any]:
        """
        Получение аналитических данных для скоринга
        
        Args:
            cadastral_numbers: Список кадастровых номеров для анализа
            
        Returns:
            Аналитические данные по недвижимости
        """
        analytics = {
            'total_properties': len(cadastral_numbers),
            'valid_properties': 0,
            'total_cadastral_value': 0,
            'properties_with_encumbrances': 0,
            'encumbrance_types': [],
            'property_types': {},
            'risk_factors': [],
            'source': 'rosreestr'
        }
        
        for cadastral_number in cadastral_numbers:
            try:
                property_info = await self.get_property_details(cadastral_number)
                
                if property_info and 'error' not in property_info:
                    analytics['valid_properties'] += 1
                    
                    # Кадастровая стоимость
                    cadastral_cost = property_info.get('cadastral_cost')
                    if cadastral_cost and isinstance(cadastral_cost, (int, float)):
                        analytics['total_cadastral_value'] += cadastral_cost
                    
                    # Типы недвижимости
                    obj_type = property_info.get('object_type')
                    if obj_type:
                        analytics['property_types'][obj_type] = analytics['property_types'].get(obj_type, 0) + 1
                    
                    # Обременения
                    encumbrances = property_info.get('encumbrances', [])
                    if encumbrances:
                        analytics['properties_with_encumbrances'] += 1
                        
                        for enc in encumbrances:
                            enc_type = enc.get('type')
                            if enc_type and enc_type not in analytics['encumbrance_types']:
                                analytics['encumbrance_types'].append(enc_type)
                                
                            # Факторы риска на основе обременений
                            if enc_type in ['Ипотека', 'Залог']:
                                analytics['risk_factors'].append(f'Залоговое обременение: {cadastral_number}')
                            elif enc_type in ['Арест', 'Запрет на совершение сделок']:
                                analytics['risk_factors'].append(f'Арест/запрет: {cadastral_number}')
                
                await asyncio.sleep(self.delay)
                
            except Exception as e:
                self.logger.error(f"Ошибка анализа объекта {cadastral_number}: {e}")
        
        # Расчет дополнительных метрик
        if analytics['valid_properties'] > 0:
            analytics['avg_cadastral_value'] = analytics['total_cadastral_value'] / analytics['valid_properties']
            analytics['encumbrance_ratio'] = analytics['properties_with_encumbrances'] / analytics['valid_properties']
        else:
            analytics['avg_cadastral_value'] = 0
            analytics['encumbrance_ratio'] = 0
            
        return analytics

    async def check_connection(self) -> bool:
        """Проверка доступности сервиса"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    timeout=aiohttp.ClientTimeout(total=10),
                    proxy=await self.get_proxy()
                ) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Ошибка проверки подключения к Росреестр: {e}")
            return False
        
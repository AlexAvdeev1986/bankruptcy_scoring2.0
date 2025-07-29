"""
Парсер для работы с Федресурс (Единый федеральный реестр сведений о банкротстве)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseParser


class FedresursParser(BaseParser):
    """Парсер для получения данных о банкротстве из Федресурс"""
    
    def __init__(self, proxy_manager=None, delay: float = 1.0):
        super().__init__(proxy_manager, delay)
        self.base_url = "https://fedresurs.ru"
        self.api_url = "https://fedresurs.ru/backend"
        self.search_url = f"{self.api_url}/persons"
        self.logger = logging.getLogger(__name__)

    async def search_by_inn(self, inn: str) -> List[Dict[str, Any]]:
        """
        Поиск данных по ИНН
        
        Args:
            inn: ИНН организации или ИП
            
        Returns:
            Список найденных записей о банкротстве
        """
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Content-Type': 'application/json',
                'Referer': 'https://fedresurs.ru/',
            }
            
            # Параметры поиска
            search_params = {
                "searchType": "parties",
                "isActive": None,
                "regionId": None,
                "inn": inn,
                "ogrnip": None,
                "snils": None,
                "code": None,
                "name": None,
                "address": None,
                "publishDateFrom": None,
                "publishDateTo": None,
                "orderBy": "relevance",
                "isAscending": False,
                "limit": 50,
                "offset": 0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.search_url,
                    json=search_params,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_search_results(data)
                    else:
                        self.logger.error(f"Ошибка поиска в Федресурс: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка при поиске в Федресурс по ИНН {inn}: {e}")
            return []

    async def search_by_name(self, name: str, region_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Поиск данных по наименованию
        
        Args:
            name: Наименование организации
            region_id: ID региона (опционально)
            
        Returns:
            Список найденных записей о банкротстве
        """
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Content-Type': 'application/json',
                'Referer': 'https://fedresurs.ru/',
            }
            
            search_params = {
                "searchType": "parties",
                "isActive": None,
                "regionId": region_id,
                "inn": None,
                "ogrnip": None,
                "snils": None,
                "code": None,
                "name": name,
                "address": None,
                "publishDateFrom": None,
                "publishDateTo": None,
                "orderBy": "relevance",
                "isAscending": False,
                "limit": 50,
                "offset": 0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.search_url,
                    json=search_params,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_search_results(data)
                    else:
                        self.logger.error(f"Ошибка поиска в Федресурс: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка при поиске в Федресурс по наименованию {name}: {e}")
            return []

    async def get_bankruptcy_details(self, guid: str) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о деле о банкротстве
        
        Args:
            guid: GUID дела
            
        Returns:
            Детальная информация о банкротстве
        """
        try:
            details_url = f"{self.api_url}/bankruptcy/{guid}"
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://fedresurs.ru/',
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    details_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_bankruptcy_details(data)
                    else:
                        self.logger.error(f"Ошибка получения деталей дела {guid}: {response.status}")
                        return None
                        
        except Exception as e:
            self.logger.error(f"Ошибка при получении деталей дела {guid}: {e}")
            return None

    async def get_messages(self, guid: str) -> List[Dict[str, Any]]:
        """
        Получение сообщений по делу о банкротстве
        
        Args:
            guid: GUID дела
            
        Returns:
            Список сообщений по делу
        """
        try:
            messages_url = f"{self.api_url}/messages"
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Content-Type': 'application/json',
                'Referer': 'https://fedresurs.ru/',
            }
            
            params = {
                "searchType": "messages",
                "bankruptcyId": guid,
                "limit": 100,
                "offset": 0,
                "orderBy": "publishDate",
                "isAscending": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    messages_url,
                    json=params,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        return await self._process_messages(data)
                    else:
                        self.logger.error(f"Ошибка получения сообщений дела {guid}: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка при получении сообщений дела {guid}: {e}")
            return []

    async def _process_search_results(self, data: Dict) -> List[Dict[str, Any]]:
        """Обработка результатов поиска"""
        results = []
        
        try:
            if 'data' in data and 'searchResult' in data['data']:
                for item in data['data']['searchResult']:
                    processed_item = {
                        'guid': item.get('guid'),
                        'inn': item.get('inn'),
                        'ogrn': item.get('ogrn'),
                        'name': item.get('name'),
                        'address': item.get('address'),
                        'region': item.get('region', {}).get('name'),
                        'arbitr_court': item.get('court', {}).get('name'),
                        'case_number': item.get('caseNumber'),
                        'manager_name': item.get('managerName'),
                        'status': item.get('status', {}).get('name'),
                        'publish_date': item.get('publishDate'),
                        'is_active': item.get('isActive'),
                        'bankruptcy_stage': item.get('bankruptcyStage', {}).get('name'),
                        'source': 'fedresurs'
                    }
                    results.append(processed_item)
                    
        except Exception as e:
            self.logger.error(f"Ошибка обработки результатов поиска: {e}")
            
        return results

    async def _process_bankruptcy_details(self, data: Dict) -> Dict[str, Any]:
        """Обработка детальной информации о банкротстве"""
        try:
            return {
                'guid': data.get('guid'),
                'case_number': data.get('caseNumber'),
                'debtor_info': {
                    'name': data.get('debtor', {}).get('name'),
                    'inn': data.get('debtor', {}).get('inn'),
                    'ogrn': data.get('debtor', {}).get('ogrn'),
                    'address': data.get('debtor', {}).get('address'),
                },
                'court_info': {
                    'name': data.get('court', {}).get('name'),
                    'address': data.get('court', {}).get('address'),
                },
                'manager_info': {
                    'name': data.get('manager', {}).get('name'),
                    'sro': data.get('manager', {}).get('sro'),
                    'contact': data.get('manager', {}).get('contact'),
                },
                'dates': {
                    'case_start': data.get('caseStartDate'),
                    'bankruptcy_start': data.get('bankruptcyStartDate'),
                    'completion_date': data.get('completionDate'),
                },
                'status': data.get('status', {}).get('name'),
                'stage': data.get('bankruptcyStage', {}).get('name'),
                'is_active': data.get('isActive'),
                'source': 'fedresurs'
            }
        except Exception as e:
            self.logger.error(f"Ошибка обработки деталей банкротства: {e}")
            return {}

    async def _process_messages(self, data: Dict) -> List[Dict[str, Any]]:
        """Обработка сообщений по делу"""
        messages = []
        
        try:
            if 'data' in data and 'searchResult' in data['data']:
                for message in data['data']['searchResult']:
                    processed_message = {
                        'id': message.get('id'),
                        'title': message.get('title'),
                        'content': message.get('content'),
                        'publish_date': message.get('publishDate'),
                        'message_type': message.get('messageType', {}).get('name'),
                        'attachments': [
                            {
                                'name': att.get('name'),
                                'url': att.get('url'),
                                'size': att.get('size')
                            }
                            for att in message.get('attachments', [])
                        ],
                        'source': 'fedresurs'
                    }
                    messages.append(processed_message)
                    
        except Exception as e:
            self.logger.error(f"Ошибка обработки сообщений: {e}")
            
        return messages

    async def get_analytics_data(self, inn: str) -> Dict[str, Any]:
        """
        Получение аналитических данных для скоринга
        
        Args:
            inn: ИНН для анализа
            
        Returns:
            Аналитические данные
        """
        bankruptcy_data = await self.search_by_inn(inn)
        
        analytics = {
            'has_bankruptcy_history': len(bankruptcy_data) > 0,
            'bankruptcy_cases_count': len(bankruptcy_data),
            'active_bankruptcy_cases': 0,
            'completed_bankruptcy_cases': 0,
            'latest_case_date': None,
            'stages_history': [],
            'risk_factors': [],
            'source': 'fedresurs'
        }
        
        if bankruptcy_data:
            for case in bankruptcy_data:
                # Подсчет активных и завершенных дел
                if case.get('is_active'):
                    analytics['active_bankruptcy_cases'] += 1
                else:
                    analytics['completed_bankruptcy_cases'] += 1
                
                # Определение последней даты
                publish_date = case.get('publish_date')
                if publish_date:
                    case_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                    if not analytics['latest_case_date'] or case_date > analytics['latest_case_date']:
                        analytics['latest_case_date'] = case_date
                
                # Сбор стадий банкротства
                stage = case.get('bankruptcy_stage')
                if stage and stage not in analytics['stages_history']:
                    analytics['stages_history'].append(stage)
            
            # Определение факторов риска
            if analytics['active_bankruptcy_cases'] > 0:
                analytics['risk_factors'].append('Активное банкротство')
            
            if analytics['bankruptcy_cases_count'] > 1:
                analytics['risk_factors'].append('Множественные банкротства')
            
            if analytics['latest_case_date']:
                days_since_last = (datetime.now() - analytics['latest_case_date'].replace(tzinfo=None)).days
                if days_since_last < 365:
                    analytics['risk_factors'].append('Недавнее банкротство')
        
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
            self.logger.error(f"Ошибка проверки подключения к Федресурс: {e}")
            return False
        
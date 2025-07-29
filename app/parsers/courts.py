"""
Парсер для работы с судебными системами (ГАС РФ "Правосудие", картотека арбитражных дел)
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote, urlencode

import aiohttp
from bs4 import BeautifulSoup

from .base import BaseParser


class CourtsParser(BaseParser):
    """Парсер для получения данных из судебных систем"""
    
    def __init__(self, proxy_manager=None, delay: float = 3.0):
        super().__init__(proxy_manager, delay)
        self.arbitrage_url = "https://kad.arbitr.ru"
        self.pravosudiye_url = "https://sudrf.ru"
        self.kad_search_url = "https://kad.arbitr.ru/Kad/SearchInstances"
        self.logger = logging.getLogger(__name__)

    async def search_arbitrage_cases(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Поиск арбитражных дел
        
        Args:
            query_params: Параметры поиска (INN, название, номер дела и т.д.)
            
        Returns:
            Список найденных дел
        """
        try:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://kad.arbitr.ru/'
            }
            
            # Подготовка параметров поиска
            search_data = await self._prepare_arbitrage_search_params(query_params)
            
            async with aiohttp.ClientSession() as session:
                # Сначала получаем форму поиска для извлечения токенов
                async with session.get(
                    f"{self.arbitrage_url}/Kad/SearchInstances",
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status != 200:
                        self.logger.error(f"Ошибка получения формы поиска: {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Извлечение необходимых токенов
                    tokens = self._extract_form_tokens(soup)
                    search_data.update(tokens)
                
                # Выполнение поиска
                async with session.post(
                    self.kad_search_url,
                    data=search_data,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        html = await response.text()
                        return await self._parse_arbitrage_results(html)
                    else:
                        self.logger.error(f"Ошибка поиска арбитражных дел: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка при поиске арбитражных дел: {e}")
            return []

    async def search_by_inn(self, inn: str, court_type: str = "arbitrage") -> List[Dict[str, Any]]:
        """
        Поиск дел по ИНН
        
        Args:
            inn: ИНН организации
            court_type: Тип суда (arbitrage, general)
            
        Returns:
            Список найденных дел
        """
        if court_type == "arbitrage":
            return await self.search_arbitrage_cases({"inn": inn})
        elif court_type == "general":
            return await self.search_general_cases({"inn": inn})
        else:
            # Поиск в обеих системах
            arbitrage_cases = await self.search_arbitrage_cases({"inn": inn})
            general_cases = await self.search_general_cases({"inn": inn})
            return arbitrage_cases + general_cases

    async def search_by_name(self, name: str, court_type: str = "arbitrage") -> List[Dict[str, Any]]:
        """
        Поиск дел по наименованию организации
        
        Args:
            name: Наименование организации
            court_type: Тип суда
            
        Returns:
            Список найденных дел
        """
        if court_type == "arbitrage":
            return await self.search_arbitrage_cases({"name": name})
        elif court_type == "general":
            return await self.search_general_cases({"name": name})
        else:
            arbitrage_cases = await self.search_arbitrage_cases({"name": name})
            general_cases = await self.search_general_cases({"name": name})
            return arbitrage_cases + general_cases

    async def search_general_cases(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Поиск дел в судах общей юрисдикции
        
        Args:
            query_params: Параметры поиска
            
        Returns:
            Список найденных дел
        """
        try:
            # Примечание: Поиск в судах общей юрисдикции сложнее из-за разнообразия региональных систем
            # Здесь реализован базовый функционал для основных регионов
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://sudrf.ru/'
            }
            
            # Поиск через федеральный портал
            search_url = f"{self.pravosudiye_url}/index.php?id=300"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        html = await response.text()
                        # В реальном проекте здесь должна быть детальная обработка
                        # различных региональных систем
                        return await self._parse_general_courts_results(html, query_params)
                    else:
                        self.logger.error(f"Ошибка поиска в судах общей юрисдикции: {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Ошибка при поиске в судах общей юрисдикции: {e}")
            return []

    async def get_case_details(self, case_id: str, court_type: str = "arbitrage") -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о деле
        
        Args:
            case_id: ID дела
            court_type: Тип суда
            
        Returns:
            Детальная информация о деле
        """
        try:
            if court_type == "arbitrage":
                return await self._get_arbitrage_case_details(case_id)
            else:
                return await self._get_general_case_details(case_id)
                
        except Exception as e:
            self.logger.error(f"Ошибка получения деталей дела {case_id}: {e}")
            return None

    async def _prepare_arbitrage_search_params(self, query_params: Dict[str, Any]) -> Dict[str, str]:
        """Подготовка параметров для поиска в арбитражных судах"""
        search_data = {
            'Page': '1',
            'Count': '25',
            'Cases.CaseType': 'A',
            'Cases.WithVKSInstances': 'false',
            'Cases.Court.Region': '',
            'Cases.Court.Id': '',
            'Cases.CaseNumber': '',
            'Cases.Judge': '',
            'Cases.LegalArea': '',
            'Cases.Participant.Name': query_params.get('name', ''),
            'Cases.Participant.Inn': query_params.get('inn', ''),
            'Cases.Participant.Ogrn': query_params.get('ogrn', ''),
            'Cases.DateFrom': '',
            'Cases.DateTo': '',
            'Cases.Instances.Status': '',
            'Cases.Instances.Reason': '',
            'Cases.Instances.Document.Type': '',
            'Cases.Instances.Document.Status': '',
            'Cases.Instances.Document.Category': '',
            'Cases.WithVKSInstances': 'false'
        }
        
        return search_data

    def _extract_form_tokens(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Извлечение токенов безопасности из формы"""
        tokens = {}
        
        # Поиск скрытых полей с токенами
        hidden_inputs = soup.find_all('input', {'type': 'hidden'})
        for input_field in hidden_inputs:
            name = input_field.get('name')
            value = input_field.get('value', '')
            if name and ('Token' in name or 'Stamp' in name or '__RequestVerificationToken' in name):
                tokens[name] = value
        
        return tokens

    async def _parse_arbitrage_results(self, html: str) -> List[Dict[str, Any]]:
        """Парсинг результатов поиска арбитражных дел"""
        cases = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Поиск таблицы с результатами
            table = soup.find('table', {'class': 'custom_table'})
            if not table:
                return cases
            
            rows = table.find_all('tr')[1:]  # Пропускаем заголовок
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    case_info = {
                        'case_number': cols[0].get_text(strip=True),
                        'case_type': cols[1].get_text(strip=True),
                        'court': cols[2].get_text(strip=True),
                        'judge': cols[3].get_text(strip=True),
                        'parties': cols[4].get_text(strip=True),
                        'status': cols[5].get_text(strip=True),
                        'last_action_date': self._extract_date(cols[6].get_text(strip=True)) if len(cols) > 6 else None,
                        'case_url': self._extract_case_url(cols[0]),
                        'source': 'arbitrage_courts'
                    }
                    cases.append(case_info)
                    
        except Exception as e:
            self.logger.error(f"Ошибка парсинга результатов арбитражных дел: {e}")
            
        return cases

    async def _parse_general_courts_results(self, html: str, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Парсинг результатов поиска в судах общей юрисдикции"""
        cases = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Примерная структура парсинга (зависит от конкретного региона)
            search_results = soup.find_all('div', {'class': 'search-result'})
            
            for result in search_results:
                case_info = {
                    'case_number': self._extract_text(result, '.case-number'),
                    'court': self._extract_text(result, '.court-name'),
                    'judge': self._extract_text(result, '.judge-name'),
                    'parties': self._extract_text(result, '.parties'),
                    'status': self._extract_text(result, '.case-status'),
                    'category': self._extract_text(result, '.case-category'),
                    'filing_date': self._extract_date(self._extract_text(result, '.filing-date')),
                    'source': 'general_courts'
                }
                cases.append(case_info)
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга результатов судов общей юрисдикции: {e}")
            
        return cases

    async def _get_arbitrage_case_details(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации об арбитражном деле"""
        try:
            details_url = f"{self.arbitrage_url}/Card/{case_id}"
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://kad.arbitr.ru/'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    details_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        html = await response.text()
                        return await self._parse_case_details(html, "arbitrage")
                    else:
                        return None
                        
        except Exception as e:
            self.logger.error(f"Ошибка получения деталей арбитражного дела {case_id}: {e}")
            return None

    async def _get_general_case_details(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о деле в суде общей юрисдикции"""
        try:
            # Логика зависит от конкретного суда/региона
            # Здесь приведен общий пример
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
            }
            
            # URL формируется в зависимости от системы суда
            details_url = f"https://court-system.ru/case/{case_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    details_url,
                    headers=headers,
                    proxy=await self.get_proxy()
                ) as response:
                    
                    if response.status == 200:
                        html = await response.text()
                        return await self._parse_case_details(html, "general")
                    else:
                        return None
                        
        except Exception as e:
            self.logger.error(f"Ошибка получения деталей дела суда общей юрисдикции {case_id}: {e}")
            return None

    async def _parse_case_details(self, html: str, court_type: str) -> Dict[str, Any]:
        """Парсинг детальной информации о деле"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            details = {
                'case_number': self._extract_text(soup, '.case-number, .b-case-number'),
                'case_type': self._extract_text(soup, '.case-type, .b-case-type'),
                'court': self._extract_text(soup, '.court-name, .b-court-name'),
                'judge': self._extract_text(soup, '.judge-name, .b-judge'),
                'category': self._extract_text(soup, '.case-category, .b-case-category'),
                'filing_date': self._extract_date(self._extract_text(soup, '.filing-date, .b-filing-date')),
                'parties': [],
                'hearings': [],
                'documents': [],
                'current_status': self._extract_text(soup, '.current-status, .b-status'),
                'court_type': court_type,
                'source': 'courts'
            }
            
            # Извлечение участников
            parties_section = soup.find('div', {'class': ['parties', 'b-parties']})
            if parties_section:
                parties = parties_section.find_all('div', {'class': ['party', 'b-party']})
                for party in parties:
                    party_info = {
                        'name': self._extract_text(party, '.party-name, .b-party-name'),
                        'role': self._extract_text(party, '.party-role, .b-party-role'),
                        'address': self._extract_text(party, '.party-address, .b-party-address'),
                        'representative': self._extract_text(party, '.representative, .b-representative')
                    }
                    details['parties'].append(party_info)
            
            # Извлечение заседаний
            hearings_section = soup.find('div', {'class': ['hearings', 'b-hearings']})
            if hearings_section:
                hearings = hearings_section.find_all('div', {'class': ['hearing', 'b-hearing']})
                for hearing in hearings:
                    hearing_info = {
                        'date': self._extract_date(self._extract_text(hearing, '.hearing-date, .b-hearing-date')),
                        'time': self._extract_text(hearing, '.hearing-time, .b-hearing-time'),
                        'type': self._extract_text(hearing, '.hearing-type, .b-hearing-type'),
                        'result': self._extract_text(hearing, '.hearing-result, .b-hearing-result'),
                        'judge': self._extract_text(hearing, '.hearing-judge, .b-hearing-judge')
                    }
                    details['hearings'].append(hearing_info)
            
            # Извлечение документов
            documents_section = soup.find('div', {'class': ['documents', 'b-documents']})
            if documents_section:
                documents = documents_section.find_all('div', {'class': ['document', 'b-document']})
                for doc in documents:
                    doc_info = {
                        'type': self._extract_text(doc, '.doc-type, .b-doc-type'),
                        'date': self._extract_date(self._extract_text(doc, '.doc-date, .b-doc-date')),
                        'name': self._extract_text(doc, '.doc-name, .b-doc-name'),
                        'url': self._extract_link(doc, '.doc-link, .b-doc-link')
                    }
                    details['documents'].append(doc_info)
            
            return details
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга деталей дела ({court_type}): {e}")
            return {'error': str(e), 'court_type': court_type, 'source': 'courts'}

    def _extract_text(self, soup, selector: str) -> Optional[str]:
        """Извлечение текста по CSS селектору"""
        try:
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else None
        except:
            return None

    def _extract_link(self, soup, selector: str) -> Optional[str]:
        """Извлечение ссылки по CSS селектору"""
        try:
            element = soup.select_one(selector)
            return element.get('href') if element else None
        except:
            return None

    def _extract_date(self, date_str: str) -> Optional[str]:
        """Извлечение и нормализация даты"""
        if not date_str:
            return None
        
        try:
            # Паттерны для различных форматов дат
            patterns = [
                r'(\d{2}\.\d{2}\.\d{4})',
                r'(\d{2}-\d{2}-\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}\s+\w+\s+\d{4})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, date_str)
                if match:
                    return match.group(1)
            
            return date_str.strip()
        except:
            return None

    def _extract_case_url(self, cell) -> Optional[str]:
        """Извлечение URL дела из ячейки таблицы"""
        try:
            link = cell.find('a')
            if link and link.get('href'):
                return urljoin(self.arbitrage_url, link.get('href'))
            return None
        except:
            return None

    async def get_analytics_data(self, inn: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение аналитических данных для скоринга
        
        Args:
            inn: ИНН для анализа
            name: Наименование организации (опционально)
            
        Returns:
            Аналитические данные по судебным делам
        """
        # Поиск дел по ИНН
        arbitrage_cases = await self.search_by_inn(inn, "arbitrage")
        general_cases = await self.search_by_inn(inn, "general")
        
        # Дополнительный поиск по наименованию
        if name:
            arbitrage_cases_name = await self.search_by_name(name, "arbitrage")
            general_cases_name = await self.search_by_name(name, "general")
            
            # Объединение результатов (с удалением дубликатов)
            arbitrage_cases.extend([case for case in arbitrage_cases_name 
                                   if case not in arbitrage_cases])
            general_cases.extend([case for case in general_cases_name 
                                 if case not in general_cases])
        
        all_cases = arbitrage_cases + general_cases
        
        analytics = {
            'total_cases': len(all_cases),
            'arbitrage_cases': len(arbitrage_cases),
            'general_cases': len(general_cases),
            'active_cases': 0,
            'completed_cases': 0,
            'case_types': {},
            'plaintiff_cases': 0,
            'defendant_cases': 0,
            'recent_cases': 0,  # За последний год
            'risk_factors': [],
            'source': 'courts'
        }
        
        current_date = datetime.now()
        one_year_ago = current_date - timedelta(days=365)
        
        for case in all_cases:
            # Статистика по статусам
            status = case.get('status', '').lower()
            if any(word in status for word in ['активное', 'рассматривается', 'назначено']):
                analytics['active_cases'] += 1
            elif any(word in status for word in ['завершено', 'решение', 'определение']):
                analytics['completed_cases'] += 1
            
            # Статистика по типам дел
            case_type = case.get('case_type')
            if case_type:
                analytics['case_types'][case_type] = analytics['case_types'].get(case_type, 0) + 1
            
            # Роль в деле (истец/ответчик)
            parties = case.get('parties', '')
            if 'истец' in parties.lower():
                analytics['plaintiff_cases'] += 1
            if 'ответчик' in parties.lower() or 'должник' in parties.lower():
                analytics['defendant_cases'] += 1
            
            # Недавние дела
            filing_date = case.get('filing_date') or case.get('last_action_date')
            if filing_date:
                try:
                    case_date = datetime.strptime(filing_date, '%d.%m.%Y')
                    if case_date >= one_year_ago:
                        analytics['recent_cases'] += 1
                except:
                    pass
        
        # Определение факторов риска
        if analytics['defendant_cases'] > analytics['plaintiff_cases']:
            analytics['risk_factors'].append('Преобладают дела в качестве ответчика')
        
        if analytics['active_cases'] > 5:
            analytics['risk_factors'].append('Большое количество активных судебных дел')
        
        if analytics['recent_cases'] > 3:
            analytics['risk_factors'].append('Высокая судебная активность в последний год')
        
        # Проверка на банкротные дела
        bankruptcy_keywords = ['банкротство', 'несостоятельность', 'банкрот']
        for case in all_cases:
            case_type = case.get('case_type', '').lower()
            if any(keyword in case_type for keyword in bankruptcy_keywords):
                analytics['risk_factors'].append('Наличие дел о банкротстве')
                break
        
        return analytics

# ...existing code...

    async def get_case_history(self, case_id: str, court_type: str = "arbitrage") -> List[Dict[str, Any]]:
        """
        Получение истории по делу (заседания, документы, этапы)
        
        Args:
            case_id: ID дела
            court_type: Тип суда ("arbitrage" или "general")
        
        Returns:
            Список событий по делу (заседания, документы, этапы)
        """
        try:
            details = await self.get_case_details(case_id, court_type)
            if not details:
                return []
            
            history = []
            # Заседания
            for hearing in details.get('hearings', []):
                history.append({
                    'type': 'hearing',
                    'date': hearing.get('date'),
                    'time': hearing.get('time'),
                    'result': hearing.get('result'),
                    'judge': hearing.get('judge'),
                    'description': hearing.get('type')
                })
            # Документы
            for doc in details.get('documents', []):
                history.append({
                    'type': 'document',
                    'date': doc.get('date'),
                    'name': doc.get('name'),
                    'doc_type': doc.get('type'),
                    'url': doc.get('url')
                })
            # Статусы/этапы
            if details.get('current_status'):
                history.append({
                    'type': 'status',
                    'date': details.get('filing_date'),
                    'status': details.get('current_status')
                })
            return history
        except Exception as e:
            self.logger.error(f"Ошибка получения истории дела {case_id}: {e}")
            return []

#     async def get_case_documents(self, case_id: str, court_type: str = "arbitrage") -> List[Dict[str, Any]]:
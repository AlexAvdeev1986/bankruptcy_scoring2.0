import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from app.parsers.base import BaseParser
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

class FSSPParser(BaseParser):
    """Парсер для ФССП (Федеральная служба судебных приставов)"""
    
    def __init__(self):
        super().__init__()
        self.base_url = settings.FSSP_BASE_URL
        self.search_url = f"{self.base_url}/iss/ip"
        self.captcha_solved = False
        
    async def search_by_inn(self, inn: str) -> Dict[str, Any]:
        """Поиск по ИНН в ФССП"""
        if not inn or len(inn) not in [10, 12]:
            return {'success': False, 'error': 'Invalid INN format'}
            
        search_params = {
            'type': 'ip',
            'inn': inn
        }
        
        return await self._perform_search(search_params, f"INN: {inn}")
    
    async def search_by_fio_dob(self, fio: str, dob: str) -> Dict[str, Any]:
        """Поиск по ФИО и дате рождения в ФССП"""
        if not fio:
            return {'success': False, 'error': 'FIO is required'}
            
        # Парсим ФИО
        fio_parts = self._parse_fio(fio)
        if not fio_parts:
            return {'success': False, 'error': 'Cannot parse FIO'}
            
        search_params = {
            'type': 'physical',
            'lastname': fio_parts.get('lastname', ''),
            'firstname': fio_parts.get('firstname', ''),
            'middlename': fio_parts.get('middlename', ''),
            'birthdate': dob
        }
        
        return await self._perform_search(search_params, f"FIO: {fio}")
    
    async def _perform_search(self, params: Dict[str, str], search_key: str) -> Dict[str, Any]:
        """Выполнение поиска в ФССП"""
        try:
            # Получаем страницу поиска
            search_page = await self._get_search_page()
            if not search_page:
                return {'success': False, 'error': 'Cannot load search page'}
            
            # Извлекаем токены и параметры формы
            form_data = await self._extract_form_data(search_page)
            if not form_data:
                return {'success': False, 'error': 'Cannot extract form data'}
            
            # Добавляем параметры поиска
            form_data.update(params)
            
            # Выполняем поиск
            search_response = await self._submit_search(form_data)
            if not search_response:
                return {'success': False, 'error': 'Search request failed'}
            
            # Парсим результаты
            results = await self._parse_search_results(search_response)
            
            self._log_request(self.search_url, 'success', {'results_count': len(results.get('items', []))})
            
            return {
                'success': True,
                'data': results,
                'search_key': search_key,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"FSSP search error for {search_key}: {str(e)}"
            logger.error(error_msg)
            self._log_request(self.search_url, 'error', error=error_msg)
            return {'success': False, 'error': error_msg}
    
    async def _get_search_page(self) -> Optional[str]:
        """Получение страницы поиска ФССП"""
        response = await self._make_request(self.search_url)
        if response:
            return await response.text()
        return None
    
    async def _extract_form_data(self, html: str) -> Optional[Dict[str, str]]:
        """Извлечение данных формы из HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        form = soup.find('form', {'id': 'search-form'})
        if not form:
            # Пробуем найти любую форму
            form = soup.find('form')
            
        if not form:
            return None
        
        form_data = {}
        
        # Извлекаем скрытые поля
        for hidden_input in form.find_all('input', {'type': 'hidden'}):
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name:
                form_data[name] = value
        
        # Ищем CSRF токен
        csrf_token = soup.find('meta', {'name': 'csrf-token'})
        if csrf_token:
            form_data['_token'] = csrf_token.get('content', '')
        
        # Ищем капчу
        captcha_img = soup.find('img', {'class': 'captcha'})
        if captcha_img:
            # В реальном проекте здесь должно быть решение капчи
            # Для демо возвращаем заглушку
            form_data['captcha'] = 'DEMO_CAPTCHA'
            logger.warning("CAPTCHA detected - using demo value")
        
        return form_data
    
    async def _submit_search(self, form_data: Dict[str, str]) -> Optional[str]:
        """Отправка формы поиска"""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': self.search_url,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        response = await self._make_request(
            self.search_url, 
            method='POST',
            data=form_data,
            headers=headers
        )
        
        if response:
            return await response.text()
        return None
    
    async def _parse_search_results(self, html: str) -> Dict[str, Any]:
        """Парсинг результатов поиска"""
        soup = BeautifulSoup(html, 'html.parser')
        results = {
            'items': [],
            'total_debt': 0,
            'active_cases': 0
        }
        
        # Ищем таблицу с результатами
        table = soup.find('table', {'class': 'table-results'}) or soup.find('table')
        
        if not table:
            # Пробуем найти результаты в JSON формате
            json_data = self._extract_json_from_html(html)
            if json_data:
                return self._parse_json_results(json_data)
            return results
        
        # Парсим строки таблицы
        rows = table.find_all('tr')[1:]  # Пропускаем заголовок
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 5:
                debt_info = self._parse_debt_row(cells)
                if debt_info:
                    results['items'].append(debt_info)
                    results['total_debt'] += debt_info.get('amount', 0)
                    if debt_info.get('status') == 'active':
                        results['active_cases'] += 1
        
        return results
    
    def _parse_debt_row(self, cells: List) -> Optional[Dict[str, Any]]:
        """Парсинг строки с информацией о долге"""
        try:
            # Извлекаем данные из ячеек таблицы
            # Структура может отличаться, поэтому делаем гибкий парсинг
            
            debt_info = {}
            
            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                
                # Ищем сумму долга
                amount_match = re.search(r'(\d+[\s,.]?\d*)\s*руб', text, re.IGNORECASE)
                if amount_match:
                    amount_str = amount_match.group(1).replace(' ', '').replace(',', '.')
                    debt_info['amount'] = float(amount_str)
                
                # Ищем дату
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
                if date_match:
                    debt_info['date'] = date_match.group(1)
                
                # Ищем статус
                if any(word in text.lower() for word in ['окончено', 'прекращено']):
                    debt_info['status'] = 'closed'
                elif any(word in text.lower() for word in ['производство', 'взыскание']):
                    debt_info['status'] = 'active'
                
                # Ищем тип долга
                if any(word in text.lower() for word in ['банк', 'кредит']):
                    debt_info['type'] = 'bank'
                elif any(word in text.lower() for word in ['мфо', 'микрофинанс']):
                    debt_info['type'] = 'mfo'
                elif any(word in text.lower() for word in ['налог', 'фнс']):
                    debt_info['type'] = 'tax'
                elif any(word in text.lower() for word in ['жкх', 'коммунальн']):
                    debt_info['type'] = 'utilities'
                
                # Взыскатель
                if i == 2:  # Обычно взыскатель в 3-й колонке
                    debt_info['creditor'] = text
            
            return debt_info if debt_info else None
            
        except Exception as e:
            logger.error(f"Error parsing debt row: {str(e)}")
            return None
    
    def _extract_json_from_html(self, html: str) -> Optional[Dict]:
        """Извлечение JSON данных из HTML"""
        # Ищем JSON в скриптах
        json_pattern = r'var\s+searchResults\s*=\s*({.*?});'
        match = re.search(json_pattern, html, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _parse_json_results(self, json_data: Dict) -> Dict[str, Any]:
        """Парсинг результатов из JSON"""
        results = {
            'items': [],
            'total_debt': 0,
            'active_cases': 0
        }
        
        items = json_data.get('result', {}).get('items', [])
        
        for item in items:
            debt_info = {
                'amount': float(item.get('debt_amount', 0)),
                'type': self._determine_debt_type(item.get('creditor', '')),
                'creditor': item.get('creditor', ''),
                'status': item.get('status', ''),
                'date': item.get('case_date', ''),
                'case_number': item.get('case_number', '')
            }
            
            results['items'].append(debt_info)
            results['total_debt'] += debt_info['amount']
            
            if debt_info['status'] == 'active':
                results['active_cases'] += 1
        
        return results
    
    def _determine_debt_type(self, creditor: str) -> str:
        """Определение типа долга по взыскателю"""
        creditor_lower = creditor.lower()
        
        if any(word in creditor_lower for word in ['банк', 'bank']):
            return 'bank'
        elif any(word in creditor_lower for word in ['мфо', 'микрофинанс']):
            return 'mfo'  
        elif any(word in creditor_lower for word in ['налог', 'фнс']):
            return 'tax'
        elif any(word in creditor_lower for word in ['жкх', 'коммунальн']):
            return 'utilities'
        else:
            return 'other'
    
    def _parse_fio(self, fio: str) -> Optional[Dict[str, str]]:
        """Парсинг ФИО на составные части"""
        if not fio:
            return None
        
        parts = fio.strip().split()
        if len(parts) < 2:
            return None
        
        result = {
            'lastname': parts[0],
            'firstname': parts[1] if len(parts) > 1 else '',
            'middlename': parts[2] if len(parts) > 2 else ''
        }
        
        return result
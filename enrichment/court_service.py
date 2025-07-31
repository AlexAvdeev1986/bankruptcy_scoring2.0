import requests
import logging
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

class CourtService:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('CourtService')
        self.base_url = config['COURT_URL']
        self.retry_count = 3
        self.timeout = 30
        self.cache = {}
    
    def enrich(self, lead: dict) -> dict:
        """Проверка наличия судебных приказов"""
        # Инициализация полей
        lead.setdefault('has_court_order', False)
        lead.setdefault('has_recent_court_order', False)
        
        # Проверка кеша
        cache_key = f"court_{lead.get('fio', '')}"
        if cache_key in self.cache:
            return {**lead, **self.cache[cache_key]}
        
        # Если нет ФИО, пропускаем
        if not lead.get('fio'):
            return lead
        
        try:
            # Попытки запроса с ротацией прокси
            for attempt in range(self.retry_count):
                try:
                    proxy = self.proxy_rotator.get_proxy()
                    headers = {
                        'User-Agent': self.proxy_rotator.get_user_agent(),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                    }
                    
                    response = requests.get(
                        self.base_url,
                        params={'fio': lead['fio']},
                        proxies=proxy,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = self.parse_response(response.text)
                        self.cache[cache_key] = result
                        return {**lead, **result}
                    
                    # Обработка блокировки
                    elif response.status_code in [403, 429]:
                        self.logger.warning(f"Доступ запрещен (код {response.status_code}), меняем прокси")
                        self.proxy_rotator.report_bad_proxy(proxy['http'])
                
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    self.logger.error(f"Ошибка сети (попытка {attempt+1}): {str(e)}")
                    time.sleep(random.uniform(1, 3))
        
        except Exception as e:
            self.logger.error(f"Ошибка CourtService: {str(e)}")
        
        return lead

    def parse_response(self, html: str) -> dict:
        """Парсинг HTML ответа судебного сервиса"""
        result = {
            'has_court_order': False,
            'has_recent_court_order': False
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Проверка наличия результатов
            results_section = soup.find('div', class_='search-results')
            if not results_section:
                return result
            
            # Поиск таблицы с результатами
            results_table = results_section.find('table', class_='results-table')
            if not results_table:
                return result
            
            # Помечаем, что есть хотя бы один приказ
            result['has_court_order'] = True
            
            # Поиск строк с результатами
            rows = results_table.find_all('tr')[1:]  # Пропускаем заголовок
            
            # Проверка свежих приказов (за последние 3 месяца)
            three_months_ago = datetime.now() - timedelta(days=90)
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) > 2:
                    # Извлечение даты
                    date_cell = cells[1].get_text().strip()
                    try:
                        order_date = datetime.strptime(date_cell, '%d.%m.%Y')
                        if order_date > three_months_ago:
                            result['has_recent_court_order'] = True
                            break  # Достаточно одного свежего приказа
                    except ValueError:
                        continue
        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга HTML: {str(e)}")
        
        return result
    
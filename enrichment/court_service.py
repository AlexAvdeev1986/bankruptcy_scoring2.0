import os
import requests
import logging
import time
import random
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class CourtService:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('CourtService')
        self.base_url = config['COURT_URL']
        self.retry_count = 5  # Увеличили количество попыток
        self.timeout = 30     # Уменьшили таймаут одного запроса
        self.cache = {}
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
        # Настройка сессии с повторными попытками
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def enrich(self, lead: dict) -> dict:
        """Проверка наличия судебных приказов с улучшенной обработкой ошибок"""
        if self.mock_mode:
            return self.mock_enrich(lead)
            
        # Инициализация полей
        lead.setdefault('has_court_order', False)
        lead.setdefault('has_recent_court_order', False)
        
        # Проверка кеша
        cache_key = f"court_{lead.get('fio', '')}_{lead.get('dob', '')}"
        if cache_key in self.cache:
            return {**lead, **self.cache[cache_key]}
        
        # Если нет ФИО, пропускаем
        if not lead.get('fio'):
            return lead
        
        try:
            # Параметры запроса
            params = {'fio': lead['fio']}
            if lead.get('dob'):
                params['birth_date'] = lead['dob'].strftime('%Y-%m-%d')
            
            # Попытка запроса
            proxy = self.proxy_rotator.get_proxy()
            headers = {
                'User-Agent': self.proxy_rotator.get_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive'
            }
            
            response = self.session.get(
                self.base_url,
                params=params,
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
                return lead
                
        except requests.exceptions.Timeout:
            self.logger.warning("Таймаут при запросе к судебному сервису")
            return lead
        except Exception as e:
            self.logger.error(f"Критическая ошибка CourtService: {str(e)}", exc_info=True)
        
        return lead

    def parse_response(self, html: str) -> dict:
        """Парсинг HTML ответа судебного сервиса с улучшенной обработкой"""
        result = {
            'has_court_order': False,
            'has_recent_court_order': False
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Проверка наличия результатов
            no_results = soup.find('div', class_='no-results')
            if no_results:
                return result
                
            # Поиск таблицы с результатами
            results_table = soup.find('table', class_='results-table')
            if not results_table:
                return result
            
            # Помечаем, что есть хотя бы один приказ
            result['has_court_order'] = True
            
            # Проверка свежих приказов (за последние 3 месяца)
            three_months_ago = datetime.now() - timedelta(days=90)
            
            # Поиск всех строк в таблице (кроме заголовка)
            rows = results_table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) > 1:
                    date_cell = cells[1].get_text().strip()
                    try:
                        # Пробуем разные форматы дат
                        for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
                            try:
                                order_date = datetime.strptime(date_cell, fmt)
                                break
                            except ValueError:
                                continue
                        
                        if order_date > three_months_ago:
                            result['has_recent_court_order'] = True
                            break  # Достаточно одного свежего приказа
                    except:
                        continue
        
        except Exception as e:
            self.logger.error(f"Ошибка парсинга HTML: {str(e)}")
        
        return result
    
    def mock_enrich(self, lead: dict) -> dict:
        """Заглушка для тестового режима с более реалистичными данными"""
        # Генерация данных на основе характеристик лида
        has_debt = lead.get('debt_amount', 0) > 0
        is_high_risk = lead.get('score', 0) > 70 if 'score' in lead else False
        
        # Вероятности
        p_court = 0.7 if has_debt else 0.3
        p_recent = 0.8 if is_high_risk else 0.4
        
        return {
            'has_court_order': random.random() < p_court,
            'has_recent_court_order': random.random() < p_recent
        }
        
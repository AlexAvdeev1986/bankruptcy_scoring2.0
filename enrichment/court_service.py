import os
import requests
import logging
import time
import random
import socket
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.packages.urllib3.exceptions import NameResolutionError

class CourtService:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('CourtService')
        self.base_url = config['COURT_URL']
        self.retry_count = config.get('COURT_RETRIES', 8)
        self.timeout = config.get('COURT_TIMEOUT', 60)
        self.cache = {}
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        
        # Настройка сессии с повторными попытками
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Настройка DNS-резолвера
        self.dns_cache = {}
        self.dns_cache_timeout = 300  # 5 минут
        
        # Настройка параметров соединения
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://sudrf.ru/'
        })
    
    def resolve_dns(self, hostname):
        """Кеширующее DNS-разрешение с обработкой ошибок"""
        now = time.time()
        
        # Проверка кеша
        if hostname in self.dns_cache:
            ip, timestamp = self.dns_cache[hostname]
            if now - timestamp < self.dns_cache_timeout:
                return ip
        
        try:
            # Разрешение DNS с таймаутом
            self.logger.info(f"Разрешение DNS для {hostname}")
            ip = socket.gethostbyname(hostname)
            self.dns_cache[hostname] = (ip, now)
            return ip
        except socket.gaierror as e:
            self.logger.error(f"Ошибка DNS-разрешения: {str(e)}")
            return None
    
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
            
            # Разрешение DNS
            hostname = "sudrf.ru"
            ip_address = self.resolve_dns(hostname)
            
            if not ip_address:
                self.logger.error(f"Не удалось разрешить DNS для {hostname}")
                return lead
                
            # Формирование URL с IP-адресом
            url = f"http://{ip_address}/index.php"
            
            # Попытка запроса
            proxy = self.proxy_rotator.get_proxy()
            headers = {
                'User-Agent': self.proxy_rotator.get_user_agent(),
                'Host': hostname  # Важно сохранить оригинальный Host
            }
            
            start_time = time.time()
            response = self.session.get(
                url,
                params=params,
                proxies=proxy,
                headers=headers,
                timeout=self.timeout
            )
            request_time = time.time() - start_time
            
            if response.status_code == 200:
                self.logger.debug(f"Запрос к судебному сервису выполнен за {request_time:.2f} сек")
                result = self.parse_response(response.text)
                self.cache[cache_key] = result
                return {**lead, **result}
            
            # Обработка блокировки
            elif response.status_code in [403, 429]:
                self.logger.warning(f"Доступ запрещен (код {response.status_code}), меняем прокси")
                self.proxy_rotator.report_bad_proxy(proxy['http'])
                return lead
                
        except NameResolutionError as nre:
            self.logger.error(f"Критическая ошибка разрешения имени: {str(nre)}")
            return lead
        except requests.exceptions.Timeout:
            self.logger.warning(f"Таймаут при запросе к судебному сервису ({self.timeout} сек)")
            return lead
        except requests.exceptions.ConnectionError as ce:
            self.logger.error(f"Ошибка соединения: {str(ce)}")
            return lead
        except requests.exceptions.RequestException as re:
            self.logger.error(f"Ошибка запроса: {str(re)}")
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
                    except Exception as date_error:
                        self.logger.debug(f"Ошибка парсинга даты '{date_cell}': {str(date_error)}")
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
        
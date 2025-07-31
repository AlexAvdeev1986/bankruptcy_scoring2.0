import requests
import logging
import time
import random

class RosreestrService:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('RosreestrService')
        self.base_url = config['ROSREESTR_URL']
        self.retry_count = 3
        self.timeout = 20
        self.cache = {}
    
    def enrich(self, lead: dict) -> dict:
        """Проверка наличия недвижимости через Росреестр"""
        # Инициализация поля
        lead.setdefault('has_property', False)
        
        # Проверка кеша
        cache_key = f"rosreestr_{lead.get('inn', '')}"
        if cache_key in self.cache:
            return {**lead, **self.cache[cache_key]}
        
        # Если нет ИНН, пропускаем
        if not lead.get('inn'):
            return lead
        
        try:
            # Попытки запроса с ротацией прокси
            for attempt in range(self.retry_count):
                try:
                    proxy = self.proxy_rotator.get_proxy()
                    headers = {
                        'User-Agent': self.proxy_rotator.get_user_agent(),
                        'Accept': 'application/json'
                    }
                    
                    response = requests.get(
                        f"{self.base_url}/properties?inn={lead['inn']}",
                        proxies=proxy,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    # Успешный запрос
                    if response.status_code == 200:
                        result = self.parse_response(response.json())
                        self.cache[cache_key] = result
                        return {**lead, **result}
                    
                    # Обработка отсутствия данных
                    elif response.status_code == 404:
                        self.logger.info(f"ИНН {lead['inn']} не найден в Росреестре")
                        return lead
                    
                    # Обработка блокировки
                    elif response.status_code in [403, 429]:
                        self.logger.warning(f"Доступ запрещен (код {response.status_code}), меняем прокси")
                        self.proxy_rotator.report_bad_proxy(proxy['http'])
                
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    self.logger.error(f"Ошибка сети (попытка {attempt+1}): {str(e)}")
                    time.sleep(random.uniform(1, 2))
        
        except Exception as e:
            self.logger.error(f"Ошибка RosreestrService: {str(e)}")
        
        return lead

    def parse_response(self, data: dict) -> dict:
        """Парсинг JSON ответа Росреестра"""
        result = {'has_property': False}
        
        try:
            # Проверка наличия объектов недвижимости
            properties = data.get('properties', [])
            if properties:
                result['has_property'] = True
                result['property_count'] = len(properties)
                result['property_types'] = list(set([p.get('type', '') for p in properties]))
        except Exception as e:
            self.logger.error(f"Ошибка парсинга JSON: {str(e)}")
        return result
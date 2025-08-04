import requests
import logging
import time
import random

class TaxService:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('TaxService')
        self.base_url = config['TAX_SERVICE_URL']
        self.retry_count = 3
        self.timeout = 20
        self.cache = {}
    
    def enrich(self, lead: dict) -> dict:
        """Проверка активности ИНН и налоговой задолженности"""
        # Инициализация полей
        lead.setdefault('is_inn_active', True)
        lead.setdefault('tax_debt', 0)
        lead.setdefault('is_wanted', False)
        lead.setdefault('is_dead', False)
        
        # Проверка кеша
        cache_key = f"tax_{lead.get('inn', '')}"
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
                        f"{self.base_url}/inn/{lead['inn']}/status",
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
                        self.logger.info(f"ИНН {lead['inn']} не найден в налоговой службе")
                        return {
                            'is_inn_active': False,
                            'tax_debt': 0,
                            'is_wanted': False,
                            'is_dead': False
                        }
                    
                    # Обработка блокировки
                    elif response.status_code in [403, 429]:
                        self.logger.warning(f"Доступ запрещен (код {response.status_code}), меняем прокси")
                        self.proxy_rotator.report_bad_proxy(proxy['http'])
                
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    self.logger.error(f"Ошибка сети (попытка {attempt+1}): {str(e)}")
                    time.sleep(random.uniform(1, 2))
        
        except Exception as e:
            self.logger.error(f"Критическая ошибка TaxService: {str(e)}", exc_info=True)
        finally:
            return lead

    def parse_response(self, data: dict) -> dict:
        """Парсинг JSON ответа налоговой службы"""
        result = {
            'is_inn_active': data.get('status') == 'ACTIVE',
            'tax_debt': data.get('debt', 0),
            'is_wanted': data.get('is_wanted', False),
            'is_dead': data.get('is_dead', False)
        }
        return result
    
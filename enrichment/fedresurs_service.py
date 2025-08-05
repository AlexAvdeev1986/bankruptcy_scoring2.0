import requests
import json
import time
import logging
from typing import Dict, Optional, List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FedresursService:
    """
    Сервис для получения данных о компаниях с портала Федресурс.
    Обеспечивает поиск информации о банкротствах по ИНН/ОГРН.
    """
    
    BASE_API_URL = "https://api.fedresurs.ru"
    SEARCH_ENDPOINT = "/public/companies/search"
    COMPANY_INFO_ENDPOINT = "/public/companies/{}"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
        'Accept': 'application/json'
    }
    
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('FedresursService')
        self.request_delay = 0.5
        self.retry_count = 3
        self.timeout = 20
        
    def enrich(self, lead: dict) -> dict:
        """Обогащение данных лида информацией о банкротстве"""
        # Инициализация поля
        lead.setdefault('is_bankrupt', False)
        
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
                        f"{self.BASE_API_URL}{self.SEARCH_ENDPOINT}",
                        params={'searchString': lead['inn']},
                        proxies=proxy,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Проверяем наличие информации о банкротстве
                        lead['is_bankrupt'] = self.has_bankruptcy(data)
                        return lead
                    
                    # Обработка блокировки
                    elif response.status_code in [403, 429]:
                        self.logger.warning(f"Доступ запрещен, меняем прокси")
                        self.proxy_rotator.report_bad_proxy(proxy['http'])
                
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    self.logger.error(f"Ошибка сети (попытка {attempt+1}): {str(e)}")
                    time.sleep(self.request_delay)
        
        except Exception as e:
            self.logger.error(f"Критическая ошибка FedresursService: {str(e)}")
        
        return lead

    def has_bankruptcy(self, data: dict) -> bool:
        """Проверка наличия процедуры банкротства в ответе"""
        try:
            if data.get('items'):
                for company in data['items']:
                    if company.get('status') == 'BANKRUPT':
                        return True
                    if company.get('bankruptcyCases') and len(company['bankruptcyCases']) > 0:
                        return True
        except Exception as e:
            self.logger.error(f"Ошибка парсинга данных: {str(e)}")
        return False

# Пример использования
if __name__ == "__main__":
    # Создание экземпляра сервиса
    from utils.proxy_rotator import ProxyRotator
    from config import Config
    
    proxy_rotator = ProxyRotator([])
    service = FedresursService(proxy_rotator, Config)
    
    # Пример запроса информации о компании
    lead = {"inn": "7707083893", "fio": "Иванов Иван"}  # ИНН Яндекс
    enriched_lead = service.enrich(lead)
    
    print(f"Результат обогащения: {enriched_lead}")
    
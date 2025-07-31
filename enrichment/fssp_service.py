import requests
import logging
import time
import random
from bs4 import BeautifulSoup

class FSSPService:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('FSSPService')
        self.base_url = config['FSSP_URL']
        self.retry_count = 3
        self.timeout = 30
    
    def enrich(self, lead: dict) -> dict:
        """Получение данных о долгах из ФССП"""
        # Инициализация полей
        lead.setdefault('debt_amount', 0)
        lead.setdefault('debt_count', 0)
        lead.setdefault('has_bank_mfo_debt', False)
        lead.setdefault('only_tax_utility_debts', True)
        
        try:
            # Поиск по ИНН (если есть)
            if lead.get('inn'):
                return self._search_by_inn(lead)
            
            # Поиск по ФИО и дате рождения (если есть)
            if lead.get('fio') and lead.get('dob'):
                return self._search_by_fio_dob(lead)
        
        except Exception as e:
            self.logger.error(f"Ошибка ФССП для {lead.get('fio', '')}: {str(e)}")
        
        return lead

    def _search_by_inn(self, lead: dict) -> dict:
        """Поиск по ИНН"""
        inn = lead['inn']
        
        for attempt in range(self.retry_count):
            try:
                proxy = self.proxy_rotator.get_proxy()
                headers = {
                    'User-Agent': self.proxy_rotator.get_user_agent(),
                    'Accept': 'application/json'
                }
                
                response = requests.get(
                    f"{self.base_url}?inn={inn}",
                    proxies=proxy,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, lead)
                elif response.status_code == 403:
                    self.logger.warning(f"Доступ запрещен, меняем прокси")
                    self.proxy_rotator.report_bad_proxy(proxy['http'])
            
            except Exception as e:
                self.logger.error(f"Ошибка запроса к ФССП (попытка {attempt+1}): {str(e)}")
                time.sleep(random.uniform(1, 3))
        
        return lead

    def _search_by_fio_dob(self, lead: dict) -> dict:
        """Поиск по ФИО и дате рождения"""
        # Аналогичная реализация для поиска по ФИО и дате рождения
        return lead

    def _parse_response(self, data: dict, lead: dict) -> dict:
        """Парсинг ответа от ФССП"""
        if data.get('status') == 'success' and 'debts' in data:
            for debt in data['debts']:
                lead['debt_amount'] += debt['amount']
                lead['debt_count'] += 1
                
                creditor_type = debt['creditor_type'].lower()
                if 'банк' in creditor_type or 'мфо' in creditor_type or 'микрофинанс' in creditor_type:
                    lead['has_bank_mfo_debt'] = True
                    lead['only_tax_utility_debts'] = False
                elif 'налог' in creditor_type or 'жкх' in creditor_type or 'коммунал' in creditor_type:
                    # Оставляем флаг only_tax_utility_debts как True
                    pass
                else:
                    lead['only_tax_utility_debts'] = False
        
        return lead
    
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
    
    def __init__(self, api_key: str = None, request_delay: float = 0.5):
        """
        Инициализация сервиса
        
        :param api_key: API-ключ для доступа (если требуется)
        :param request_delay: Задержка между запросами для избежания блокировки
        """
        self.api_key = api_key
        self.request_delay = request_delay
        self.session = requests.Session()
        
        if api_key:
            self.HEADERS['Authorization'] = f'Bearer {api_key}'
    
    def get_company_info(self, inn: str) -> Optional[Dict]:
        """
        Получение информации о компании по ИНН
        
        :param inn: ИНН компании (10 или 12 цифр)
        :return: Словарь с данными компании или None в случае ошибки
        """
        try:
            # Поиск компании по ИНН
            search_url = f"{self.BASE_API_URL}{self.SEARCH_ENDPOINT}"
            params = {'searchString': inn}
            
            response = self.session.get(
                search_url, 
                headers=self.HEADERS, 
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Search failed: {response.status_code} - {response.text}")
                return None
                
            search_data = response.json()
            
            if not search_data.get('items') or len(search_data['items']) == 0:
                logger.info(f"No companies found for INN: {inn}")
                return None
                
            # Берем первую найденную компанию
            company_id = search_data['items'][0]['id']
            
            # Делаем паузу перед следующим запросом
            time.sleep(self.request_delay)
            
            # Получение детальной информации
            return self._get_company_details(company_id)
            
        except Exception as e:
            logger.exception(f"Error getting company info: {e}")
            return None
    
    def _get_company_details(self, company_id: str) -> Optional[Dict]:
        """
        Получение детальной информации о компании по её ID
        
        :param company_id: Уникальный идентификатор компании в системе Федресурс
        :return: Словарь с детальной информацией
        """
        try:
            details_url = f"{self.BASE_API_URL}{self.COMPANY_INFO_ENDPOINT.format(company_id)}"
            
            response = self.session.get(
                details_url, 
                headers=self.HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Details request failed: {response.status_code} - {response.text}")
                return None
                
            return response.json()
            
        except Exception as e:
            logger.exception(f"Error getting company details: {e}")
            return None
    
    def get_bankruptcy_info(self, inn: str) -> List[Dict]:
        """
        Получение информации о процедурах банкротства компании
        
        :param inn: ИНН компании
        :return: Список процедур банкротства
        """
        # В реальной реализации здесь будет запрос к соответствующему API
        # Для примера возвращаем заглушку
        return [
            {
                "case_number": "А40-123456/2024",
                "start_date": "2024-01-15",
                "status": "В процессе",
                "arbitrator": "Иванов И.И."
            }
        ]
    
    def enrich_company_data(self, company_data: Dict) -> Dict:
        """
        Обогащение данных компании информацией из Федресурса
        
        :param company_data: Базовые данные компании
        :return: Обогащенный словарь данных
        """
        inn = company_data.get('inn')
        if not inn:
            return company_data
            
        fedresurs_data = self.get_company_info(inn)
        if not fedresurs_data:
            return company_data
            
        # Основные данные
        company_data['full_name'] = fedresurs_data.get('fullName')
        company_data['legal_address'] = fedresurs_data.get('legalAddress')
        company_data['status'] = fedresurs_data.get('status')
        
        # Данные о банкротстве
        company_data['bankruptcy_cases'] = self.get_bankruptcy_info(inn)
        
        return company_data

# Пример использования
if __name__ == "__main__":
    # Создание экземпляра сервиса
    service = FedresursService()
    
    # Пример запроса информации о компании
    inn = "7707083893"  # ИНН Яндекс
    company_info = service.get_company_info(inn)
    
    if company_info:
        print("Информация о компании:")
        print(json.dumps(company_info, indent=2, ensure_ascii=False))
        
        # Пример обогащения данных
        base_data = {"inn": inn, "name": "Яндекс"}
        enriched_data = service.enrich_company_data(base_data)
        print("\nОбогащенные данные:")
        print(json.dumps(enriched_data, indent=2, ensure_ascii=False))
    else:
        print(f"Данные для ИНН {inn} не найдены")
        
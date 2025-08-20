import logging
from cachetools import TTLCache
from .fssp_service import FSSPService
from .fedresurs_service import FedresursService
from .rosreestr_service import RosreestrService
from .court_service import CourtService
from .tax_service import TaxService

class DataEnricher:
    def __init__(self, proxy_rotator, config):
        self.proxy_rotator = proxy_rotator
        self.config = config
        self.logger = logging.getLogger('DataEnricher')
        self.cache = TTLCache(maxsize=1000, ttl=3600)  # Кеш на 1 час
        
        # Инициализация сервисов
        self.fssp_service = FSSPService(proxy_rotator, config)
        self.fedresurs_service = FedresursService(proxy_rotator, config)
        self.rosreestr_service = RosreestrService(proxy_rotator, config)
        self.court_service = CourtService(proxy_rotator, config)
        self.tax_service = TaxService(proxy_rotator, config)
        
        self.services = [
            self.fssp_service,
            self.fedresurs_service,
            self.rosreestr_service,
            self.court_service,
            self.tax_service
        ]
    
    def enrich(self, lead: dict) -> dict:
        """Обогащение данных лида с обработкой ошибок и кешированием"""
        # Проверка кеша
        cache_key = f"{lead.get('phone', '')}_{lead.get('inn', '')}_{lead.get('fio', '')}"
        if cache_key in self.cache:
            self.logger.debug(f"Использован кеш для лида: {cache_key}")
            return self.cache[cache_key]
        
        # Инициализация полей по умолчанию
        lead.setdefault('debt_amount', 0)
        lead.setdefault('debt_count', 0)
        lead.setdefault('has_bank_mfo_debt', False)
        lead.setdefault('only_tax_utility_debts', True)
        lead.setdefault('is_bankrupt', False)
        lead.setdefault('has_property', False)
        lead.setdefault('has_court_order', False)
        lead.setdefault('has_recent_court_order', False)
        lead.setdefault('is_inn_active', True)
        lead.setdefault('tax_debt', 0)
        lead.setdefault('is_wanted', False)
        lead.setdefault('is_dead', False)
        
        # Последовательное обогащение данными
        for service in self.services:
            try:
                lead = service.enrich(lead)
            except Exception as e:
                self.logger.error(f"Ошибка в {service.__class__.__name__}: {str(e)}")
        
        # Сохранение в кеш
        self.cache[cache_key] = lead
        
        return lead
    
import logging
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
        
        # Инициализация сервисов
        self.fssp_service = FSSPService(proxy_rotator, config)
        self.fedresurs_service = FedresursService(proxy_rotator, config)
        self.rosreestr_service = RosreestrService(proxy_rotator, config)
        self.court_service = CourtService(proxy_rotator, config)
        self.tax_service = TaxService(proxy_rotator, config)
    
    def enrich(self, lead: dict) -> dict:
        """Обогащение данных лида"""
        # Обогащение из ФССП
        lead = self.fssp_service.enrich(lead)
        
        # Обогащение из Федресурса
        lead = self.fedresurs_service.enrich(lead)
        
        # Обогащение из Росреестра
        lead = self.rosreestr_service.enrich(lead)
        
        # Обогащение из судов
        lead = self.court_service.enrich(lead)
        
        # Обогащение из налоговой
        lead = self.tax_service.enrich(lead)
        
        return lead
    
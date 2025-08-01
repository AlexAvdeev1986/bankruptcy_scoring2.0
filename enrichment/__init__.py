# Явно экспортируйте классы для импорта
from .fedresurs_service import FedresursService
from .enricher import DataEnricher

__all__ = ['FedresursService', 'DataEnricher']
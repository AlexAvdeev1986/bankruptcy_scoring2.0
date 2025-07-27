import asyncio
from typing import List, Dict, Any
from app.parsers.fssp import FSSPParser
from app.parsers.fedresurs import FedresursParser
from app.parsers.rosreestr import RosreestrParser
from app.parsers.courts import CourtsParser
from app.parsers.nalog import NalogParser
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

class DataEnrichment:
    """Класс для обогащения данных лидов информацией из внешних источников"""
    
    def __init__(self):
        self.parsers = {}
        self.semaphore = asyncio.Semaphore(settings.CONCURRENT_REQUESTS)
    
    async def init_parsers(self):
        """Инициализация всех парсеров"""
        self.parsers = {
            'fssp': FSSPParser(),
            'fedresurs': FedresursParser(),
            'rosreestr': RosreestrParser(),
            'courts': CourtsParser(),
            'nalog': NalogParser()
        }
        
        # Инициализируем сессии
        for parser in self.parsers.values():
            await parser.init_session()
    
    async def close_parsers(self):
        """Закрытие всех парсеров"""
        for parser in self.parsers.values():
            await parser.close_session()
    
    async def enrich_batch(self, leads_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Обогащение батча лидов"""
        if not self.parsers:
            await self.init_parsers()
        
        enriched_leads = []
        
        # Создаем задачи для параллельной обработки
        tasks = []
        for lead in leads_batch:
            task = asyncio.create_task(self.enrich_single_lead(lead))
            tasks.append(task)
        
        # Выполняем все задачи
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error enriching lead {leads_batch[i].get('lead_id')}: {str(result)}")
                # Возвращаем исходный лид без обогащения
                enriched_leads.append(leads_batch[i])
            else:
                enriched_leads.append(result)
        
        return enriched_leads
    
    async def enrich_single_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Обогащение одного лида данными из всех источников"""
        async with self.semaphore:
            enriched_lead = lead.copy()
            
            # Инициализируем поля для обогащенных данных
            enriched_lead.update({
                'total_debt': 0,
                'debts': [],
                'has_property': False,
                'is_bankrupt': False,
                'inn_active': True,
                'has_recent_court_order': False,
                'court_orders': [],
                'enrichment_status': {}
            })
            
            inn = lead.get('inn', '')
            fio = lead.get('fio', '')
            dob = lead.get('dob', '')
            
            # Обогащение данными ФССП
            try:
                fssp_data = await self._enrich_fssp(inn, fio, dob)
                if fssp_data['success']:
                    self._process_fssp_data(enriched_lead, fssp_data['data'])
                    enriched_lead['enrichment_status']['fssp'] = 'success'
                else:
                    enriched_lead['enrichment_status']['fssp'] = 'error'
            except Exception as e:
                logger.error(f"FSSP enrichment error for {lead.get('lead_id')}: {str(e)}")
                enriched_lead['enrichment_status']['fssp'] = 'error'
            
            # Обогащение данными Федресурс
            try:
                fedresurs_data = await self._enrich_fedresurs(inn, fio, dob)
                if fedresurs_data['success']:
                    self._process_fedresurs_data(enriched_lead, fedresurs_data['data'])
                    enriched_lead['enrichment_status']['fedresurs'] = 'success'
                else:
                    enriched_lead['enrichment_status']['fedresurs'] = 'error'
            except Exception as e:
                logger.error(f"Fedresurs enrichment error for {lead.get('lead_id')}: {str(e)}")
                enriched_lead['enrichment_status']['fedresurs'] = 'error'
            
            # Обогащение данными Росреестр
            try:
                rosreestr_data = await self._enrich_rosreestr(inn)
                if rosreestr_data['success']:
                    self._process_rosreestr_data(enriched_lead, rosreestr_data['data'])
                    enriched_lead['enrichment_status']['rosreestr'] = 'success'
                else:
                    enriched_lead['enrichment_status']['rosreestr'] = 'error'
            except Exception as e:
                logger.error(f"Rosreestr enrichment error for {lead.get('lead_id')}: {str(e)}")
                enriched_lead['enrichment_status']['rosreestr'] = 'error'
            
            # Обогащение данными судов
            try:
                courts_data = await self._enrich_courts(fio)
                if courts_data['success']:
                    self._process_courts_data(enriched_lead, courts_data['data'])
                    enriched_lead['enrichment_status']['courts'] = 'success'
                else:
                    enriched_lead['enrichment_status']['courts'] = 'error'
            except Exception as e:
                logger.error(f"Courts enrichment error for {lead.get('lead_id')}: {str(e)}")
                enriched_lead['enrichment_status']['courts'] = 'error'
            
            # Обогащение данными налоговой
            try:
                nalog_data = await self._enrich_nalog(inn)
                if nalog_data['success']:
                    self._process_nalog_data(enriched_lead, nalog_data['data'])
                    enriched_lead['enrichment_status']['nalog'] = 'success'
                else:
                    enriched_lead['enrichment_status']['nalog'] = 'error'
            except Exception as e:
                logger.error(f"Nalog enrichment error for {lead.get('lead_id')}: {str(e)}")
                enriched_lead['enrichment_status']['nalog'] = 'error'
            
            return enriched_lead
    
    async def _enrich_fssp(self, inn: str, fio: str, dob: str) -> Dict[str, Any]:
        """Обогащение данными ФССП"""
        if inn:
            return await self.parsers['fssp'].search_by_inn(inn)
        elif fio:
            return await self.parsers['fssp'].search_by_fio_dob(fio, dob)
        else:
            return {'success': False, 'error': 'No INN or FIO provided'}
    
    async def _enrich_fedresurs(self, inn: str, fio: str, dob: str) -> Dict[str, Any]:
        """Обогащение данными Федресурс"""
        if inn:
            return await self.parsers['fedresurs'].search_by_inn(inn)
        elif fio:
            return await self.parsers['fedresurs'].search_by_fio_dob(fio, dob)
        else:
            return {'success': False, 'error': 'No INN or FIO provided'}
    
    async def _enrich_rosreestr(self, inn: str) -> Dict[str, Any]:
        """Обогащение данными Росреестр"""
        if inn:
            return await self.parsers['rosreestr'].search_by_inn(inn)
        else:
            return {'success': False, 'error': 'No INN provided'}
    
    async def _enrich_courts(self, fio: str) -> Dict[str, Any]:
        """Обогащение данными судов"""
        if fio:
            return await self.parsers['courts'].search_by_fio_dob(fio, '')
        else:
            return {'success': False, 'error': 'No FIO provided'}
    
    async def _enrich_nalog(self, inn: str) -> Dict[str, Any]:
        """Обогащение данными налоговой"""
        if inn:
            return await self.parsers['nalog'].search_by_inn(inn)
        else:
            return {'success': False, 'error': 'No INN provided'}
    
    def _process_fssp_data(self, lead: Dict[str, Any], fssp_data: Dict[str, Any]):
        """Обработка данных ФССП"""
        items = fssp_data.get('items', [])
        total_debt = fssp_data.get('total_debt', 0)
        
        lead['total_debt'] += total_debt
        
        for item in items:
            debt_info = {
                'amount': item.get('amount', 0),
                'type': item.get('type', 'other'),
                'creditor': item.get('creditor', ''),
                'status': item.get('status', ''),
                'date': item.get('date', ''),
                'source': 'fssp'
            }
            lead['debts'].append(debt_info)
    
    def _process_fedresurs_data(self, lead: Dict[str, Any], fedresurs_data: Dict[str, Any]):
        """Обработка данных Федресурс"""
        lead['is_bankrupt'] = fedresurs_data.get('is_bankrupt', False)
        
        procedures = fedresurs_data.get('bankruptcy_procedures', [])
        if procedures:
            lead['bankruptcy_procedures'] = procedures
    
    def _process_rosreestr_data(self, lead: Dict[str, Any], rosreestr_data: Dict[str, Any]):
        """Обработка данных Росреестр"""
        lead['has_property'] = rosreestr_data.get('has_property', False)
        
        if rosreestr_data.get('properties'):
            lead['properties'] = rosreestr_data['properties']
    
    def _process_courts_data(self, lead: Dict[str, Any], courts_data: Dict[str, Any]):
        """Обработка данных судов"""
        orders = courts_data.get('court_orders', [])
        lead['court_orders'] = orders
        
        # Проверяем наличие недавних приказов
        from datetime import datetime, timedelta
        three_months_ago = datetime.now() - timedelta(days=90)
        
        for order in orders:
            order_date_str = order.get('date', '')
            if order_date_str:
                try:
                    order_date = datetime.strptime(order_date_str, '%d.%m.%Y')
                    if order_date >= three_months_ago:
                        lead['has_recent_court_order'] = True
                        break
                except ValueError:
                    continue
    
    def _process_nalog_data(self, lead: Dict[str, Any], nalog_data: Dict[str, Any]):
        """Обработка данных налоговой"""
        lead['inn_active'] = nalog_data.get('inn_active', True)
        
        tax_debt = nalog_data.get('tax_debt', 0)
        if tax_debt > 0:
            debt_info = {
                'amount': tax_debt,
                'type': 'tax',
                'creditor': 'ФНС России',
                'status': 'active',
                'source': 'nalog'
            }
            lead['debts'].append(debt_info)
            lead['total_debt'] += tax_debt
    
    async def get_enrichment_statistics(self) -> Dict[str, Any]:
        """Получение статистики работы парсеров"""
        stats = {}
        
        for parser_name, parser in self.parsers.items():
            stats[parser_name] = parser.get_statistics()
        
        return stats
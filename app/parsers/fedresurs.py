import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.parsers.base import BaseParser
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

class FedresursParser(BaseParser):
    """Парсер для Федресурса - проверка банкротства"""
    
    def __init__(self):
        super().__init__()
        self.base_url = settings.FEDRESURS_API_URL
        self.api_endpoints = {
            'search': f"{self.base_url}/search",
            'company': f"{self.base_url}/company",
            'bankruptcy': f"{self.base_url}/bankruptcy"
        }
        
    async def search_by_inn(self, inn: str) -> Dict[str, Any]:
        """Поиск информации о банкротстве по ИНН"""
        if not inn or len(inn) not in [10, 12]:
            return {'success': False, 'error': 'Invalid INN format'}
        
        try:
            # Ищем компанию/лицо по ИНН
            search_result = await self._search_entity(inn)
            if not search_result['success']:
                return search_result
            
            entities = search_result['data'].get('entities', [])
            if not entities:
                return {
                    'success': True,
                    'data': {
                        'is_bankrupt': False,
                        'bankruptcy_procedures': [],
                        'inn': inn
                    }
                }
            
            # Для каждой найденной сущности проверяем процедуры банкротства
            all_procedures = []
            is_bankrupt = False
            
            for entity in entities:
                entity_id = entity.get('id')
                if entity_id:
                    procedures = await self._get_bankruptcy_procedures(entity_id)
                    if procedures:
                        all_procedures.extend(procedures)
                        # Проверяем активные процедуры
                        for proc in procedures:
                            if proc.get('status') in ['active', 'ongoing']:
                                is_bankrupt = True
            
            self._log_request(self.api_endpoints['search'], 'error', error=error_msg)
            return {'success': False, 'error': error_msg}
    
    async def search_by_fio_dob(self, fio: str, dob: str) -> Dict[str, Any]:
        """Поиск информации о банкротстве по ФИО и дате рождения"""
        if not fio:
            return {'success': False, 'error': 'FIO is required'}
        
        try:
            search_result = await self._search_entity_by_name(fio, dob)
            if not search_result['success']:
                return search_result
            
            entities = search_result['data'].get('entities', [])
            if not entities:
                return {
                    'success': True,
                    'data': {
                        'is_bankrupt': False,
                        'bankruptcy_procedures': [],
                        'fio': fio
                    }
                }
            
            all_procedures = []
            is_bankrupt = False
            
            for entity in entities:
                entity_id = entity.get('id')
                if entity_id:
                    procedures = await self._get_bankruptcy_procedures(entity_id)
                    if procedures:
                        all_procedures.extend(procedures)
                        for proc in procedures:
                            if proc.get('status') in ['active', 'ongoing']:
                                is_bankrupt = True
            
            return {
                'success': True,
                'data': {
                    'is_bankrupt': is_bankrupt,
                    'bankruptcy_procedures': all_procedures,
                    'entities': entities,
                    'fio': fio
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Fedresurs search error for FIO {fio}: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    async def _search_entity(self, inn: str) -> Dict[str, Any]:
        """Поиск сущности по ИНН"""
        search_params = {
            'inn': inn,
            'type': 'all'
        }
        
        response = await self._make_request(
            self.api_endpoints['search'],
            method='GET',
            params=search_params
        )
        
        if not response:
            return {'success': False, 'error': 'Search request failed'}
        
        try:
            data = await response.json()
            return {
                'success': True,
                'data': data
            }
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON response: {str(e)}'}
    
    async def _search_entity_by_name(self, fio: str, dob: str = None) -> Dict[str, Any]:
        """Поиск сущности по ФИО"""
        search_params = {
            'name': fio,
            'type': 'person'
        }
        
        if dob:
            search_params['birthDate'] = dob
        
        response = await self._make_request(
            self.api_endpoints['search'],
            method='GET', 
            params=search_params
        )
        
        if not response:
            return {'success': False, 'error': 'Search request failed'}
        
        try:
            data = await response.json()
            return {
                'success': True,
                'data': data
            }
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON response: {str(e)}'}
    
    async def _get_bankruptcy_procedures(self, entity_id: str) -> Optional[list]:
        """Получение процедур банкротства для сущности"""
        try:
            response = await self._make_request(
                f"{self.api_endpoints['bankruptcy']}/{entity_id}",
                method='GET'
            )
            
            if not response:
                return []
            
            data = await response.json()
            procedures = data.get('procedures', [])
            
            # Обрабатываем и нормализуем данные процедур
            normalized_procedures = []
            for proc in procedures:
                normalized_proc = self._normalize_procedure_data(proc)
                if normalized_proc:
                    normalized_procedures.append(normalized_proc)
            
            return normalized_procedures
            
        except Exception as e:
            logger.error(f"Error getting bankruptcy procedures for entity {entity_id}: {str(e)}")
            return []
    
    def _normalize_procedure_data(self, procedure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Нормализация данных процедуры банкротства"""
        try:
            return {
                'id': procedure.get('id'),
                'type': procedure.get('type', ''),
                'status': self._normalize_status(procedure.get('status', '')),
                'start_date': procedure.get('startDate'),
                'end_date': procedure.get('endDate'),
                'court': procedure.get('court', ''),
                'case_number': procedure.get('caseNumber', ''),
                'manager': procedure.get('manager', {}),
                'debtor_type': procedure.get('debtorType', ''),
                'is_active': procedure.get('isActive', False),
                'procedure_stage': procedure.get('stage', ''),
                'debt_amount': procedure.get('debtAmount', 0)
            }
        except Exception as e:
            logger.error(f"Error normalizing procedure data: {str(e)}")
            return None
    
    def _normalize_status(self, status: str) -> str:
        """Нормализация статуса процедуры"""
        status_mapping = {
            'наблюдение': 'supervision',
            'финансовое оздоровление': 'financial_recovery',
            'внешнее управление': 'external_management', 
            'конкурсное производство': 'bankruptcy_proceedings',
            'мировое соглашение': 'settlement_agreement',
            'реструктуризация долгов': 'debt_restructuring',
            'реализация имущества': 'asset_realization',
            'завершено': 'completed',
            'прекращено': 'terminated',
            'активное': 'active',
            'в процессе': 'ongoing'
        }
        
        status_lower = status.lower().strip()
        return status_mapping.get(status_lower, status_lower)
    
    async def check_bankruptcy_status(self, inn: str = None, fio: str = None, dob: str = None) -> Dict[str, Any]:
        """Универсальная проверка статуса банкротства"""
        if inn:
            return await self.search_by_inn(inn)
        elif fio:
            return await self.search_by_fio_dob(fio, dob)
        else:
            return {'success': False, 'error': 'Either INN or FIO must be provided'}
    
    def is_person_bankrupt(self, search_result: Dict[str, Any]) -> bool:
        """Проверка, является ли лицо банкротом на основе результата поиска"""
        if not search_result.get('success'):
            return False
        
        data = search_result.get('data', {})
        
        # Прямая проверка флага
        if data.get('is_bankrupt'):
            return True
        
        # Проверка активных процедур
        procedures = data.get('bankruptcy_procedures', [])
        for proc in procedures:
            if proc.get('status') in ['active', 'ongoing', 'supervision', 'bankruptcy_proceedings']:
                return True
        
        return False
    
    def get_active_procedures(self, search_result: Dict[str, Any]) -> list:
        """Получение списка активных процедур банкротства"""
        if not search_result.get('success'):
            return []
        
        data = search_result.get('data', {})
        procedures = data.get('bankruptcy_procedures', [])
        
        active_procedures = []
        for proc in procedures:
            if proc.get('is_active') or proc.get('status') in ['active', 'ongoing']:
                active_procedures.append(proc)
        
        return active_procedures 'success', 
                            {'inn': inn, 'procedures_count': len(all_procedures)})
            
            return {
                'success': True,
                'data': {
                    'is_bankrupt': is_bankrupt,
                    'bankruptcy_procedures': all_procedures,
                    'entities': entities,
                    'inn': inn
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Fedresurs search error for INN {inn}: {str(e)}"
            logger.error(error_msg)
            self._log_request(self.api_endpoints['search'], 
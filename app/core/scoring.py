from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

class BankruptcyScorer:
    """Класс для расчета скоринга потенциальных банкротов"""
    
    def __init__(self):
        self.scoring_rules = self._init_scoring_rules()
        self.group_definitions = self._init_group_definitions()
    
    def _init_scoring_rules(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация правил скоринга согласно ТЗ"""
        return {
            'high_debt': {
                'points': 30,
                'condition': lambda data: data.get('total_debt', 0) > settings.HIGH_DEBT_THRESHOLD,
                'reason': f"Сумма долгов больше {settings.HIGH_DEBT_THRESHOLD:,} рублей"
            },
            'bank_mfo_debt': {
                'points': 20,
                'condition': lambda data: self._has_bank_or_mfo_debt(data),
                'reason': "Долг от банка или МФО"
            },
            'no_property': {
                'points': 10,
                'condition': lambda data: not data.get('has_property', False),
                'reason': "Нет имущества"
            },
            'recent_court_order': {
                'points': 15,
                'condition': lambda data: self._has_recent_court_order(data),
                'reason': "Судебный приказ за последние 3 месяца"
            },
            'no_bankruptcy_signs': {
                'points': 10,
                'condition': lambda data: not data.get('is_bankrupt', False),
                'reason': "Нет признаков банкротства"
            },
            'active_inn': {
                'points': 5,
                'condition': lambda data: data.get('inn_active', True),
                'reason': "ИНН активен"
            },
            'multiple_debts': {
                'points': 5,
                'condition': lambda data: len(data.get('debts', [])) > 2,
                'reason': "Более двух долгов"
            },
            'low_debt_penalty': {
                'points': -15,
                'condition': lambda data: data.get('total_debt', 0) < settings.MIN_DEBT_AMOUNT,
                'reason': f"Долг менее {settings.MIN_DEBT_AMOUNT:,} рублей"
            },
            'tax_utilities_only': {
                'points': -10,
                'condition': lambda data: self._only_tax_utilities_debts(data),
                'reason': "Только налоговые долги или ЖКХ"
            },
            'bankrupt_exclusion': {
                'points': -100,
                'condition': lambda data: data.get('is_bankrupt', False),
                'reason': "Человек признан банкротом"
            },
            'dead_inn_exclusion': {
                'points': -100,
                'condition': lambda data: not data.get('inn_active', True) or data.get('is_dead', False),
                'reason': "ИНН мертвый или человек умер/в розыске"
            }
        }
    
    def _init_group_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Определения групп для A/B тестирования"""
        return {
            'high_debt_recent_court': {
                'condition': lambda data: (
                    data.get('total_debt', 0) > settings.HIGH_DEBT_THRESHOLD and
                    self._has_recent_court_order(data)
                ),
                'priority': 1
            },
            'bank_only_no_property': {
                'condition': lambda data: (
                    self._has_bank_or_mfo_debt(data) and
                    not data.get('has_property', False)
                ),
                'priority': 2
            },
            'multiple_debts_active': {
                'condition': lambda data: (
                    len(data.get('debts', [])) > 2 and
                    data.get('inn_active', True)
                ),
                'priority': 3
            },
            'medium_debt_property': {
                'condition': lambda data: (
                    settings.MIN_DEBT_AMOUNT < data.get('total_debt', 0) < settings.HIGH_DEBT_THRESHOLD and
                    data.get('has_property', False)
                ),
                'priority': 4
            },
            'default': {
                'condition': lambda data: True,
                'priority': 999
            }
        }
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Основная функция расчета скоринга"""
        try:
            score = 0
            applied_rules = []
            reasons = []
            
            # Применяем все правила скоринга
            for rule_name, rule_config in self.scoring_rules.items():
                if rule_config['condition'](lead_data):
                    score += rule_config['points']
                    applied_rules.append(rule_name)
                    reasons.append(rule_config['reason'])
            
            # Ограничиваем скор диапазоном 0-100
            score = max(0, min(100, score))
            
            # Определяем является ли лид целевым
            is_target = self._is_target_lead(score, lead_data)
            
            # Определяем группу для A/B тестов
            group = self._determine_group(lead_data)
            
            # Ограничиваем количество причин до 3
            top_reasons = reasons[:3] if len(reasons) > 3 else reasons
            while len(top_reasons) < 3:
                top_reasons.append("")
            
            result = {
                'score': score,
                'is_target': is_target,
                'reason_1': top_reasons[0],
                'reason_2': top_reasons[1], 
                'reason_3': top_reasons[2],
                'group': group,
                'applied_rules': applied_rules,
                'calculation_details': self._get_calculation_details(lead_data, applied_rules)
            }
            
            logger.debug(f"Calculated score {score} for lead with rules: {applied_rules}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating score: {str(e)}")
            return {
                'score': 0,
                'is_target': False,
                'reason_1': "Ошибка расчета скоринга",
                'reason_2': "",
                'reason_3': "",
                'group': 'error',
                'applied_rules': [],
                'error': str(e)
            }
    
    def _is_target_lead(self, score: int, lead_data: Dict[str, Any]) -> bool:
        """Определение является ли лид целевым"""
        # Базовое условие - скор >= 50
        if score < settings.MIN_SCORE_THRESHOLD:
            return False
        
        # Дополнительные исключения
        if lead_data.get('is_bankrupt', False):
            return False
        
        if not lead_data.get('inn_active', True):
            return False
        
        if lead_data.get('is_dead', False):
            return False
        
        return True
    
    def _determine_group(self, lead_data: Dict[str, Any]) -> str:
        """Определение группы для A/B тестирования"""
        # Сортируем группы по приоритету
        sorted_groups = sorted(
            self.group_definitions.items(),
            key=lambda x: x[1]['priority']
        )
        
        # Находим первую подходящую группу
        for group_name, group_config in sorted_groups:
            if group_config['condition'](lead_data):
                return group_name
        
        return 'default'
    
    def _has_bank_or_mfo_debt(self, data: Dict[str, Any]) -> bool:
        """Проверка наличия долгов от банков или МФО"""
        debts = data.get('debts', [])
        return any(
            debt.get('type') in ['bank', 'mfo'] 
            for debt in debts
        )
    
    def _has_recent_court_order(self, data: Dict[str, Any]) -> bool:
        """Проверка наличия судебного приказа за последние 3 месяца"""
        court_orders = data.get('court_orders', [])
        three_months_ago = datetime.now() - timedelta(days=90)
        
        for order in court_orders:
            order_date_str = order.get('date')
            if order_date_str:
                try:
                    order_date = datetime.strptime(order_date_str, '%d.%m.%Y')
                    if order_date >= three_months_ago:
                        return True
                except ValueError:
                    continue
        
        return False
    
    def _only_tax_utilities_debts(self, data: Dict[str, Any]) -> bool:
        """Проверка что есть только налоговые долги или ЖКХ"""
        debts = data.get('debts', [])
        if not debts:
            return False
        
        debt_types = {debt.get('type') for debt in debts}
        allowed_types = {'tax', 'utilities'}
        
        return debt_types.issubset(allowed_types) and len(debt_types) > 0
    
    def _get_calculation_details(self, lead_data: Dict[str, Any], applied_rules: List[str]) -> Dict[str, Any]:
        """Получение детальной информации о расчете"""
        details = {
            'total_debt': lead_data.get('total_debt', 0),
            'debt_count': len(lead_data.get('debts', [])),
            'has_property': lead_data.get('has_property', False),
            'inn_active': lead_data.get('inn_active', True),
            'is_bankrupt': lead_data.get('is_bankrupt', False),
            'applied_rules_count': len(applied_rules),
            'debt_breakdown': self._get_debt_breakdown(lead_data.get('debts', []))
        }
        
        return details
    
    def _get_debt_breakdown(self, debts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Разбивка долгов по типам"""
        breakdown = {
            'bank': {'count': 0, 'amount': 0},
            'mfo': {'count': 0, 'amount': 0},
            'tax': {'count': 0, 'amount': 0},
            'utilities': {'count': 0, 'amount': 0},
            'other': {'count': 0, 'amount': 0}
        }
        
        for debt in debts:
            debt_type = debt.get('type', 'other')
            amount = debt.get('amount', 0)
            
            if debt_type in breakdown:
                breakdown[debt_type]['count'] += 1
                breakdown[debt_type]['amount'] += amount
            else:
                breakdown['other']['count'] += 1
                breakdown['other']['amount'] += amount
        
        return breakdown
    
    def batch_score_leads(self, leads_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Массовый расчет скоринга для списка лидов"""
        results = []
        
        for lead_data in leads_data:
            score_result = self.calculate_score(lead_data)
            score_result['lead_id'] = lead_data.get('lead_id')
            results.append(score_result)
        
        logger.info(f"Processed {len(results)} leads for scoring")
        return results
    
    def filter_target_leads(self, scored_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Фильтрация целевых лидов"""
        target_leads = [
            lead for lead in scored_leads 
            if lead.get('is_target', False)
        ]
        
        # Сортируем по убыванию скора
        target_leads.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"Filtered {len(target_leads)} target leads from {len(scored_leads)} total")
        return target_leads
    
    def get_scoring_statistics(self, scored_leads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Получение статистики по скорингу"""
        if not scored_leads:
            return {}
        
        scores = [lead.get('score', 0) for lead in scored_leads]
        target_count = sum(1 for lead in scored_leads if lead.get('is_target', False))
        
        # Группировка по группам
        groups_stats = {}
        for lead in scored_leads:
            group = lead.get('group', 'unknown')
            if group not in groups_stats:
                groups_stats[group] = 0
            groups_stats[group] += 1
        
        # Группировка по скорам
        score_ranges = {
            '0-25': 0,
            '26-50': 0, 
            '51-75': 0,
            '76-100': 0
        }
        
        for score in scores:
            if score <= 25:
                score_ranges['0-25'] += 1
            elif score <= 50:
                score_ranges['26-50'] += 1
            elif score <= 75:
                score_ranges['51-75'] += 1
            else:
                score_ranges['76-100'] += 1
        
        return {
            'total_leads': len(scored_leads),
            'target_leads': target_count,
            'target_percentage': (target_count / len(scored_leads)) * 100,
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'groups_distribution': groups_stats,
            'score_ranges': score_ranges
        }
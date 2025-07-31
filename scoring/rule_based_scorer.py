from datetime import datetime

def calculate_score(lead: dict, min_debt: int) -> (int, list):
    """Расчет скоринга по правилам ТЗ"""
    score = 0
    reasons = []
    
    # Правила добавления баллов
    if lead.get('debt_amount', 0) > min_debt:
        score += 30
        reasons.append(f"Долг > {min_debt} руб")
    
    if lead.get('has_bank_mfo_debt', False):
        score += 20
        reasons.append("Долг банка/МФО")
    
    if not lead.get('has_property', True):
        score += 10
        reasons.append("Нет имущества")
    
    if lead.get('has_recent_court_order', False):
        score += 15
        reasons.append("Суд.приказ (3 мес)")
    
    if not lead.get('is_bankrupt', False):
        score += 10
        reasons.append("Нет банкротства")
    
    if lead.get('is_inn_active', False):
        score += 5
        reasons.append("ИНН активен")
    
    if lead.get('debt_count', 0) > 2:
        score += 5
        reasons.append(">2 долгов")
    
    # Правила уменьшения баллов
    if lead.get('debt_amount', 0) < 100000:
        score -= 15
        reasons.append("Долг < 100000 руб")
    
    if lead.get('only_tax_utility_debts', False):
        score -= 10
        reasons.append("Только налоги/ЖКХ")
    
    # Дисквалифицирующие факторы
    if lead.get('is_bankrupt', False):
        score -= 100
        reasons = ["Признан банкротом"]
    
    if not lead.get('is_inn_active', False) or lead.get('is_wanted', False) or lead.get('is_dead', False):
        score -= 100
        reasons = ["ИНН неактивен/розыск/смерть"]
    
    # Ограничение диапазона
    score = max(0, min(100, score))
    
    return int(score), reasons[:3]  # Возвращаем только 3 основные причины

def assign_group(lead: dict) -> str:
    """Назначение группы для A/B тестов"""
    if lead.get('debt_amount', 0) > 500000 and lead.get('has_recent_court_order', False):
        return "high_debt_recent_court"
    elif lead.get('has_bank_mfo_debt', False) and not lead.get('has_property', False):
        return "bank_only_no_property"
    elif lead.get('debt_count', 0) > 5:
        return "multiple_debts"
    else:
        return "other"
    
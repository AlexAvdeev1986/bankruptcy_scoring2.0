from datetime import datetime, timedelta

def calculate_score(lead: dict, min_debt: int) -> (int, list):
    """Расчет скоринга по правилам ТЗ"""
    score = 0
    reasons = []
    
    # Правила добавления баллов
    debt_amount = lead.get('debt_amount', 0)
    if debt_amount > min_debt:
        score += 30
        reasons.append(f"Долг > {min_debt} руб")
    
    if lead.get('has_bank_mfo_debt', False):
        score += 20
        reasons.append("Долг банка/МФО")
    
    if not lead.get('has_property', True):
        score += 10
        reasons.append("Нет имущества")
    
    # Проверка свежести судебного приказа
    court_order_date = lead.get('court_order_date')
    if court_order_date:
        order_date = datetime.strptime(court_order_date, '%Y-%m-%d')
        if datetime.now() - order_date < timedelta(days=90):
            score += 15
            reasons.append("Суд.приказ (3 мес)")
            lead['has_recent_court_order'] = True
        else:
            lead['has_recent_court_order'] = False
    
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
    if debt_amount < 100000:
        score -= 15
        reasons.append("Долг < 100000 руб")
    
    if lead.get('only_tax_utility_debts', False):
        score -= 10
        reasons.append("Только налоги/ЖКХ")
    
    # Дисквалифицирующие факторы
    if lead.get('is_bankrupt', False):
        score = 0
        reasons = ["Признан банкротом"]
    
    if not lead.get('is_inn_active', False):
        score = 0
        reasons = ["ИНН неактивен"]
    
    if lead.get('is_wanted', False):
        score = 0
        reasons = ["В розыске"]
    
    if lead.get('is_dead', False):
        score = 0
        reasons = ["Смерть"]
    
    # Ограничение диапазона
    score = max(0, min(100, score))
    
    return int(score), reasons[:3]  # Возвращаем только 3 основные причины

def assign_group(lead: dict) -> str:
    """Назначение группы для A/B тестов"""
    debt_amount = lead.get('debt_amount', 0)
    
    if debt_amount > 500000 and lead.get('has_recent_court_order', False):
        return "high_debt_recent_court"
    elif lead.get('has_bank_mfo_debt', False) and not lead.get('has_property', False):
        return "bank_only_no_property"
    elif lead.get('debt_count', 0) > 5:
        return "multiple_debts"
    else:
        return "other"
    
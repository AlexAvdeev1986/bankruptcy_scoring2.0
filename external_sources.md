# Внешние источники данных в Bankruptcy Scoring

## 1. Федеральная служба судебных приставов (ФССП)

### Источник: https://fssp.gov.ru/
### API: https://api-ip.fssprus.ru/

**Получаемые данные:**
- Сумма задолженности по исполнительным производствам
- Количество активных исполнительных производств  
- История взысканий
- Статус должника

**Метод доступа:**
```python
# app/services/fssp_service.py
async def get_debt_info(self, inn: str) -> Dict[str, Any]:
    # Использует Playwright для обхода защиты от ботов
    # Парсит веб-интерфейс ФССП
    # Извлекает данные о долгах и производствах
```

**Пример запроса:**
- URL: `https://fssp.gov.ru/iss/ip`
- Поиск по ИНН компании
- Автоматизация через Playwright (Chromium/Firefox)

## 2. Единый федеральный реестр сведений о банкротстве (Федресурс)

### Источник: https://fedresurs.ru/
### API: https://fedresurs.ru/api

**Получаемые данные:**
- Активные дела о банкротстве
- История банкротных процедур
- Стадии банкротства
- Назначенные арбитражные управляющие
- Требования кредиторов

**Метод доступа:**
```python
# app/services/fedresurs_service.py
async def get_bankruptcy_info(self, inn: str) -> Dict[str, Any]:
    # REST API запросы к Федресурс
    # Получение данных о банкротстве
    # Обработка JSON ответов
```

**Пример API запросов:**
```bash
GET https://fedresurs.ru/api/companies/search?inn={INN}
GET https://fedresurs.ru/api/bankruptcy-cases/{company_id}
```

## 3. Росреестр (дополнительные данные о недвижимости)

### Источник: https://rosreestr.ru/
### API: https://rosreestr.ru/api

**Получаемые данные:**
- Объекты недвижимости в собственности
- Обременения и аресты
- Стоимость недвижимого имущества
- История сделок

**Метод доступа:**
```python
# app/services/rosreestr_service.py
async def get_property_info(self, inn: str) -> Dict[str, Any]:
    # Поиск недвижимости по ИНН
    # Получение данных об объектах
    # Расчет общей стоимости активов
```

## 4. Дополнительные источники данных

### 4.1 Центральный банк РФ (опционально)
- **Источник:** https://cbr.ru/
- **Данные:** Банковские лицензии, финансовая отчетность банков

### 4.2 ФНС России (налоговая служба)
- **Источник:** https://nalog.ru/
- **Данные:** Налоговые задолженности, штрафы, пени

### 4.3 Картотека арбитражных дел
- **Источник:** https://kad.arbitr.ru/
- **Данные:** Арбитражные споры, судебные решения

## 5. Настройка внешних источников

### 5.1 Конфигурация API
```python
# app/core/config.py
class Settings(BaseSettings):
    # URLs внешних API
    FSSP_API_URL: str = "https://api-ip.fssprus.ru"
    FEDRESURS_API_URL: str = "https://fedresurs.ru/api"
    ROSREESTR_API_URL: str = "https://rosreestr.ru/api"
    
    # Настройки прокси для обхода ограничений
    USE_PROXY: bool = True
    PROXY_LIST: list = [
        "http://proxy1:port",
        "http://proxy2:port",
        "http://proxy3:port"
    ]
    
    # Настройки Playwright
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit
    HEADLESS: bool = True
    
    # Лимиты запросов
    MAX_REQUESTS_PER_MINUTE: int = 60
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 5
```

### 5.2 Управление прокси
```python
# app/services/proxy_manager.py
import random
from typing import Optional, Dict, Any

class ProxyManager:
    def __init__(self):
        self.proxies = settings.PROXY_LIST
        self.current_proxy_index = 0
        self.failed_proxies = set()
    
    async def get_proxy(self) -> Optional[Dict[str, Any]]:
        """Получение рабочего прокси"""
        if not self.proxies:
            return None
            
        # Исключаем неработающие прокси
        available_proxies = [
            proxy for proxy in self.proxies 
            if proxy not in self.failed_proxies
        ]
        
        if not available_proxies:
            # Сброс списка неработающих прокси
            self.failed_proxies.clear()
            available_proxies = self.proxies
        
        proxy = random.choice(available_proxies)
        
        return {
            "server": proxy,
            "username": None,  # Добавить если нужна авторизация
            "password": None
        }
    
    def mark_proxy_failed(self, proxy: str):
        """Отметка прокси как неработающего"""
        self.failed_proxies.add(proxy)
```

### 5.3 Обработка ошибок и повторных попыток
```python
# app/utils/retry_handler.py
import asyncio
import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

def retry_async(max_attempts: int = 3, delay: int = 1):
    """Декоратор для повторных попыток асинхронных функций"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}"
                    )
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
            
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator
```

## 6. Ограничения и рекомендации

### 6.1 Лимиты запросов
- **ФССП:** ~100 запросов в минуту (неофициально)
- **Федресурс:** 1000 запросов в день по API
- **Росреестр:** Ограничения по IP, требуется ротация

### 6.2 Обход блокировок
```python
# Настройки для обхода защиты
PLAYWRIGHT_OPTIONS = {
    'headless': True,
    'args': [
        '--no-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-web-security',
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    ]
}
```

### 6.3 Кэширование данных
```python
# app/services/cache_manager.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CacheManager:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(hours=24)  # Время жизни кэша
    
    def get(self, key: str) -> Optional[Any]:
        """Получение данных из кэша"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Сохранение данных в кэш"""
        self.cache[key] = (value, datetime.now())
    
    def clear_expired(self):
        """Очистка устаревших данных"""
        current_time = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
```

## 7. Мониторинг внешних источников

### 7.1 Логирование запросов
```python
# app/utils/api_logger.py
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.logs import APIRequestLog

class APILogger:
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    async def log_request(self, source: str, inn: str, status: str, response_time: float):
        """Логирование API запроса"""
        try:
            log_entry = APIRequestLog(
                source=source,
                inn=inn,
                status=status,
                response_time=response_time,
                timestamp=datetime.now()
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error logging API request: {e}")
```

### 7.2 Статистика по источникам
```python
# app/api/stats.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

router = APIRouter()

@router.get("/api-stats")
async def get_api_stats(db: Session = Depends(get_db)):
    """Статистика по внешним API"""
    stats = db.query(
        APIRequestLog.source,
        func.count(APIRequestLog.id).label('total_requests'),
        func.avg(APIRequestLog.response_time).label('avg_response_time'),
        func.count(
            func.case([(APIRequestLog.status == 'success', 1)])
        ).label('successful_requests')
    ).group_by(APIRequestLog.source).all()
    
    return {
        "api_statistics": [
            {
                "source": stat.source,
                "total_requests": stat.total_requests,
                "success_rate": stat.successful_requests / stat.total_requests * 100,
                "avg_response_time": round(stat.avg_response_time, 2)
            }
            for stat in stats
        ]
    }
```

## 8. Пример использования всех источников

```python
# app/core/data_enrichment.py
async def enrich_company_data(company_inn: str) -> Dict[str, Any]:
    """Обогащение данных компании из всех внешних источников"""
    
    results = {
        'inn': company_inn,
        'fssp_data': {},
        'fedresurs_data': {},
        'rosreestr_data': {},
        'enrichment_timestamp': datetime.now()
    }
    
    # Параллельное получение данных из всех источников
    tasks = [
        fssp_service.get_debt_info(company_inn),
        fedresurs_service.get_bankruptcy_info(company_inn),
        rosreestr_service.get_property_info(company_inn)
    ]
    
    try:
        fssp_data, fedresurs_data, rosreestr_data = await asyncio.gather(*tasks)
        
        results.update({
            'fssp_data': fssp_data,
            'fedresurs_data': fedresurs_data,
            'rosreestr_data': rosreestr_data
        })
        
    except Exception as e:
        logger.error(f"Error enriching data for {company_inn}: {e}")
    
    return results
```
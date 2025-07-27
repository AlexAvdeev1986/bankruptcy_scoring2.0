import asyncio
import aiohttp
import random
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from fake_useragent import UserAgent
from app.utils.logger import get_logger
from app.utils.proxy import ProxyManager
from app.config import settings
import time

logger = get_logger(__name__)

class BaseParser(ABC):
    """Базовый класс для всех парсеров внешних источников"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.proxy_manager = ProxyManager()
        self.ua = UserAgent()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.init_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()
        
    async def init_session(self):
        """Инициализация HTTP сессии"""
        timeout = aiohttp.ClientTimeout(total=settings.PROXY_TIMEOUT)
        connector = aiohttp.TCPConnector(
            limit=settings.CONCURRENT_REQUESTS,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=self._get_default_headers()
        )
        
    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            
    def _get_default_headers(self) -> Dict[str, str]:
        """Получение стандартных заголовков"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Выполнение HTTP запроса с обработкой ошибок и ретраями"""
        
        # Контроль частоты запросов
        await self._rate_limit()
        
        for attempt in range(settings.MAX_RETRIES):
            proxy = None
            if settings.USE_PROXY:
                proxy = await self.proxy_manager.get_proxy()
                
            try:
                # Обновляем User-Agent для каждого запроса
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['User-Agent'] = self.ua.random
                
                if proxy:
                    kwargs['proxy'] = proxy
                
                async with self.session.request(method, url, **kwargs) as response:
                    self.request_count += 1
                    
                    if response.status == 200:
                        return response
                    elif response.status == 429:  # Rate limiting
                        wait_time = 2 ** attempt + random.uniform(0, 1)
                        logger.warning(f"Rate limited, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                    elif response.status in [403, 404]:
                        logger.warning(f"HTTP {response.status} for {url}")
                        if proxy:
                            await self.proxy_manager.mark_proxy_bad(proxy)
                        break
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
                if proxy:
                    await self.proxy_manager.mark_proxy_bad(proxy)
                    
            except aiohttp.ClientError as e:
                logger.warning(f"Client error for {url}: {str(e)} (attempt {attempt + 1})")
                if proxy:
                    await self.proxy_manager.mark_proxy_bad(proxy)
                    
            except Exception as e:
                logger.error(f"Unexpected error for {url}: {str(e)} (attempt {attempt + 1})")
                
            if attempt < settings.MAX_RETRIES - 1:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                await asyncio.sleep(wait_time)
        
        self.error_count += 1
        return None
    
    async def _rate_limit(self):
        """Контроль частоты запросов"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < settings.REQUEST_DELAY:
            sleep_time = settings.REQUEST_DELAY - time_since_last
            await asyncio.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    @abstractmethod
    async def search_by_inn(self, inn: str) -> Dict[str, Any]:
        """Поиск информации по ИНН"""
        pass
    
    @abstractmethod 
    async def search_by_fio_dob(self, fio: str, dob: str) -> Dict[str, Any]:
        """Поиск информации по ФИО и дате рождения"""
        pass
    
    def _log_request(self, url: str, status: str, response_data: Optional[Dict] = None, error: Optional[str] = None):
        """Логирование запроса"""
        log_data = {
            'url': url,
            'status': status,
            'response_data': response_data,
            'error': error,
            'parser': self.__class__.__name__
        }
        
        if status == 'success':
            logger.info(f"Successful request to {url}")
        else:
            logger.error(f"Failed request to {url}: {error}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики работы парсера"""
        return {
            'parser_name': self.__class__.__name__,
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'success_rate': (self.request_count - self.error_count) / max(self.request_count, 1) * 100
        }
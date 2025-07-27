import asyncio
import random
from typing import List, Optional, Set
from app.utils.logger import get_logger
from app.config import settings
import os

logger = get_logger(__name__)

class ProxyManager:
    """Менеджер для управления прокси-серверами"""
    
    def __init__(self):
        self.proxies: List[str] = []
        self.bad_proxies: Set[str] = set()
        self.current_index = 0
        self.lock = asyncio.Lock()
        
    async def load_proxies(self):
        """Загрузка списка прокси из файла"""
        if not os.path.exists(settings.PROXY_LIST_FILE):
            logger.warning(f"Proxy file not found: {settings.PROXY_LIST_FILE}")
            return
        
        try:
            with open(settings.PROXY_LIST_FILE, 'r', encoding='utf-8') as f:
                self.proxies = [
                    line.strip() for line in f.readlines() 
                    if line.strip() and not line.startswith('#')
                ]
            
            logger.info(f"Loaded {len(self.proxies)} proxies")
            
        except Exception as e:
            logger.error(f"Error loading proxies: {str(e)}")
    
    async def get_proxy(self) -> Optional[str]:
        """Получение следующего рабочего прокси"""
        if not settings.USE_PROXY:
            return None
        
        if not self.proxies:
            await self.load_proxies()
        
        if not self.proxies:
            return None
        
        async with self.lock:
            # Фильтруем рабочие прокси
            working_proxies = [p for p in self.proxies if p not in self.bad_proxies]
            
            if not working_proxies:
                # Если все прокси плохие, сбрасываем список плохих
                logger.warning("All proxies marked as bad, resetting bad proxies list")
                self.bad_proxies.clear()
                working_proxies = self.proxies.copy()
            
            if not working_proxies:
                return None
            
            # Используем случайный прокси для лучшего распределения нагрузки
            proxy = random.choice(working_proxies)
            
            # Форматируем прокси для aiohttp
            return self._format_proxy(proxy)
    
    def _format_proxy(self, proxy: str) -> str:
        """Форматирование прокси для использования в aiohttp"""
        if '://' not in proxy:
            # Добавляем протокол по умолчанию
            proxy = f'http://{proxy}'
        
        return proxy
    
    async def mark_proxy_bad(self, proxy: str):
        """Отметка прокси как неработающего"""
        if proxy:
            # Извлекаем оригинальный прокси без протокола
            original_proxy = proxy.replace('http://', '').replace('https://', '')
            
            async with self.lock:
                self.bad_proxies.add(original_proxy)
                logger.debug(f"Marked proxy as bad: {original_proxy}")
    
    async def test_proxy(self, proxy: str, test_url: str = "http://httpbin.org/ip") -> bool:
        """Тестирование прокси"""
        import aiohttp
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(test_url, proxy=proxy) as response:
                    if response.status == 200:
                        logger.debug(f"Proxy {proxy} is working")
                        return True
        except Exception as e:
            logger.debug(f"Proxy {proxy} failed test: {str(e)}")
        
        return False
    
    async def test_all_proxies(self):
        """Тестирование всех прокси"""
        if not self.proxies:
            await self.load_proxies()
        
        logger.info(f"Testing {len(self.proxies)} proxies...")
        
        tasks = []
        for proxy in self.proxies:
            formatted_proxy = self._format_proxy(proxy)
            task = asyncio.create_task(self.test_proxy(formatted_proxy))
            tasks.append((proxy, task))
        
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        working_count = 0
        for i, (proxy, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception) or not result:
                self.bad_proxies.add(proxy)
            else:
                working_count += 1
        
        logger.info(f"Proxy test completed: {working_count}/{len(self.proxies)} working")
    
    def get_statistics(self) -> dict:
        """Получение статистики прокси"""
        total_proxies = len(self.proxies)
        bad_proxies = len(self.bad_proxies)
        working_proxies = total_proxies - bad_proxies
        
        return {
            'total_proxies': total_proxies,
            'working_proxies': working_proxies,
            'bad_proxies': bad_proxies,
            'success_rate': (working_proxies / max(total_proxies, 1)) * 100
        }

# Создаем глобальный экземпляр
proxy_manager = ProxyManager()
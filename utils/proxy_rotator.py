import random
import logging

class ProxyRotator:
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.logger = logging.getLogger('ProxyRotator')
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
        ]
        
    def get_proxy(self) -> dict:
        """Получение случайного прокси"""
        proxy = random.choice(self.proxy_list)
        return {'http': proxy, 'https': proxy}
    
    def get_user_agent(self) -> str:
        """Получение случайного User-Agent"""
        return random.choice(self.user_agents)
    
    def report_bad_proxy(self, proxy_url: str):
        """Сообщение о нерабочем прокси"""
        if proxy_url in self.proxy_list:
            self.proxy_list.remove(proxy_url)
            self.logger.warning(f"Удален нерабочий прокси: {proxy_url}")
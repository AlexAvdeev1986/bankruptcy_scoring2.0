from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/bankruptcy_scoring"
    DATABASE_URL_SYNC: str = "postgresql+asyncpg://user:password@localhost:5432/bankruptcy_scoring"
    
    # Redis for caching and task queue
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Bankruptcy Scoring System"
    DEBUG: bool = True
    
    # External APIs
    FSSP_BASE_URL: str = "https://fssp.gov.ru"
    FEDRESURS_API_URL: str = "https://fedresurs.ru/backend/companies"
    ROSREESTR_BASE_URL: str = "https://rosreestr.gov.ru"
    NALOG_BASE_URL: str = "https://service.nalog.ru"
    
    # Proxy settings
    PROXY_LIST_FILE: str = "data/proxies.txt"
    USE_PROXY: bool = True
    PROXY_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    
    # Parsing settings
    REQUEST_DELAY: float = 1.0
    BATCH_SIZE: int = 100
    CONCURRENT_REQUESTS: int = 10
    
    # File paths
    INPUT_DIR: str = "data/input"
    OUTPUT_DIR: str = "data/output"
    LOGS_DIR: str = "data/logs"
    
    # Scoring thresholds
    MIN_DEBT_AMOUNT: int = 100000
    HIGH_DEBT_THRESHOLD: int = 250000
    MIN_SCORE_THRESHOLD: int = 50
    
    # Regions
    AVAILABLE_REGIONS: List[str] = [
        "Москва", "Санкт-Петербург", "Татарстан", "Саратов", 
        "Калуга", "Краснодар", "Екатеринбург", "Новосибирск"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
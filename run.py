#!/usr/bin/env python3
"""
Точка входа для запуска системы скоринга банкротства
"""

import asyncio
import uvicorn
from app.main import app
from app.config import settings
from app.database import init_db_sync
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """Основная функция запуска"""
    logger.info("Starting Bankruptcy Scoring System...")
    
    # Инициализация базы данных (синхронно)
    try:
        init_db_sync()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return
    
    # Запуск веб-сервера
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
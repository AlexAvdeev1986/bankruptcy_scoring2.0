from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import json
import asyncio
from datetime import datetime

from app.config import settings
from app.database import get_async_db, init_db
from app.schemas import ScoringRequest, ProcessingStatus
from app.core.normalization import DataNormalizer
from app.core.scoring import BankruptcyScorer
from app.core.enrichment import DataEnrichment
from app.utils.logger import get_logger
from app.api.endpoints import router as api_router

# Инициализация
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутов
app.include_router(api_router, prefix=settings.API_V1_STR)

# Статические файлы и шаблоны
templates = Jinja2Templates(directory="app/templates")

# Создание директорий
os.makedirs(settings.INPUT_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)

logger = get_logger(__name__)

# Глобальные переменные для отслеживания статуса
processing_status = {
    'status': 'idle',
    'message': 'Система готова к работе',
    'progress': 0,
    'total_leads': 0,
    'processed_leads': 0,
    'target_leads': 0,
    'errors_count': 0,
    'started_at': None,
    'completed_at': None
}

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Starting Bankruptcy Scoring System...")
    await init_db()
    logger.info("Database initialized")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница"""
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "available_regions": settings.AVAILABLE_REGIONS,
            "status": processing_status
        }
    )

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Страница логов"""
    # Читаем последние логи
    logs = []
    log_file = os.path.join(settings.LOGS_DIR, "app.log")
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                logs = lines[-100:]  # Последние 100 строк
        except Exception as e:
            logs = [f"Ошибка чтения логов: {str(e)}"]
    
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "logs": logs
        }
    )

@app.post("/start-scoring")
async def start_scoring(
    background_tasks: BackgroundTasks,
    regions: List[str] = Form(...),
    min_debt_amount: int = Form(250000),
    exclude_bankrupts: bool = Form(False),
    exclude_no_debts: bool = Form(False),
    only_with_property: bool = Form(False),
    only_bank_mfo_debts: bool = Form(False),
    only_recent_court_orders: bool = Form(False),
    only_active_inn: bool = Form(False)
):
    """Запуск процесса скоринга"""
    
    if processing_status['status'] == 'running':
        return JSONResponse(
            status_code=400,
            content={"error": "Скоринг уже выполняется"}
        )
    
    scoring_request = ScoringRequest(
        regions=regions,
        min_debt_amount=min_debt_amount,
        exclude_bankrupts=exclude_bankrupts,
        exclude_no_debts=exclude_no_debts,
        only_with_property=only_with_property,
        only_bank_mfo_debts=only_bank_mfo_debts,
        only_recent_court_orders=only_recent_court_orders,
        only_active_inn=only_active_inn
    )
    
    # Запускаем процесс в фоне
    background_tasks.add_task(run_scoring_process, scoring_request)
    
    return JSONResponse(
        content={
            "status": "started",
            "message": "Скоринг запущен в фоновом режиме"
        }
    )

@app.get("/status")
async def get_status():
    """Получение статуса выполнения"""
    return JSONResponse(content=processing_status)

@app.get("/download-result")
async def download_result():
    """Скачивание результата"""
    result_file = os.path.join(settings.OUTPUT_DIR, "scoring_ready.csv")
    
    if not os.path.exists(result_file):
        return JSONResponse(
            status_code=404,
            content={"error": "Файл результатов не найден"}
        )
    
    return FileResponse(
        result_file,
        media_type='text/csv',
        filename="scoring_ready.csv"
    )

@app.post("/upload-csv")
async def upload_csv(files: List[UploadFile] = File(...)):
    """Загрузка CSV файлов"""
    try:
        uploaded_files = []
        
        for file in files:
            if not file.filename.endswith('.csv'):
                continue
                
            file_path = os.path.join(settings.INPUT_DIR, file.filename)
            
            with open(file_path, 'wb') as f:
                content = await file.read()
                f.write(content)
            
            uploaded_files.append(file.filename)
            logger.info(f"Uploaded file: {file.filename}")
        
        return JSONResponse(
            content={
                "status": "success",
                "uploaded_files": uploaded_files,
                "message": f"Загружено {len(uploaded_files)} файлов"
            }
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Ошибка загрузки: {str(e)}"}
        )

async def run_scoring_process(request: ScoringRequest):
    """Основной процесс скоринга"""
    global processing_status
    
    try:
        # Обновляем статус
        processing_status.update({
            'status': 'running',
            'message': 'Инициализация процесса скоринга...',
            'progress': 0,
            'started_at': datetime.now(),
            'errors_count': 0
        })
        
        logger.info("Starting scoring process with filters:", extra={'filters': request.dict()})
        
        # Этап 1: Нормализация данных
        processing_status.update({
            'message': 'Нормализация входных данных...',
            'progress': 10
        })
        
        normalizer = DataNormalizer()
        csv_files = []
        
        # Ищем CSV файлы в директории input
        for filename in os.listdir(settings.INPUT_DIR):
            if filename.endswith('.csv'):
                csv_files.append(os.path.join(settings.INPUT_DIR, filename))
        
        if not csv_files:
            raise Exception("Не найдено CSV файлов для обработки")
        
        normalized_data = normalizer.normalize_csv_files(csv_files)
        
        if normalized_data.empty:
            raise Exception("После нормализации не осталось данных")
        
        processing_status.update({
            'total_leads': len(normalized_data),
            'message': f'Нормализовано {len(normalized_data)} записей',
            'progress': 20
        })
        
        # Этап 2: Фильтрация по регионам
        if request.regions:
            normalized_data = normalized_data[
                normalized_data['region'].isin(request.regions)
            ]
            logger.info(f"Filtered by regions: {len(normalized_data)} records remain")
        
        processing_status.update({
            'message': 'Обогащение данными из внешних источников...',
            'progress': 30
        })
        
        # Этап 3: Обогащение данными
        enrichment = DataEnrichment()
        enriched_data = []
        
        batch_size = settings.BATCH_SIZE
        total_batches = (len(normalized_data) + batch_size - 1) // batch_size
        
        for i, batch_start in enumerate(range(0, len(normalized_data), batch_size)):
            batch_end = min(batch_start + batch_size, len(normalized_data))
            batch_df = normalized_data.iloc[batch_start:batch_end]
            
            # Обогащаем батч
            batch_enriched = await enrichment.enrich_batch(batch_df.to_dict('records'))
            enriched_data.extend(batch_enriched)
            
            # Обновляем прогресс
            progress = 30 + (i + 1) / total_batches * 40  # 30-70%
            processing_status.update({
                'processed_leads': len(enriched_data),
                'progress': int(progress),
                'message': f'Обработано {len(enriched_data)} из {len(normalized_data)} записей'
            })
        
        # Этап 4: Расчет скоринга
        processing_status.update({
            'message': 'Расчет скоринга...',
            'progress': 70
        })
        
        scorer = BankruptcyScorer()
        scored_leads = scorer.batch_score_leads(enriched_data)
        
        # Этап 5: Применение фильтров
        processing_status.update({
            'message': 'Применение фильтров...',
            'progress': 80
        })
        
        filtered_leads = apply_filters(scored_leads, request)
        
        # Этап 6: Создание выходного файла
        processing_status.update({
            'message': 'Создание выходного файла...',
            'progress': 90
        })
        
        output_file = create_output_csv(filtered_leads)
        
        # Завершение
        processing_status.update({
            'status': 'completed',
            'message': f'Скоринг завершен. Найдено {len(filtered_leads)} целевых контактов',
            'progress': 100,
            'target_leads': len(filtered_leads),
            'completed_at': datetime.now()
        })
        
        logger.info(f"Scoring process completed. Target leads: {len(filtered_leads)}")
        
    except Exception as e:
        error_msg = f"Ошибка при выполнении скоринга: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        processing_status.update({
            'status': 'error',
            'message': error_msg,
            'errors_count': processing_status.get('errors_count', 0) + 1
        })

def apply_filters(scored_leads: List[Dict], request: ScoringRequest) -> List[Dict]:
    """Применение фильтров к результатам скоринга"""
    filtered = scored_leads.copy()
    
    # Базовая фильтрация - только целевые лиды с score >= 50
    filtered = [lead for lead in filtered if lead.get('is_target', False)]
    
    # Дополнительные фильтры
    if request.exclude_bankrupts:
        filtered = [lead for lead in filtered if not lead.get('is_bankrupt', False)]
    
    if request.exclude_no_debts:
        filtered = [lead for lead in filtered if lead.get('total_debt', 0) > 0]
    
    if request.only_with_property:
        filtered = [lead for lead in filtered if lead.get('has_property', False)]
    
    if request.only_bank_mfo_debts:
        filtered = [lead for lead in filtered 
                   if any(debt.get('type') in ['bank', 'mfo'] 
                         for debt in lead.get('debts', []))]
    
    if request.only_recent_court_orders:
        filtered = [lead for lead in filtered if lead.get('has_recent_court_order', False)]
    
    if request.only_active_inn:
        filtered = [lead for lead in filtered if lead.get('inn_active', True)]
    
    # Фильтр по минимальной сумме долга
    filtered = [lead for lead in filtered 
               if lead.get('total_debt', 0) >= request.min_debt_amount]
    
    # Сортировка по убыванию скора
    filtered.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return filtered

def create_output_csv(leads: List[Dict]) -> str:
    """Создание выходного CSV файла"""
    import pandas as pd
    
    output_data = []
    
    for lead in leads:
        output_data.append({
            'phone': lead.get('phone', ''),
            'fio': lead.get('fio', ''),
            'score': lead.get('score', 0),
            'reason_1': lead.get('reason_1', ''),
            'reason_2': lead.get('reason_2', ''),
            'reason_3': lead.get('reason_3', ''),
            'is_target': 1 if lead.get('is_target', False) else 0,
            'group': lead.get('group', '')
        })
    
    df = pd.DataFrame(output_data)
    output_file = os.path.join(settings.OUTPUT_DIR, "scoring_ready.csv")
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    logger.info(f"Output file created: {output_file} with {len(output_data)} records")
    return output_file

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
    
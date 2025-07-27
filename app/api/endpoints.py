"""
API endpoints for bankruptcy scoring system
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
import uuid
from datetime import datetime

from app.database import get_db
from app.models import Company, ScoringResult, ParsingTask
from app.schemas import (
    CompanyCreate, CompanyResponse, 
    ScoringResultResponse, TaskResponse,
    ScoringRequest, CompanyUpdate
)
from app.core.scoring import BankruptcyScorer
from app.core.enrichment import DataEnricher
from app.utils.validators import validate_csv_format
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Company endpoints
@router.post("/companies/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate, 
    db: Session = Depends(get_db)
):
    """Создание новой компании"""
    try:
        db_company = Company(**company.dict())
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        logger.info(f"Company created: {db_company.inn}")
        return db_company
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/companies/", response_model=List[CompanyResponse])
async def get_companies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Получение списка компаний"""
    companies = db.query(Company).offset(skip).limit(limit).all()
    return companies

@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int, 
    db: Session = Depends(get_db)
):
    """Получение компании по ID"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db)
):
    """Обновление данных компании"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    for field, value in company_update.dict(exclude_unset=True).items():
        setattr(company, field, value)
    
    db.commit()
    db.refresh(company)
    logger.info(f"Company updated: {company.inn}")
    return company

@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: int, 
    db: Session = Depends(get_db)
):
    """Удаление компании"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    db.delete(company)
    db.commit()
    logger.info(f"Company deleted: {company.inn}")
    return {"message": "Company deleted successfully"}

# File upload endpoints
@router.post("/upload/csv/", response_model=TaskResponse)
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузка CSV файла с компаниями"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV format")
    
    try:
        # Чтение CSV файла
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Валидация формата
        if not validate_csv_format(df):
            raise HTTPException(
                status_code=400, 
                detail="Invalid CSV format. Required columns: inn, name"
            )
        
        # Создание задачи
        task_id = str(uuid.uuid4())
        task = ParsingTask(
            id=task_id,
            status="pending",
            created_at=datetime.utcnow(),
            total_companies=len(df)
        )
        db.add(task)
        db.commit()
        
        # Запуск обработки в фоне
        background_tasks.add_task(process_csv_file, df, task_id, db)
        
        logger.info(f"CSV upload started: {file.filename}, companies: {len(df)}")
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"Processing {len(df)} companies"
        )
        
    except Exception as e:
        logger.error(f"Error uploading CSV: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

async def process_csv_file(df: pd.DataFrame, task_id: str, db: Session):
    """Обработка CSV файла в фоновом режиме"""
    try:
        task = db.query(ParsingTask).filter(ParsingTask.id == task_id).first()
        task.status = "processing"
        db.commit()
        
        processed = 0
        for _, row in df.iterrows():
            try:
                # Создание или обновление компании
                existing = db.query(Company).filter(Company.inn == row['inn']).first()
                if existing:
                    existing.name = row.get('name', existing.name)
                    existing.updated_at = datetime.utcnow()
                else:
                    company = Company(
                        inn=row['inn'],
                        name=row.get('name', ''),
                        ogrn=row.get('ogrn', ''),
                        address=row.get('address', ''),
                        created_at=datetime.utcnow()
                    )
                    db.add(company)
                
                processed += 1
                
                # Обновление прогресса
                if processed % 100 == 0:
                    task.processed_companies = processed
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error processing company {row.get('inn', 'unknown')}: {str(e)}")
                continue
        
        task.status = "completed"
        task.processed_companies = processed
        task.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"CSV processing completed: {processed} companies processed")
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        db.commit()
        logger.error(f"CSV processing failed: {str(e)}")

# Scoring endpoints
@router.post("/scoring/run/", response_model=TaskResponse)
async def run_scoring(
    background_tasks: BackgroundTasks,
    request: ScoringRequest,
    db: Session = Depends(get_db)
):
    """Запуск процесса скоринга"""
    try:
        # Получение компаний для скоринга
        query = db.query(Company)
        if request.company_ids:
            query = query.filter(Company.id.in_(request.company_ids))
        companies = query.all()
        
        if not companies:
            raise HTTPException(status_code=404, detail="No companies found for scoring")
        
        # Создание задачи
        task_id = str(uuid.uuid4())
        task = ParsingTask(
            id=task_id,
            status="pending",
            created_at=datetime.utcnow(),
            total_companies=len(companies)
        )
        db.add(task)
        db.commit()
        
        # Запуск скоринга в фоне
        background_tasks.add_task(run_scoring_process, companies, task_id, request.settings, db)
        
        logger.info(f"Scoring started for {len(companies)} companies")
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"Scoring {len(companies)} companies"
        )
        
    except Exception as e:
        logger.error(f"Error starting scoring: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

async def run_scoring_process(companies: List[Company], task_id: str, settings: dict, db: Session):
    """Процесс скоринга в фоновом режиме"""
    try:
        task = db.query(ParsingTask).filter(ParsingTask.id == task_id).first()
        task.status = "processing"
        db.commit()
        
        scorer = BankruptcyScorer()
        enricher = DataEnricher()
        processed = 0
        
        for company in companies:
            try:
                # Обогащение данных
                if settings.get('enrich_data', True):
                    enricher.enrich_company_data(company)
                
                # Скоринг
                score_data = scorer.calculate_score(company)
                
                # Сохранение результата
                result = ScoringResult(
                    company_id=company.id,
                    score=score_data['score'],
                    risk_level=score_data['risk_level'],
                    factors=score_data['factors'],
                    created_at=datetime.utcnow()
                )
                db.add(result)
                
                processed += 1
                
                # Обновление прогресса
                if processed % 10 == 0:
                    task.processed_companies = processed
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error scoring company {company.inn}: {str(e)}")
                continue
        
        task.status = "completed"
        task.processed_companies = processed
        task.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Scoring completed: {processed} companies processed")
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        db.commit()
        logger.error(f"Scoring failed: {str(e)}")

# Results endpoints
@router.get("/results/", response_model=List[ScoringResultResponse])
async def get_scoring_results(
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Получение результатов скоринга"""
    query = db.query(ScoringResult)
    if company_id:
        query = query.filter(ScoringResult.company_id == company_id)
    
    results = query.offset(skip).limit(limit).all()
    return results

@router.get("/results/{result_id}", response_model=ScoringResultResponse)
async def get_scoring_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Получение результата скоринга по ID"""
    result = db.query(ScoringResult).filter(ScoringResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Scoring result not found")
    return result

# Task monitoring endpoints
@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Получение статуса задачи"""
    task = db.query(ParsingTask).filter(ParsingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        task_id=task.id,
        status=task.status,
        processed=task.processed_companies,
        total=task.total_companies,
        error_message=task.error_message
    )

@router.get("/tasks/", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Получение списка задач"""
    tasks = db.query(ParsingTask).order_by(ParsingTask.created_at.desc()).offset(skip).limit(limit).all()
    return [
        TaskResponse(
            task_id=task.id,
            status=task.status,
            processed=task.processed_companies,
            total=task.total_companies,
            error_message=task.error_message
        ) for task in tasks
    ]

# Export endpoints
@router.get("/export/results/csv/")
async def export_results_csv(
    company_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """Экспорт результатов в CSV"""
    try:
        query = db.query(ScoringResult).join(Company)
        if company_ids:
            query = query.filter(Company.id.in_(company_ids))
        
        results = query.all()
        
        # Создание DataFrame
        data = []
        for result in results:
            data.append({
                'company_inn': result.company.inn,
                'company_name': result.company.name,
                'score': result.score,
                'risk_level': result.risk_level,
                'created_at': result.created_at.isoformat()
            })
        
        df = pd.DataFrame(data)
        
        # Создание CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=scoring_results.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@router.get("/health/")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "bankruptcy-scoring-api"
    }

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class ScoringRequest(BaseModel):
    regions: List[str] = Field(..., description="Список регионов для обработки")
    min_debt_amount: int = Field(250000, description="Минимальная сумма долга")
    exclude_bankrupts: bool = Field(True, description="Исключать признанных банкротов")
    exclude_no_debts: bool = Field(True, description="Исключать контакты без долгов")
    only_with_property: bool = Field(False, description="Только с недвижимостью")
    only_bank_mfo_debts: bool = Field(False, description="Только банковские/МФО долги")
    only_recent_court_orders: bool = Field(False, description="Только с судебными приказами за 3 месяца")
    only_active_inn: bool = Field(True, description="Только с живыми ИНН")

class LeadCreate(BaseModel):
    fio: str
    phone: Optional[str] = None
    inn: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    source: str
    tags: Optional[str] = None
    email: Optional[str] = None
    region: Optional[str] = None

    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.startswith('+7'):
            # Попытка нормализации телефона
            v = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if v.startswith('8'):
                v = '+7' + v[1:]
            elif v.startswith('7'):
                v = '+' + v
            elif len(v) == 10:
                v = '+7' + v
        return v

class LeadResponse(BaseModel):
    id: int
    lead_id: str
    fio: str
    phone: Optional[str]
    inn: Optional[str]
    region: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ScoringResultResponse(BaseModel):
    lead_id: str
    fio: str
    phone: str
    score: int
    reason_1: Optional[str]
    reason_2: Optional[str] 
    reason_3: Optional[str]
    is_target: bool
    group: Optional[str]

    class Config:
        from_attributes = True

class DebtInfoResponse(BaseModel):
    debt_amount: float
    debt_type: str
    creditor: str
    case_date: Optional[datetime]
    status: str

    class Config:
        from_attributes = True

class ProcessingStatus(BaseModel):
    status: str  # running, completed, error
    message: str
    progress: Optional[int] = None
    total_leads: Optional[int] = None
    processed_leads: Optional[int] = None
    target_leads: Optional[int] = None
    errors_count: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    source: str
    lead_id: Optional[str]
    message: str
    error_details: Optional[Dict[Any, Any]] = None

class EnrichmentResult(BaseModel):
    lead_id: str
    fssp_success: bool = False
    fedresurs_success: bool = False
    rosreestr_success: bool = False
    courts_success: bool = False
    nalog_success: bool = False
    errors: List[str] = []

class UploadResponse(BaseModel):
    filename: str
    total_records: int
    valid_records: int
    duplicates_removed: int
    errors: List[str] = []

class StatisticsResponse(BaseModel):
    total_leads: int
    processed_leads: int
    target_leads: int
    avg_score: float
    groups_stats: Dict[str, int]
    regions_stats: Dict[str, int]
    debt_types_stats: Dict[str, int]
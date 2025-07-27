from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, unique=True, index=True)
    fio = Column(String, index=True)
    phone = Column(String, index=True)
    inn = Column(String, index=True)
    dob = Column(String)  # дата рождения
    address = Column(Text)
    source = Column(String)  # источник данных
    tags = Column(String)  # теги через запятую
    email = Column(String)
    region = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DebtInfo(Base):
    __tablename__ = "debt_info"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    debt_amount = Column(Float)
    debt_type = Column(String)  # банк, МФО, налоги, ЖКХ
    creditor = Column(String)  # взыскатель
    case_date = Column(DateTime)
    status = Column(String)
    fssp_data = Column(JSON)  # сырые данные ФССП
    created_at = Column(DateTime, default=datetime.utcnow)

class PropertyInfo(Base):
    __tablename__ = "property_info"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    has_property = Column(Boolean, default=False)
    property_type = Column(String)  # квартира, дом, участок
    property_details = Column(JSON)
    rosreestr_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class CourtInfo(Base):
    __tablename__ = "court_info"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    has_court_order = Column(Boolean, default=False)
    court_date = Column(DateTime)
    court_type = Column(String)  # мировой, районный
    case_number = Column(String)
    court_details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class BankruptcyInfo(Base):
    __tablename__ = "bankruptcy_info"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    is_bankrupt = Column(Boolean, default=False)
    bankruptcy_status = Column(String)
    procedure_date = Column(DateTime)
    fedresurs_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class TaxInfo(Base):
    __tablename__ = "tax_info"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    inn_active = Column(Boolean, default=True)
    tax_debt = Column(Float)
    tax_status = Column(String)
    nalog_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScoringResult(Base):
    __tablename__ = "scoring_results"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    score = Column(Integer)
    is_target = Column(Boolean, default=False)
    reason_1 = Column(String)
    reason_2 = Column(String)
    reason_3 = Column(String)
    group = Column(String)  # для A/B тестов
    scoring_date = Column(DateTime, default=datetime.utcnow)
    filters_applied = Column(JSON)  # какие фильтры применялись
    
class ScoringHistory(Base):
    __tablename__ = "scoring_history"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    score = Column(Integer)
    group = Column(String)
    reason_1 = Column(String)
    scoring_date = Column(DateTime, default=datetime.utcnow)
    
class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, index=True)
    source = Column(String)  # ФССП, Федресурс и т.д.
    status = Column(String)  # success, error, skip
    error_message = Column(Text)
    response_data = Column(JSON)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
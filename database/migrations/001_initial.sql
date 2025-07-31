-- Создание таблицы лидов
CREATE TABLE IF NOT EXISTS leads (
    lead_id SERIAL PRIMARY KEY,
    fio VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    inn VARCHAR(12),
    dob DATE,
    address TEXT,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags VARCHAR(50),
    email VARCHAR(100)
);

-- Создание таблицы истории скоринга
CREATE TABLE IF NOT EXISTS scoring_history (
    history_id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(lead_id),
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INTEGER NOT NULL,
    group_name VARCHAR(50) NOT NULL,
    reason_1 TEXT,
    reason_2 TEXT,
    reason_3 TEXT
);

-- Создание таблицы ошибок
CREATE TABLE IF NOT EXISTS error_logs (
    error_id SERIAL PRIMARY KEY,
    fio VARCHAR(255),
    inn VARCHAR(12),
    error TEXT NOT NULL,
    service VARCHAR(50) NOT NULL,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для ускорения запросов
CREATE INDEX idx_leads_phone ON leads(phone);
CREATE INDEX idx_leads_inn ON leads(inn);
CREATE INDEX idx_history_lead ON scoring_history(lead_id);
CREATE INDEX idx_history_scored_at ON scoring_history(scored_at);
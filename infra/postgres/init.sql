-- Sepsis Early-Warning CDSS Database Initialization
-- ===================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── ROLE ──
CREATE TABLE IF NOT EXISTS role (
    role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE
);

-- ── USER ──
CREATE TABLE IF NOT EXISTS "user" (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id UUID NOT NULL REFERENCES role(role_id),
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- ── PATIENT ──
CREATE TABLE IF NOT EXISTS patient (
    patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_ref VARCHAR(100),
    name VARCHAR(200),
    age INTEGER,
    gender VARCHAR(10)
);

-- ── ICU STAY ──
CREATE TABLE IF NOT EXISTS icu_stay (
    stay_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patient(patient_id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'RUNNING',
    source_record VARCHAR(100)
);

-- ── MODEL VERSION ──
CREATE TABLE IF NOT EXISTS model_version (
    model_version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    artifact_uri VARCHAR(500),
    metrics_json JSONB,
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- ── SEPSIS PREDICTION ──
CREATE TABLE IF NOT EXISTS sepsis_prediction (
    pred_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stay_id UUID NOT NULL REFERENCES icu_stay(stay_id),
    model_version_id UUID REFERENCES model_version(model_version_id),
    hour INTEGER NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_level VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── ALERT ──
CREATE TABLE IF NOT EXISTS alert (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stay_id UUID NOT NULL REFERENCES icu_stay(stay_id),
    model_version_id UUID REFERENCES model_version(model_version_id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    severity DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'NEW',
    evidence_json JSONB
);

-- ── ALERT ACTION ──
CREATE TABLE IF NOT EXISTS alert_action (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID NOT NULL REFERENCES alert(alert_id),
    user_id UUID NOT NULL REFERENCES "user"(user_id),
    action_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action_type VARCHAR(20) NOT NULL,
    reason TEXT,
    note TEXT
);

-- ── SYSTEM SETTING ──
CREATE TABLE IF NOT EXISTS system_setting (
    setting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) NOT NULL UNIQUE,
    current_value_json JSONB
);

-- ── SETTING VERSION ──
CREATE TABLE IF NOT EXISTS setting_version (
    setting_version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_id UUID NOT NULL REFERENCES system_setting(setting_id),
    changed_by UUID REFERENCES "user"(user_id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    value_json JSONB
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sepsis_pred_stay ON sepsis_prediction(stay_id);
CREATE INDEX IF NOT EXISTS idx_sepsis_pred_hour ON sepsis_prediction(hour);
CREATE INDEX IF NOT EXISTS idx_alert_stay ON alert(stay_id);
CREATE INDEX IF NOT EXISTS idx_alert_status ON alert(status);
CREATE INDEX IF NOT EXISTS idx_alert_action_alert ON alert_action(alert_id);

-- ===================================
-- SEED DATA
-- ===================================

-- Roles
INSERT INTO role (role_id, name) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'admin'),
    ('a0000000-0000-0000-0000-000000000002', 'clinician')
ON CONFLICT (name) DO NOTHING;

-- Admin user (password: admin123) - bcrypt hash
INSERT INTO "user" (user_id, role_id, username, password_hash, display_name) VALUES
    ('b0000000-0000-0000-0000-000000000001',
     'a0000000-0000-0000-0000-000000000001',
     'admin',
     '$2b$12$hf7IZRUH92KCLZyTHtwCk.y9dx7XlDRXgVsRHcKouJ6VYE4K5oiSC',
     'Administrator')
ON CONFLICT (username) DO NOTHING;

-- Demo clinician (password: doctor123)
INSERT INTO "user" (user_id, role_id, username, password_hash, display_name) VALUES
    ('b0000000-0000-0000-0000-000000000002',
     'a0000000-0000-0000-0000-000000000002',
     'doctor',
     '$2b$12$9xx/34mlqn0XvRWRoV0Cgeuy8uQpfbRp.Mi./y7QalrEIuq3CUPtK',
     'Dr. Demo')
ON CONFLICT (username) DO NOTHING;

-- Model version
INSERT INTO model_version (model_version_id, name, artifact_uri, is_active) VALUES
    ('c0000000-0000-0000-0000-000000000001',
     'sepsis_v1',
     'artifacts/sepsis_model.json',
     TRUE)
ON CONFLICT DO NOTHING;

-- Demo patient
INSERT INTO patient (patient_id, external_ref, name, age, gender) VALUES
    ('e0000000-0000-0000-0000-000000000001', 'MIMIC-DEMO-001', 'Demo Patient', 65, 'M')
ON CONFLICT DO NOTHING;

-- System settings
INSERT INTO system_setting (key, current_value_json) VALUES
    ('alert_risk_threshold', '0.6'),
    ('sustained_hours', '3'),
    ('cooldown_hours', '12'),
    ('hour_interval_sec', '1.0')
ON CONFLICT (key) DO NOTHING;

-- ===================================
-- AIRFLOW METADATA DATABASE
-- ===================================

-- Create airflow database for Airflow metadata store
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

\c airflow
GRANT ALL PRIVILEGES ON DATABASE airflow TO sepsis_admin;

-- ECG CDSS Database Initialization
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
    display_name VARCHAR(200)
);

-- ── SESSION ──
CREATE TABLE IF NOT EXISTS session (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES patient(patient_id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    source_type VARCHAR(50) DEFAULT 'replay',
    status VARCHAR(20) DEFAULT 'RUNNING',
    record_name VARCHAR(100)
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

-- ── PREDICTION BEAT ──
CREATE TABLE IF NOT EXISTS prediction_beat (
    pred_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES session(session_id),
    model_version_id UUID REFERENCES model_version(model_version_id),
    beat_ts_sec DOUBLE PRECISION NOT NULL,
    pred_class VARCHAR(5) NOT NULL,
    confidence DOUBLE PRECISION,
    p_a DOUBLE PRECISION,
    probs_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── ALERT ──
CREATE TABLE IF NOT EXISTS alert (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES session(session_id),
    model_version_id UUID REFERENCES model_version(model_version_id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    alert_type VARCHAR(5) NOT NULL,
    status VARCHAR(20) DEFAULT 'NEW',
    severity DOUBLE PRECISION DEFAULT 0.0,
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
CREATE INDEX IF NOT EXISTS idx_prediction_beat_session ON prediction_beat(session_id);
CREATE INDEX IF NOT EXISTS idx_prediction_beat_ts ON prediction_beat(beat_ts_sec);
CREATE INDEX IF NOT EXISTS idx_alert_session ON alert(session_id);
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
     'mitbih_v25',
     'artifacts/best_mitbih_v25.pt',
     TRUE)
ON CONFLICT DO NOTHING;

-- Demo patient
INSERT INTO patient (patient_id, external_ref, display_name) VALUES
    ('d0000000-0000-0000-0000-000000000001', 'MIT-BIH-223', 'Demo Patient (Record 223)')
ON CONFLICT DO NOTHING;

-- System settings
INSERT INTO system_setting (key, current_value_json) VALUES
    ('thr_A', '0.65'),
    ('V_WINDOW', '10'),
    ('V_THRESH', '5'),
    ('COOLDOWN_V', '20'),
    ('A_WINDOW', '30'),
    ('A_THRESH', '4'),
    ('COOLDOWN_A', '45'),
    ('STREAM_CHUNK_SEC', '1.0'),
    ('REALTIME_SPEED', '1.0')
ON CONFLICT (key) DO NOTHING;

-- ===================================
-- AIRFLOW METADATA DATABASE
-- ===================================

-- Create airflow database for Airflow metadata store
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

\c airflow
GRANT ALL PRIVILEGES ON DATABASE airflow TO ecg_admin;

# Architecture — Sepsis Early-Warning CDSS

## 1. System Overview

The Sepsis Early-Warning CDSS is a microservices-based clinical decision support system that:
1. Ingests ICU patient vital signs hour by hour (PhysioNet/CinC Challenge 2019 dataset)
2. Engineers time-series features (forward-fill, rolling 6h statistics, recency)
3. Runs hourly XGBoost inference to estimate sepsis risk
4. Applies clinical alert rules with a risk threshold, sustained-hours requirement, and cooldown
5. Delivers real-time risk scores, trajectories, and alerts to a React dashboard
6. Reproduces model training/evaluation through DVC + Airflow and tracks experiments/models in MLflow

## 2. Architecture Diagram

```
┌──────────────────┐   patient_vitals   ┌─────────────────────┐  patient_features  ┌──────────────┐
│ Replay Producer  │───────────────────►│ Preprocess Buffer   │──────────────────► │              │
│ / push_patient   │                    │ Service             │                    │   FastAPI    │
│ (PhysioNet .psv) │                    │ (feature engineer)  │                    │   Backend    │
└──────────────────┘                    └─────────────────────┘                    │              │
                                                                                   │  REST + WS   │◄──► React Frontend
                                         ┌─────────────────────┐ sepsis_prediction │              │
                                         │ Inference Service   │──────────────────►│              │
                                         │ (XGBoost)           │                    │              │
                                         └─────────────────────┘                    └──────┬───────┘
                                              ▲                                            │
                                              │ patient_features                           │
                                              │                                            ▼
                                         ┌─────────────────────┐   sepsis_alert     ┌──────────────┐
                                         │ Alert Engine        │──────────────────► │  PostgreSQL  │
                                         │ Service             │                    └──────────────┘
                                         └─────────────────────┘
                                              ▲
                                              │ sepsis_prediction
```

All inter-service communication flows through **Apache Kafka**. State is persisted in **PostgreSQL**.
Offline model operations use **DVC** + **Airflow** for pipeline reproducibility and **MLflow** for
experiment tracking, the model registry, and artifacts.

## 3. Kafka Topics

| Topic | Producer | Consumer(s) | Description |
|-------|----------|-------------|-------------|
| `patient_vitals` | Replay Producer / Backend | Preprocess Buffer | Raw hourly vital signs for an ICU stay |
| `patient_features` | Preprocess Buffer | Inference Service | Engineered 114-feature vectors |
| `sepsis_prediction` | Inference Service | Alert Engine, Backend | Hourly sepsis risk score + risk level |
| `sepsis_alert` | Alert Engine | Backend (WS) | Sepsis alert events |

## 4. Services

### 4.1 Replay Producer
- Reads PhysioNet/CinC 2019 `.psv` files (1 row = 1 ICU hour, 41 columns)
- Creates patient + ICU stay rows, then publishes hourly vitals to `patient_vitals`
- Simulates real-time playback speed

### 4.2 Preprocess Buffer Service
- Maintains per-stay history of incoming hourly vitals
- Engineers 114 features: forward-filled signals + rolling 6h statistics + recency indicators
- Publishes feature vectors to `patient_features`

### 4.3 Inference Service
- Loads the XGBoost model (`sepsis_model.json`, 114 features)
- Runs per-hour inference → sepsis risk score (0–1) and risk level (LOW/MEDIUM/HIGH)
- Publishes predictions to `sepsis_prediction`

### 4.4 Alert Engine Service
- Per-stay sliding-window alert rules
- Raises an alert when risk ≥ `ALERT_RISK_THRESHOLD` (0.6) for `SUSTAINED_HOURS` (3) consecutive hours
- Enforces `COOLDOWN_HOURS` (12) between alerts to prevent alert fatigue
- Persists alerts to PostgreSQL

### 4.5 FastAPI Backend
- REST API: auth (JWT), CRUD for patients/stays/alerts/users/settings
- WebSocket gateway: consumes Kafka topics, broadcasts to clients by stay
- Analytics and MLOps proxy endpoints (MLflow experiments/registry, Airflow pipeline status)

### 4.6 React Frontend
- Ant Design components + ECharts for risk gauge and trajectory
- Triage board, patient monitor, patient/stay management, alerts, analytics
- MLOps dashboard (experiments, model registry, retraining pipeline status)

### 4.7 MLOps Pipeline
- `params.yaml` stores reproducible data split, training, evaluation, and tracking parameters
- `dvc.yaml` defines `prepare_data → train → evaluate → compare_and_register`
- Airflow DAG `sepsis_daily_retrain` runs the same stages daily
- MLflow records run parameters, metrics, checkpoints, and the model registry (`sepsis-xgb-earlywarning`)
- `compare_and_register` gates promotion by `min_auroc` and copies the serving model into
  `services/inference-service/artifacts/`

## 5. Service Ports (host)

| Service | Host port | Container port |
|---------|-----------|----------------|
| Frontend | 13000 | 3000 |
| Backend (FastAPI) | 18800 | 8000 |
| MLflow | 15000 | 5000 |
| Airflow webserver | 18080 | 8080 |
| PostgreSQL | 15432 | 5432 |
| Kafka | 9092 | 9092 |

## 6. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Ant Design, ECharts, TanStack Query, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, JWT |
| Services | Python 3.11, XGBoost, pandas, NumPy, confluent-kafka |
| Database | PostgreSQL |
| Messaging | Apache Kafka |
| MLOps | DVC, MLflow, Apache Airflow |
| Infra | Docker, Docker Compose |

## 7. Security

- JWT-based authentication with bcrypt password hashing
- Role-based access control; admin-only endpoints for user management
- An admin cannot deactivate or delete their own account; only admins can manage other accounts
- CORS configured for the frontend origin

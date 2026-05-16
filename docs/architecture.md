# Architecture — ECG Real-time CDSS

## 1. System Overview

The ECG Real-time CDSS is a microservices-based system that:
1. Replays MIT-BIH ECG recordings as a real-time stream
2. Processes and buffers the signal for UI display
3. Runs beat-level PyTorch inference for arrhythmia classification (N/A/V)
4. Applies clinical alert rules with thresholds and cooldown
5. Delivers real-time waveform + predictions + alerts via WebSocket to a React dashboard
6. Reproduces model training/evaluation through DVC and tracks experiments through MLflow

## 2. Architecture Diagram

```
┌─────────────────┐     ecg_raw        ┌─────────────────────┐    ecg_waveform     ┌──────────────┐
│ Replay Producer │───────────────────►│ Preprocess Buffer   │──────────────────►  │              │
│ (MIT-BIH WFDB)  │     ecg_beat_event │ Service             │    ecg_beat_ready   │   FastAPI    │
│                  │───────────────────►│                     │──────────────────►  │   Backend    │
└─────────────────┘                    └─────────────────────┘                     │              │
                                                                                   │  REST + WS   │◄───► React Frontend
                                        ┌─────────────────────┐    ecg_pred_beat   │              │
                                        │ Inference Service    │──────────────────►│              │
                                        │ (PyTorch CNN)        │                    │              │
                                        └─────────────────────┘                    └──────┬───────┘
                                              ▲                                           │
                                              │ ecg_beat_ready                            │
                                              │                                           ▼
                                        ┌─────────────────────┐    ecg_alert       ┌──────────────┐
                                        │ Alert Engine         │──────────────────►│  PostgreSQL   │
                                        │ Service              │                    └──────────────┘
                                        └─────────────────────┘
                                              ▲
                                              │ ecg_pred_beat
```

All inter-service communication flows through **Apache Kafka**. State is persisted in **PostgreSQL**.
Offline model operations use **DVC** for pipeline reproducibility and **MLflow** for experiment tracking/artifacts.

## 3. Kafka Topics

| Topic | Producer | Consumer(s) | Description |
|-------|----------|-------------|-------------|
| `ecg_raw` | Replay Producer | Preprocess Buffer | Raw waveform chunks (1s) |
| `ecg_beat_event` | Replay Producer | Preprocess Buffer | Beat-level segments + features |
| `ecg_waveform` | Preprocess Buffer | Backend (WS) | Processed waveform for UI |
| `ecg_beat_ready` | Preprocess Buffer | Inference Service | Normalized beat events |
| `ecg_pred_beat` | Inference Service | Alert Engine, Backend | Per-beat predictions |
| `ecg_alert` | Alert Engine | Backend (WS) | Alert events |

## 4. Services

### 4.1 Replay Producer
- Reads WFDB records using `wfdb` library
- Publishes raw waveform in 1-second chunks
- Extracts beats from annotations, computes bandpass/zscore segments, RR4, M8 features
- Simulates real-time playback speed

### 4.2 Preprocess Buffer Service
- Ring buffer maintains last 10 seconds of waveform
- Downsamples for UI rendering
- Computes Signal Quality Index (SQI)
- Passes through beat events for inference

### 4.3 Inference Service
- Loads `CNN_RR4_Morph8` model from checkpoint
- Runs forward pass: segment (C,L) + RR4 (4,) + M8 (8,) → logits → softmax
- A-threshold gating: if pred=A and pA < thr_A → reclassify as N
- Publishes prediction with class, confidence, probabilities

### 4.4 Alert Engine Service
- Sliding window alert rules per session
- V alert: ≥ V_THRESH V-beats in V_WINDOW seconds, with COOLDOWN_V
- A alert: ≥ A_THRESH A-beats (pA ≥ thr_A) in A_WINDOW seconds, with COOLDOWN_A
- Persists alerts to PostgreSQL

### 4.5 FastAPI Backend
- REST API: auth (JWT), CRUD for sessions/alerts/users/settings
- WebSocket gateway: consumes Kafka topics, broadcasts to clients by session_id
- Analytics endpoints for alerts/hour and summary statistics

### 4.6 React Frontend
- Ant Design components + ECharts waveform rendering
- Real-time WebSocket updates for waveform, predictions, alerts
- Alert workflow: ACK/DISMISS with reason/note
- Admin: user management, system settings with audit log

### 4.7 MLOps Pipeline
- `params.yaml` stores reproducible data split, training, evaluation, and tracking parameters
- `dvc.yaml` defines prepare_data → train → evaluate → promote_model stages
- MLflow records run parameters, validation/test metrics, checkpoints, and evaluation artifacts
- Promotion copies a gated checkpoint into `services/inference-service/artifacts/` with a manifest
- Inference can serve either the promoted local checkpoint or a tracked MLflow artifact URI

## 5. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Ant Design, ECharts, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT |
| Services | Python 3.11, PyTorch, WFDB, NumPy, SciPy, confluent-kafka |
| Database | PostgreSQL 15 |
| Messaging | Apache Kafka 3.6 |
| MLOps | DVC, MLflow |
| Infra | Docker, Docker Compose |

## 6. Security

- JWT-based authentication with bcrypt password hashing
- Role-based access control (Admin, Clinician)
- CORS configured for frontend origin
- All admin endpoints require Admin role

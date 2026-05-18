# Runbook — Sepsis Early-Warning CDSS

## Prerequisites

- Docker & Docker Compose installed
- PhysioNet/CinC Challenge 2019 dataset under `Data/sepsis-2019/training_setA` and `training_setB`
- A serving model `services/inference-service/artifacts/sepsis_model.json`, or run the MLOps
  pipeline to create one

## Setup

### 1. Configure

```bash
cd CNM-Final-Project
cp .env.example .env
# Edit .env if needed (default values work for local dev)
```

### 2. Place Data Files

Copy the PhysioNet/CinC 2019 dataset so the layout is:

```text
Data/sepsis-2019/training_setA/p000001.psv
Data/sepsis-2019/training_setB/p100001.psv
...
```

To train and promote a model locally, see `docs/mlops.md`.

### 3. Build & Start

```bash
docker compose up -d
```

Core services: `postgres`, `kafka`, `mlflow`, `backend`, `frontend`,
`preprocess-buffer`, `inference-service`, `alert-engine`.
MLOps services: `airflow-init` (one-shot), `airflow-webserver`, `airflow-scheduler`.
`replay-producer` is optional — start it only if you want auto-streamed demo patients.

### 4. Endpoints

| UI | URL | Credentials |
|----|-----|-------------|
| Web app | http://localhost:13000 | admin / admin123 |
| MLflow | http://localhost:15000 | — |
| Airflow | http://localhost:18080 | admin / admin123 |
| Backend API | http://localhost:18800 | JWT |

## Demo Flow

### Step 1: Login
Open http://localhost:13000 → log in with `admin` / `admin123`.

### Step 2: Stream a patient

Use a test-set record (the model never trained on it — honest demo):

```bash
python tools/push_patient.py \
  --patient-name "Demo Test Patient" \
  --psv "data/splits/test/p017347.psv" \
  --interval 5 --stop
```

The script logs in, creates a patient + ICU stay, and pushes hourly vitals.

### Step 3: Watch real-time
- **Triage Board** (`/overview`) — risk per stay, refreshes every 5s
- **Patient Monitor** (`/live`) — risk gauge, sepsis risk trajectory, vital signs, alerts
- **ICU Stays** (`/stays`) — stay list; **Stop** ends a stay
- **Sepsis Alerts** (`/alerts`) — alerts raised when risk stays above threshold
- **Analytics** (`/analytics`) — aggregate statistics

### Step 4: Patient management
**Patients** → open a patient → **+ New ICU Stay** to add another monitoring session.

### Step 5: MLOps
- **MLOps → Dashboard / Experiments / Model Registry** in the web app
- MLflow UI: http://localhost:15000
- Airflow UI: http://localhost:18080 — DAG `sepsis_daily_retrain`

## Troubleshooting

### Kafka not ready
Services may restart a few times while Kafka initializes. This is normal.
The `Unknown topic or partition` log on first start is harmless — topics are auto-created
on first publish.

### No predictions / no risk on the monitor
- Check the serving model exists: `services/inference-service/artifacts/sepsis_model.json`
- Check inference-service logs: `docker compose logs inference-service`

### Airflow task logs show 403
Webserver and scheduler must share `AIRFLOW__WEBSERVER__SECRET_KEY` (set in docker-compose).

### Out of memory during training
Training is memory-heavy. Free RAM by stopping non-essential containers, or reduce
`n_workers` in `prepare_data`.

### Database issues
Reset everything (drops DB, MLflow, and Airflow volumes):
```bash
docker compose down -v
docker compose up -d
```

## Stopping

```bash
docker compose stop                       # stop containers
docker compose stop airflow-webserver airflow-scheduler   # stop only Airflow (save RAM)
docker compose down                       # stop & remove containers
docker compose down -v                    # also remove volumes (reset all data)
```

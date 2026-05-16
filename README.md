# ECG Real-time Clinical Decision Support System (CDSS)

Real-time AI-powered arrhythmia detection from ECG signals using MIT-BIH Arrhythmia Database, with an MLOps workflow for dataset preparation, training, experiment tracking, evaluation, and model promotion.

## Architecture

```
MIT-BIH Files → Replay Producer → Kafka → Preprocess Buffer → Inference (PyTorch) → Alert Engine → FastAPI (WS) → React UI
```

Offline MLOps workflow:

```
MIT-BIH Files → DVC Prepare Data → Train CNN → MLflow Tracking → Evaluate → Promote Checkpoint → Inference Service
```

## Quick Start

```bash
# 1. Copy your model checkpoint, or build one with the MLOps workflow below
cp best_mitbih_v25.pt services/inference-service/artifacts/

# 2. Copy MIT-BIH data (e.g., record 223)
cp 223.dat 223.hea 223.atr services/replay-producer/data/

# 3. Copy .env
cp .env.example .env

# 4. Start everything
docker compose up --build
```

Open http://localhost:3000 → Login with `admin` / `admin123`

## MLOps Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e mlops

docker compose up -d mlflow
export MLFLOW_TRACKING_URI=http://localhost:5000
dvc repro
```

MLflow UI: http://localhost:5000

The DVC pipeline writes a promoted checkpoint to `services/inference-service/artifacts/best_mitbih_v25.pt`.

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React + Vite + Ant Design |
| Backend | 8000 | FastAPI REST + WebSocket |
| Kafka | 9092 | Message broker |
| Postgres | 5432 | Database |
| MLflow | 5000 | Experiment tracking and model artifacts |
| Replay Producer | — | MIT-BIH ECG stream simulator |
| Preprocess Buffer | — | Waveform processing |
| Inference Service | — | PyTorch CNN inference |
| Alert Engine | — | Clinical alert rules |

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Runbook](docs/runbook.md)
- [MLOps Workflow](docs/mlops.md)
- Diagrams: `docs/diagrams/` (use case, ERD, class)

## Tech Stack

- **Frontend**: React, TypeScript, Vite, Ant Design, ECharts, TanStack Query
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, JWT Auth
- **MLOps**: DVC, MLflow, PyTorch, scikit-learn
- **Services**: Python, PyTorch, WFDB, NumPy, SciPy
- **Infra**: Docker Compose, Kafka, PostgreSQL

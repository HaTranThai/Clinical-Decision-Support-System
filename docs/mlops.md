# MLOps Workflow

This project now separates online serving from offline model operations.

## Flow

```text
MIT-BIH WFDB files
 -> DVC prepare_data
 -> DVC train
 -> MLflow experiment tracking
 -> DVC evaluate
 -> gated promote_model
 -> inference-service/artifacts/best_mitbih_v25.pt
 -> realtime serving pipeline
```

## Local Setup

```bash
cd /home/bbsw/DP/CNM-Final-Project
python -m venv .venv
source .venv/bin/activate
pip install -e mlops
```

Copy MIT-BIH records into `services/replay-producer/data`, for example:

```text
services/replay-producer/data/223.dat
services/replay-producer/data/223.hea
services/replay-producer/data/223.atr
```

Start MLflow tracking:

```bash
docker compose up -d mlflow
```

Open `http://localhost:5000`.

## Reproduce The Pipeline

```bash
export MLFLOW_TRACKING_URI=http://localhost:5000
dvc repro
```

The promoted serving checkpoint is written to:

```text
services/inference-service/artifacts/best_mitbih_v25.pt
```

The promotion stage is gated by `--min-f1` in `dvc.yaml`.

## Serving With A Tracked Artifact

The inference service still supports the legacy local checkpoint:

```bash
MODEL_CHECKPOINT=artifacts/best_mitbih_v25.pt
```

It also supports MLflow artifact URIs:

```bash
MODEL_URI=runs:/<run_id>/model/best_mitbih_mlops.pt
MLFLOW_TRACKING_URI=http://mlflow:5000
```

When `MODEL_URI` is set, it takes precedence over `MODEL_CHECKPOINT`.

## What Is Versioned

- `params.yaml`: reproducible training configuration.
- `dvc.yaml`: data, training, evaluation, and promotion DAG.
- MLflow: parameters, metrics, checkpoints, and evaluation artifacts.
- `services/inference-service/artifacts/model_manifest.json`: latest promotion metadata.

Raw WFDB files, processed arrays, checkpoints, and MLflow run directories are intentionally ignored by Git.

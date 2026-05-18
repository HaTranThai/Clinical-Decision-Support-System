# MLOps Workflow

This project separates online serving from offline model operations. The same pipeline
can be run manually (DVC) or on a schedule (Airflow).

## Flow

```text
PhysioNet/CinC 2019 .psv files
 -> prepare_data        (engineer features, patient-level train/val/test split)
 -> train               (XGBoost challenger, logged to MLflow)
 -> evaluate            (metrics on the holdout test set)
 -> compare_and_register (gate by min_auroc, register + promote in MLflow Model Registry)
 -> services/inference-service/artifacts/sepsis_model.json
 -> realtime serving pipeline
```

## Data Split

The split is **patient-level** (each `.psv` file goes entirely into one of train/val/test),
stratified by septic flag, and deterministic (`random_seed` in `params.yaml`).
Ratios default to 70 / 15 / 15. This prevents leakage between hours of the same patient.

`tools/organize_splits.py` mirrors the split into `data/splits/{train,val,test}/` as symlinks
so demo records can be picked from the test set (model never trained on them).

## Local Setup

```bash
cd /home/bbsw/DP/CNM-Final-Project
python -m venv .venv
source .venv/bin/activate
pip install -e mlops
```

Place the PhysioNet/CinC 2019 dataset under `Data/sepsis-2019/training_setA` and
`Data/sepsis-2019/training_setB`.

## Reproduce The Pipeline — DVC

```bash
docker compose up -d mlflow
export MLFLOW_TRACKING_URI=http://localhost:15000
dvc repro
```

`dvc.yaml` stages: `prepare_data → train → evaluate → compare_and_register`.

## Reproduce The Pipeline — Airflow

The DAG `sepsis_daily_retrain` runs the same stages daily at 02:00. Each stage runs
as an isolated subprocess (`python -m sepsis_mlops.<module>`).

- Airflow UI: http://localhost:18080 (admin / admin123)
- Trigger manually: `docker compose exec airflow-scheduler airflow dags trigger sepsis_daily_retrain`

## Model Registry & Promotion

- Registered model name: `sepsis-xgb-earlywarning`
- `compare_and_register` registers the trained challenger as a new version
- Promotion to Production requires `auroc >= min_auroc` (params.yaml) and a better AUROC than the
  current champion; otherwise the version is archived
- On promotion, the serving model is copied to
  `services/inference-service/artifacts/sepsis_model.json` with a `model_manifest.json`

## Serving With A Tracked Artifact

The inference service serves the local checkpoint by default:

```bash
MODEL_CHECKPOINT=artifacts/sepsis_model.json
```

It also supports MLflow artifact URIs (`runs:/`, `models:/`, `mlflow-artifacts:/`):

```bash
MODEL_URI=runs:/<run_id>/model
MLFLOW_TRACKING_URI=http://mlflow:5000
```

When `MODEL_URI` is set, it takes precedence over `MODEL_CHECKPOINT`.

## What Is Versioned

- `params.yaml`: reproducible training configuration
- `dvc.yaml`: data, training, evaluation, and registration DAG
- MLflow: parameters, metrics, checkpoints, and the model registry
- `services/inference-service/artifacts/model_manifest.json`: latest promotion metadata

Raw `.psv` files, processed parquet, checkpoints, and MLflow run directories are ignored by Git.

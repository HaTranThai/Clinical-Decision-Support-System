"""Daily ECG model retraining DAG.

Pipeline: validate_data → prepare_features → train_challenger → evaluate_challenger → compare_and_register

Runs at 2:00 AM daily. Uses PythonOperator to invoke each ecg_mlops module's
main() function directly, with working directory set to APP_ROOT so that
relative paths in params.yaml resolve correctly.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# ---------------------------------------------------------------------------
# Path setup — must happen at module import time so Airflow can resolve imports
# ---------------------------------------------------------------------------
APP_ROOT = Path("/app")
MLOPS_SRC = str(APP_ROOT / "mlops" / "src")
REPLAY_SRC = str(APP_ROOT / "services" / "replay-producer" / "src")
INFERENCE_SRC = str(APP_ROOT / "services" / "inference-service" / "src")

for _p in [MLOPS_SRC, REPLAY_SRC, INFERENCE_SRC]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

PARAMS_PATH = str(APP_ROOT / "params.yaml")
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

# ---------------------------------------------------------------------------
# DAG default args
# ---------------------------------------------------------------------------
default_args = {
    "owner": "ecg-cdss",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


# ---------------------------------------------------------------------------
# Task callables
# ---------------------------------------------------------------------------

def validate_data_fn(**ctx) -> None:
    """Check that all configured MIT-BIH record files exist before processing."""
    import yaml

    params = yaml.safe_load((APP_ROOT / "params.yaml").read_text(encoding="utf-8"))
    raw_dir = APP_ROOT / params["data"]["raw_dir"]
    split = params["data"]["split"]
    all_records = (
        split["train_records"]
        + split["val_records"]
        + split["test_records"]
    )

    missing: list[str] = []
    for rec in all_records:
        for ext in [".dat", ".hea", ".atr"]:
            f = raw_dir / f"{rec}{ext}"
            if not f.exists():
                missing.append(str(f))

    if missing:
        raise FileNotFoundError(
            f"Missing {len(missing)} MIT-BIH file(s). First 5: {missing[:5]}"
        )

    logging.info(f"All {len(all_records)} records validated OK in {raw_dir}")


def prepare_data_fn(**ctx) -> None:
    """Build patient-level split train/val/test npz files."""
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_URI)
    os.chdir(APP_ROOT)

    from ecg_mlops.prepare_data import main as prepare_main

    old_argv = sys.argv
    sys.argv = ["prepare_data", "--params", PARAMS_PATH]
    try:
        prepare_main()
    finally:
        sys.argv = old_argv


def train_fn(**ctx) -> None:
    """Train challenger model on train.npz, validate on val.npz."""
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_URI)
    os.chdir(APP_ROOT)

    from ecg_mlops.train import main as train_main

    old_argv = sys.argv
    sys.argv = [
        "train",
        "--params", PARAMS_PATH,
        "--train-data", str(APP_ROOT / "data" / "processed" / "train.npz"),
        "--val-data", str(APP_ROOT / "data" / "processed" / "val.npz"),
        "--output", str(APP_ROOT / "artifacts" / "model" / "challenger.pt"),
    ]
    try:
        train_main()
    finally:
        sys.argv = old_argv


def evaluate_fn(**ctx) -> None:
    """Evaluate challenger on the fixed holdout test.npz."""
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_URI)
    os.chdir(APP_ROOT)

    from ecg_mlops.evaluate import main as eval_main

    old_argv = sys.argv
    sys.argv = [
        "evaluate",
        "--params", PARAMS_PATH,
        "--test-data", str(APP_ROOT / "data" / "processed" / "test.npz"),
        "--checkpoint", str(APP_ROOT / "artifacts" / "model" / "challenger.pt"),
        "--output", str(APP_ROOT / "artifacts" / "evaluation" / "metrics.json"),
    ]
    try:
        eval_main()
    finally:
        sys.argv = old_argv


def compare_and_register_fn(**ctx) -> None:
    """Compare challenger vs Production champion; promote if challenger wins."""
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_URI)
    os.chdir(APP_ROOT)

    from ecg_mlops.compare_and_register import main as compare_main

    old_argv = sys.argv
    sys.argv = [
        "compare_and_register",
        "--params", PARAMS_PATH,
        "--checkpoint", str(APP_ROOT / "artifacts" / "model" / "challenger.pt"),
        "--metrics", str(APP_ROOT / "artifacts" / "evaluation" / "metrics.json"),
    ]
    try:
        compare_main()
    finally:
        sys.argv = old_argv


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="ecg_daily_retrain",
    default_args=default_args,
    description="Daily ECG arrhythmia model retraining pipeline",
    schedule_interval="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["ecg", "mlops", "retraining"],
) as dag:

    t_validate = PythonOperator(
        task_id="validate_data",
        python_callable=validate_data_fn,
    )
    t_prepare = PythonOperator(
        task_id="prepare_features",
        python_callable=prepare_data_fn,
    )
    t_train = PythonOperator(
        task_id="train_challenger",
        python_callable=train_fn,
    )
    t_evaluate = PythonOperator(
        task_id="evaluate_challenger",
        python_callable=evaluate_fn,
    )
    t_compare = PythonOperator(
        task_id="compare_and_register",
        python_callable=compare_and_register_fn,
    )

    t_validate >> t_prepare >> t_train >> t_evaluate >> t_compare

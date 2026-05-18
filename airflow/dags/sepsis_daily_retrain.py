from __future__ import annotations

import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

APP_ROOT = Path("/app")
MLOPS_SRC = str(APP_ROOT / "mlops" / "src")

PARAMS_PATH = str(APP_ROOT / "params.yaml")
MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")

default_args = {
    "owner": "sepsis-cdss",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def _run_module(module: str, argv: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = MLOPS_SRC + os.pathsep + env.get("PYTHONPATH", "")
    env["MLFLOW_TRACKING_URI"] = MLFLOW_URI
    result = subprocess.run(
        [sys.executable, "-m", module, *argv],
        cwd=str(APP_ROOT),
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{module} exited with code {result.returncode}")


def validate_data_fn(**_ctx) -> None:
    import yaml

    params = yaml.safe_load((APP_ROOT / "params.yaml").read_text(encoding="utf-8"))
    raw_dir = APP_ROOT / params["data"]["raw_dir"]
    files = list(raw_dir.glob("training_set*/*.psv"))
    if len(files) < 1000:
        raise FileNotFoundError(
            f"Only {len(files)} .psv files under {raw_dir}, expected ~40,000. "
            "Download the PhysioNet 2019 sepsis dataset first."
        )
    logging.info(f"Validated {len(files)} patient files in {raw_dir}")


def prepare_data_fn(**_ctx) -> None:
    _run_module("sepsis_mlops.prepare_data", ["--params", PARAMS_PATH])


def train_fn(**_ctx) -> None:
    _run_module("sepsis_mlops.train", [
        "--params", PARAMS_PATH,
        "--output", str(APP_ROOT / "artifacts" / "model" / "challenger.json"),
    ])


def evaluate_fn(**_ctx) -> None:
    _run_module("sepsis_mlops.evaluate", [
        "--params", PARAMS_PATH,
        "--checkpoint", str(APP_ROOT / "artifacts" / "model" / "challenger.json"),
        "--output", str(APP_ROOT / "artifacts" / "evaluation" / "metrics.json"),
    ])


def compare_and_register_fn(**_ctx) -> None:
    _run_module("sepsis_mlops.compare_and_register", [
        "--params", PARAMS_PATH,
        "--checkpoint", str(APP_ROOT / "artifacts" / "model" / "challenger.json"),
        "--metrics", str(APP_ROOT / "artifacts" / "evaluation" / "metrics.json"),
    ])


with DAG(
    dag_id="sepsis_daily_retrain",
    default_args=default_args,
    description="Daily sepsis early-warning model retraining pipeline",
    schedule_interval="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sepsis", "mlops", "retraining"],
) as dag:

    t_validate = PythonOperator(task_id="validate_data", python_callable=validate_data_fn)
    t_prepare = PythonOperator(task_id="prepare_data", python_callable=prepare_data_fn)
    t_train = PythonOperator(task_id="train_challenger", python_callable=train_fn)
    t_evaluate = PythonOperator(task_id="evaluate_challenger", python_callable=evaluate_fn)
    t_compare = PythonOperator(task_id="compare_and_register", python_callable=compare_and_register_fn)

    t_validate >> t_prepare >> t_train >> t_evaluate >> t_compare

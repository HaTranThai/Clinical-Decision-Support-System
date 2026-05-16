"""Evaluate a saved ECG XGBoost classifier against the fixed holdout test set.

The test set (test.npz) is produced by prepare_data.py from patient-level
split records. No re-splitting is performed here.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import mlflow
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from .config import load_config
from .data import FEATURE_NAMES, feature_matrix, load_arrays

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _predict_proba(bst: xgb.Booster, dmatrix: xgb.DMatrix) -> np.ndarray:
    best = getattr(bst, "best_iteration", None)
    if best is not None and best > 0:
        return bst.predict(dmatrix, iteration_range=(0, best + 1))
    return bst.predict(dmatrix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ECG XGBoost challenger on holdout test set")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--test-data", default="data/processed/test.npz")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.json")
    parser.add_argument("--output", default="artifacts/evaluation/metrics.json")
    args = parser.parse_args()

    cfg = load_config(args.params)

    logger.info(f"Loading test data from {args.test_data}")
    arrays = load_arrays(Path(args.test_data))

    logger.info(f"Loading model from {args.checkpoint}")
    bst = xgb.Booster()
    bst.load_model(args.checkpoint)

    idx_to_label_raw = bst.attr("idx_to_label")
    idx_to_label = (
        {int(k): v for k, v in json.loads(idx_to_label_raw).items()}
        if idx_to_label_raw
        else {0: "N", 1: "A", 2: "V"}
    )

    x_test = feature_matrix(arrays)
    y_test = arrays.labels.astype(int)
    dtest = xgb.DMatrix(x_test, feature_names=FEATURE_NAMES)

    probs = _predict_proba(bst, dtest)
    preds = np.argmax(probs, axis=1)

    target_names = [idx_to_label[i] for i in sorted(idx_to_label)]
    label_indices = sorted(idx_to_label.keys())

    accuracy = float(accuracy_score(y_test, preds))
    f1_macro = float(f1_score(y_test, preds, average="macro", zero_division=0))

    per_class_f1 = f1_score(y_test, preds, labels=label_indices, average=None, zero_division=0)
    per_class_precision = precision_score(y_test, preds, labels=label_indices, average=None, zero_division=0)
    per_class_recall = recall_score(y_test, preds, labels=label_indices, average=None, zero_division=0)

    per_class: dict[str, dict[str, float]] = {}
    for i, idx in enumerate(label_indices):
        per_class[idx_to_label[idx]] = {
            "f1": float(per_class_f1[i]),
            "precision": float(per_class_precision[i]),
            "recall": float(per_class_recall[i]),
        }

    metrics = {
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "per_class": per_class,
        "classification_report": classification_report(
            y_test, preds, target_names=target_names, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
        "n_test_beats": int(y_test.shape[0]),
        "test_records": cfg.test_records,
        "checkpoint": args.checkpoint,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    logger.info(f"Saved metrics to {output}")
    logger.info(f"Test accuracy={accuracy:.4f}  F1_macro={f1_macro:.4f}")
    for label, pc in per_class.items():
        logger.info(f"  {label}: F1={pc['f1']:.4f}  P={pc['precision']:.4f}  R={pc['recall']:.4f}")

    # Log to MLflow — attach to the same run that produced the model when possible
    mlflow.set_experiment(cfg.experiment_name)
    run_id = bst.attr("mlflow_run_id")

    mlflow_metrics = {"eval_accuracy": accuracy, "eval_f1_macro": f1_macro}
    for label, pc in per_class.items():
        mlflow_metrics[f"eval_f1_{label}"] = pc["f1"]
        mlflow_metrics[f"eval_precision_{label}"] = pc["precision"]
        mlflow_metrics[f"eval_recall_{label}"] = pc["recall"]

    if run_id:
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics(mlflow_metrics)
            mlflow.log_artifact(str(output), artifact_path="evaluation")
    else:
        with mlflow.start_run(run_name="offline-evaluation"):
            mlflow.log_metrics(mlflow_metrics)
            mlflow.log_artifact(str(output), artifact_path="evaluation")


if __name__ == "__main__":
    main()

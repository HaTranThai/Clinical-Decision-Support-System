from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import mlflow
import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .config import load_config
from .data import load_split
from .features import feature_columns
from .schema import LABEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _predict_proba(bst: xgb.Booster, dmatrix: xgb.DMatrix) -> np.ndarray:
    best = getattr(bst, "best_iteration", None)
    if best is not None and best > 0:
        return bst.predict(dmatrix, iteration_range=(0, best + 1))
    return bst.predict(dmatrix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate sepsis model on frozen val holdout")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.json")
    parser.add_argument("--output", default="artifacts/evaluation/metrics.json")
    args = parser.parse_args()

    cfg = load_config(args.params)
    feat_cols = feature_columns(cfg.rolling_window)

    logger.info("Loading val split (frozen evaluation holdout)")
    val_df = load_split(cfg.processed_dir, "val")
    x_val = val_df[feat_cols].to_numpy(dtype=np.float32)
    y_val = val_df[LABEL].to_numpy(dtype=np.int8)

    logger.info(f"Loading model from {args.checkpoint}")
    bst = xgb.Booster()
    bst.load_model(args.checkpoint)

    dval = xgb.DMatrix(x_val, feature_names=feat_cols)
    proba = _predict_proba(bst, dval)

    thr = cfg.decision_threshold
    preds = (proba >= thr).astype(np.int8)

    auroc = float(roc_auc_score(y_val, proba))
    auprc = float(average_precision_score(y_val, proba))
    tn, fp, fn, tp = confusion_matrix(y_val, preds, labels=[0, 1]).ravel()
    sensitivity = float(tp / (tp + fn)) if (tp + fn) else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) else 0.0

    metrics = {
        "auroc": auroc,
        "auprc": auprc,
        "eval_split": "val",
        "decision_threshold": thr,
        "precision": float(precision_score(y_val, preds, zero_division=0)),
        "recall": float(recall_score(y_val, preds, zero_division=0)),
        "f1": float(f1_score(y_val, preds, zero_division=0)),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "n_eval_rows": int(len(y_val)),
        "n_eval_positive": int(y_val.sum()),
        "checkpoint": args.checkpoint,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    logger.info(f"Saved metrics to {output}")
    logger.info(f"Val AUROC={auroc:.4f} AUPRC={auprc:.4f} "
                f"Sens={sensitivity:.4f} Spec={specificity:.4f}")

    mlflow.set_experiment(cfg.experiment_name)
    run_id = bst.attr("mlflow_run_id")
    mlflow_metrics = {
        "eval_auroc": auroc,
        "eval_auprc": auprc,
        "val_auroc": auroc,
        "val_auprc": auprc,
        "eval_sensitivity": sensitivity,
        "eval_specificity": specificity,
        "eval_precision": metrics["precision"],
        "eval_f1": metrics["f1"],
    }

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

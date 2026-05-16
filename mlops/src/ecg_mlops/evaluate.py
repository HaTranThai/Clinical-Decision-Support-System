"""Evaluate a saved ECG classifier checkpoint against the fixed holdout test set.

The test set (test.npz) is produced by prepare_data.py from patient-level split records.
No re-splitting is performed here.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import mlflow
import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch.utils.data import DataLoader, TensorDataset

from .config import load_config
from .data import load_arrays
from .paths import add_service_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

add_service_sources()

from model_def import CNN_RR4_Morph8  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ECG challenger checkpoint on holdout test set")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--test-data", default="data/processed/test.npz")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.pt")
    parser.add_argument("--output", default="artifacts/evaluation/metrics.json")
    args = parser.parse_args()

    cfg = load_config(args.params)

    logger.info(f"Loading test data from {args.test_data}")
    arrays = load_arrays(Path(args.test_data))

    logger.info(f"Loading checkpoint from {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    idx_to_label: dict[int, str] = {
        int(k): v for k, v in checkpoint.get("idx_to_label", {0: "N", 1: "A", 2: "V"}).items()
    }
    in_ch = checkpoint.get("in_ch", arrays.segments.shape[1])
    n_classes = checkpoint.get("n_classes", len(idx_to_label))

    dataset = TensorDataset(
        torch.tensor(arrays.segments, dtype=torch.float32),
        torch.tensor(arrays.rr4, dtype=torch.float32),
        torch.tensor(arrays.m8, dtype=torch.float32),
        torch.tensor(arrays.labels, dtype=torch.long),
    )
    loader = DataLoader(dataset, batch_size=cfg.batch_size, shuffle=False, num_workers=0)

    model = CNN_RR4_Morph8(in_ch=in_ch, n_classes=n_classes)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    all_labels: list[int] = []
    all_preds: list[int] = []
    with torch.no_grad():
        for x, rr4, m8, y in loader:
            logits = model(x, rr4, m8)
            all_preds.extend(torch.argmax(logits, dim=1).tolist())
            all_labels.extend(y.tolist())

    target_names = [idx_to_label[i] for i in sorted(idx_to_label)]
    label_indices = sorted(idx_to_label.keys())

    accuracy = float(accuracy_score(all_labels, all_preds))
    f1_macro = float(f1_score(all_labels, all_preds, average="macro", zero_division=0))

    # Per-class metrics
    per_class_f1 = f1_score(all_labels, all_preds, labels=label_indices, average=None, zero_division=0)
    per_class_precision = precision_score(all_labels, all_preds, labels=label_indices, average=None, zero_division=0)
    per_class_recall = recall_score(all_labels, all_preds, labels=label_indices, average=None, zero_division=0)

    per_class: dict[str, dict[str, float]] = {}
    for i, idx in enumerate(label_indices):
        label = idx_to_label[idx]
        per_class[label] = {
            "f1": float(per_class_f1[i]),
            "precision": float(per_class_precision[i]),
            "recall": float(per_class_recall[i]),
        }

    metrics = {
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "per_class": per_class,
        "classification_report": classification_report(
            all_labels, all_preds, target_names=target_names, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(all_labels, all_preds).tolist(),
        "n_test_beats": len(all_labels),
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

    # Log to MLflow — attach to the same run that produced the checkpoint
    mlflow.set_experiment(cfg.experiment_name)
    run_id = checkpoint.get("mlflow_run_id")

    mlflow_metrics = {
        "eval_accuracy": accuracy,
        "eval_f1_macro": f1_macro,
    }
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

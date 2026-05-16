"""Train the ECG beat classifier (XGBoost) and log the run to MLflow.

Expects pre-split train.npz and val.npz produced by prepare_data.py.
The model is a gradient-boosted tree ensemble on 12 tabular features
(RR4 interval features + M8 morphology features). No data splitting is
performed here — patient-level splits are fixed upstream.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import mlflow
import mlflow.xgboost
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score

from .config import load_config
from .data import FEATURE_NAMES, IDX_TO_LABEL, feature_matrix, load_arrays

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

N_CLASSES = len(IDX_TO_LABEL)


def _predict_proba(bst: xgb.Booster, dmatrix: xgb.DMatrix) -> np.ndarray:
    """Predict class probabilities, honouring the early-stopping best iteration."""
    best = getattr(bst, "best_iteration", None)
    if best is not None and best > 0:
        return bst.predict(dmatrix, iteration_range=(0, best + 1))
    return bst.predict(dmatrix)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ECG arrhythmia XGBoost classifier")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--train-data", default="data/processed/train.npz")
    parser.add_argument("--val-data", default="data/processed/val.npz")
    parser.add_argument("--output", default="artifacts/model/challenger.json")
    args = parser.parse_args()

    cfg = load_config(args.params)

    logger.info(f"Loading train data from {args.train_data}")
    train_arrays = load_arrays(Path(args.train_data))
    logger.info(f"Loading val data from {args.val_data}")
    val_arrays = load_arrays(Path(args.val_data))

    x_train = feature_matrix(train_arrays)
    y_train = train_arrays.labels.astype(int)
    x_val = feature_matrix(val_arrays)
    y_val = val_arrays.labels.astype(int)

    # Class-weighted sample weights to counter MIT-BIH imbalance (N >> V > A)
    class_counts = np.bincount(y_train, minlength=N_CLASSES)
    class_weights = class_counts.sum() / (N_CLASSES * np.maximum(class_counts, 1))
    sample_weight = class_weights[y_train]
    logger.info(
        f"Class counts={class_counts.tolist()} "
        f"weights={[round(float(w), 3) for w in class_weights]}"
    )

    dtrain = xgb.DMatrix(x_train, label=y_train, weight=sample_weight, feature_names=FEATURE_NAMES)
    dval = xgb.DMatrix(x_val, label=y_val, feature_names=FEATURE_NAMES)

    xgb_params = {
        "objective": "multi:softprob",
        "num_class": N_CLASSES,
        "max_depth": cfg.xgb_max_depth,
        "eta": cfg.xgb_eta,
        "subsample": cfg.xgb_subsample,
        "colsample_bytree": cfg.xgb_colsample_bytree,
        "min_child_weight": cfg.xgb_min_child_weight,
        "eval_metric": ["mlogloss", "merror"],
        "tree_method": "hist",
        "seed": 42,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_experiment(cfg.experiment_name)

    with mlflow.start_run(run_name="challenger-train") as run:
        run_id = run.info.run_id
        logger.info(f"MLflow run_id: {run_id}")

        mlflow.log_params({
            "model_type": "xgboost",
            "train_records": ",".join(cfg.train_records),
            "val_records": ",".join(cfg.val_records),
            "n_train_beats": int(y_train.shape[0]),
            "n_val_beats": int(y_val.shape[0]),
            "n_features": len(FEATURE_NAMES),
            "num_boost_round": cfg.xgb_num_boost_round,
            "early_stopping_rounds": cfg.xgb_early_stopping_rounds,
            "max_depth": cfg.xgb_max_depth,
            "eta": cfg.xgb_eta,
            "subsample": cfg.xgb_subsample,
            "colsample_bytree": cfg.xgb_colsample_bytree,
            "min_child_weight": cfg.xgb_min_child_weight,
            "class_weights": ",".join(f"{w:.3f}" for w in class_weights),
        })

        evals_result: dict = {}
        bst = xgb.train(
            xgb_params,
            dtrain,
            num_boost_round=cfg.xgb_num_boost_round,
            evals=[(dtrain, "train"), (dval, "val")],
            early_stopping_rounds=cfg.xgb_early_stopping_rounds,
            evals_result=evals_result,
            verbose_eval=False,
        )

        # Log the boosting curves per round
        for i, value in enumerate(evals_result["val"]["mlogloss"]):
            mlflow.log_metric("val_mlogloss", value, step=i)
        for i, value in enumerate(evals_result["train"]["mlogloss"]):
            mlflow.log_metric("train_mlogloss", value, step=i)

        # Validation metrics
        val_pred = np.argmax(_predict_proba(bst, dval), axis=1)
        val_f1 = float(f1_score(y_val, val_pred, average="macro", zero_division=0))
        val_acc = float(accuracy_score(y_val, val_pred))

        mlflow.log_metrics({
            "val_f1_macro": val_f1,
            "val_accuracy": val_acc,
            "best_iteration": int(bst.best_iteration),
            "n_trees": int(bst.num_boosted_rounds()),
        })
        logger.info(
            f"Training done — best_iteration={bst.best_iteration} "
            f"val_f1_macro={val_f1:.4f} val_accuracy={val_acc:.4f}"
        )

        # Persist metadata inside the model file via booster attributes
        bst.set_attr(
            idx_to_label=json.dumps(IDX_TO_LABEL),
            mlflow_run_id=run_id,
            feature_names=json.dumps(FEATURE_NAMES),
        )

        bst.save_model(str(output_path))
        mlflow.xgboost.log_model(bst, artifact_path="model")
        mlflow.log_artifact(str(output_path), artifact_path="checkpoint")
        logger.info(f"Saved challenger model to {output_path}")


if __name__ == "__main__":
    main()

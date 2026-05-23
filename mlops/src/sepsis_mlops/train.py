from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import mlflow
import mlflow.xgboost
import numpy as np
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

from .config import load_config
from .data import load_split, train_subrole
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
    parser = argparse.ArgumentParser(description="Train sepsis XGBoost classifier")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--output", default="artifacts/model/challenger.json")
    args = parser.parse_args()

    cfg = load_config(args.params)
    feat_cols = feature_columns(cfg.rolling_window)

    logger.info("Loading train split (val stays frozen for evaluation only)")
    train_df = load_split(cfg.processed_dir, "train")

    es_frac = cfg.xgb_early_stopping_holdout_frac
    roles = train_df["patient_id"].map(
        lambda pid: train_subrole(str(pid), es_frac, cfg.random_seed)
    )
    is_es = (roles == "es").to_numpy()
    fit_df = train_df[~is_es]
    es_df = train_df[is_es]
    logger.info(f"Train split: {len(fit_df)} fit rows, {len(es_df)} early-stopping rows "
                f"(carved from train, val untouched)")

    x_train = fit_df[feat_cols].to_numpy(dtype=np.float32)
    y_train = fit_df[LABEL].to_numpy(dtype=np.int8)
    x_es = es_df[feat_cols].to_numpy(dtype=np.float32)
    y_es = es_df[LABEL].to_numpy(dtype=np.int8)
    del train_df, fit_df, es_df

    n_pos = int(y_train.sum())
    n_neg = int(len(y_train) - n_pos)
    scale_pos_weight = n_neg / max(n_pos, 1)
    logger.info(f"Fit rows={len(y_train)} pos={n_pos} neg={n_neg} "
                f"scale_pos_weight={scale_pos_weight:.2f}")

    dtrain = xgb.DMatrix(x_train, label=y_train, feature_names=feat_cols)
    dval = xgb.DMatrix(x_es, label=y_es, feature_names=feat_cols)
    y_val = y_es
    del x_train, x_es

    xgb_params = {
        "objective": "binary:logistic",
        "eval_metric": ["auc", "aucpr"],
        "max_depth": cfg.xgb_max_depth,
        "eta": cfg.xgb_eta,
        "subsample": cfg.xgb_subsample,
        "colsample_bytree": cfg.xgb_colsample_bytree,
        "min_child_weight": cfg.xgb_min_child_weight,
        "gamma": cfg.xgb_gamma,
        "scale_pos_weight": scale_pos_weight,
        "tree_method": "hist",
        "seed": cfg.random_seed,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_experiment(cfg.experiment_name)

    with mlflow.start_run(run_name="challenger-train") as run:
        run_id = run.info.run_id
        logger.info(f"MLflow run_id: {run_id}")

        mlflow.log_params({
            "model_type": "xgboost",
            "n_fit_rows": len(y_train),
            "n_es_rows": len(y_val),
            "n_features": len(feat_cols),
            "num_boost_round": cfg.xgb_num_boost_round,
            "early_stopping_rounds": cfg.xgb_early_stopping_rounds,
            "max_depth": cfg.xgb_max_depth,
            "eta": cfg.xgb_eta,
            "subsample": cfg.xgb_subsample,
            "colsample_bytree": cfg.xgb_colsample_bytree,
            "min_child_weight": cfg.xgb_min_child_weight,
            "gamma": cfg.xgb_gamma,
            "scale_pos_weight": round(scale_pos_weight, 3),
            "rolling_window": cfg.rolling_window,
        })

        evals_result: dict = {}
        bst = xgb.train(
            xgb_params,
            dtrain,
            num_boost_round=cfg.xgb_num_boost_round,
            evals=[(dtrain, "fit"), (dval, "es")],
            early_stopping_rounds=cfg.xgb_early_stopping_rounds,
            evals_result=evals_result,
            verbose_eval=False,
        )

        for i, value in enumerate(evals_result["es"]["auc"]):
            mlflow.log_metric("es_auc_curve", value, step=i)

        es_proba = _predict_proba(bst, dval)
        es_auroc = float(roc_auc_score(y_val, es_proba))
        es_auprc = float(average_precision_score(y_val, es_proba))

        mlflow.log_metrics({
            "es_auroc": es_auroc,
            "es_auprc": es_auprc,
            "best_iteration": int(bst.best_iteration),
        })
        logger.info(f"Training done best_iteration={bst.best_iteration} "
                    f"es_auroc={es_auroc:.4f} es_auprc={es_auprc:.4f}")

        bst.set_attr(
            mlflow_run_id=run_id,
            feature_names=json.dumps(feat_cols),
            rolling_window=str(cfg.rolling_window),
        )

        bst.save_model(str(output_path))
        mlflow.xgboost.log_model(bst, artifact_path="model")
        mlflow.log_artifact(str(output_path), artifact_path="checkpoint")
        logger.info(f"Saved challenger model to {output_path}")


if __name__ == "__main__":
    main()

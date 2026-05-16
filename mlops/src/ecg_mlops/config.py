"""Configuration loading for MLOps jobs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .paths import REPO_ROOT


@dataclass(frozen=True)
class PipelineConfig:
    data_dir: Path
    processed_dir: Path
    artifacts_dir: Path
    experiment_name: str
    registered_model_name: str
    # Patient-level split records
    train_records: list[str]
    val_records: list[str]
    test_records: list[str]
    # Backward-compat: all records combined
    records: list[str]
    # XGBoost hyperparams
    xgb_num_boost_round: int
    xgb_early_stopping_rounds: int
    xgb_max_depth: int
    xgb_eta: float
    xgb_subsample: float
    xgb_colsample_bytree: float
    xgb_min_child_weight: float
    # Evaluate
    thr_a: float
    min_f1_macro: float


def _get(source: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    value: Any = source
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


def load_config(params_path: str | Path = REPO_ROOT / "params.yaml") -> PipelineConfig:
    path = Path(params_path)
    with path.open("r", encoding="utf-8") as fh:
        params = yaml.safe_load(fh) or {}

    train_records = [str(r) for r in _get(params, "data.split.train_records", [])]
    val_records = [str(r) for r in _get(params, "data.split.val_records", [])]
    test_records = [str(r) for r in _get(params, "data.split.test_records", [])]

    # Backward compat: if no split defined, fall back to flat records list
    if not train_records and not val_records and not test_records:
        all_records = [str(r) for r in _get(params, "data.records", ["223"])]
        train_records = all_records
    else:
        all_records = train_records + val_records + test_records

    return PipelineConfig(
        data_dir=REPO_ROOT / _get(params, "data.raw_dir", "services/replay-producer/data"),
        processed_dir=REPO_ROOT / _get(params, "data.processed_dir", "data/processed"),
        artifacts_dir=REPO_ROOT / _get(params, "artifacts.dir", "artifacts"),
        experiment_name=str(_get(params, "tracking.experiment_name", "ecg-cdss-arrhythmia")),
        registered_model_name=str(_get(params, "tracking.registered_model_name", "ecg-cdss-xgb-rr4-morph8")),
        train_records=train_records,
        val_records=val_records,
        test_records=test_records,
        records=all_records,
        xgb_num_boost_round=int(_get(params, "xgboost.num_boost_round", 400)),
        xgb_early_stopping_rounds=int(_get(params, "xgboost.early_stopping_rounds", 40)),
        xgb_max_depth=int(_get(params, "xgboost.max_depth", 6)),
        xgb_eta=float(_get(params, "xgboost.eta", 0.1)),
        xgb_subsample=float(_get(params, "xgboost.subsample", 0.8)),
        xgb_colsample_bytree=float(_get(params, "xgboost.colsample_bytree", 0.8)),
        xgb_min_child_weight=float(_get(params, "xgboost.min_child_weight", 1.0)),
        thr_a=float(_get(params, "evaluate.thr_a", 0.65)),
        min_f1_macro=float(_get(params, "evaluate.min_f1_macro", 0.75)),
    )

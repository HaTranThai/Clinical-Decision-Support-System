from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .paths import REPO_ROOT


@dataclass(frozen=True)
class PipelineConfig:
    raw_dir: Path
    processed_dir: Path
    artifacts_dir: Path
    experiment_name: str
    registered_model_name: str
    train_frac: float
    val_frac: float
    test_frac: float
    random_seed: int
    operational_enabled: bool
    operational_served_status: list[str]
    rolling_window: int
    xgb_num_boost_round: int
    xgb_early_stopping_rounds: int
    xgb_early_stopping_holdout_frac: float
    xgb_max_depth: int
    xgb_eta: float
    xgb_subsample: float
    xgb_colsample_bytree: float
    xgb_min_child_weight: float
    xgb_gamma: float
    decision_threshold: float
    min_auroc: float


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

    return PipelineConfig(
        raw_dir=REPO_ROOT / _get(params, "data.raw_dir", "Data/sepsis-2019"),
        processed_dir=REPO_ROOT / _get(params, "data.processed_dir", "data/processed"),
        artifacts_dir=REPO_ROOT / _get(params, "artifacts.dir", "artifacts"),
        experiment_name=str(_get(params, "tracking.experiment_name", "sepsis-cdss")),
        registered_model_name=str(_get(params, "tracking.registered_model_name", "sepsis-xgb-earlywarning")),
        train_frac=float(_get(params, "data.split.train_frac", 0.70)),
        val_frac=float(_get(params, "data.split.val_frac", 0.15)),
        test_frac=float(_get(params, "data.split.test_frac", 0.15)),
        random_seed=int(_get(params, "data.split.random_seed", 42)),
        operational_enabled=bool(_get(params, "operational.enabled", True)),
        operational_served_status=list(_get(params, "operational.served_status", ["ENDED", "RUNNING"])),
        rolling_window=int(_get(params, "features.rolling_window", 6)),
        xgb_num_boost_round=int(_get(params, "xgboost.num_boost_round", 600)),
        xgb_early_stopping_rounds=int(_get(params, "xgboost.early_stopping_rounds", 50)),
        xgb_early_stopping_holdout_frac=float(_get(params, "xgboost.early_stopping_holdout_frac", 0.12)),
        xgb_max_depth=int(_get(params, "xgboost.max_depth", 6)),
        xgb_eta=float(_get(params, "xgboost.eta", 0.05)),
        xgb_subsample=float(_get(params, "xgboost.subsample", 0.8)),
        xgb_colsample_bytree=float(_get(params, "xgboost.colsample_bytree", 0.8)),
        xgb_min_child_weight=float(_get(params, "xgboost.min_child_weight", 5.0)),
        xgb_gamma=float(_get(params, "xgboost.gamma", 1.0)),
        decision_threshold=float(_get(params, "evaluate.decision_threshold", 0.5)),
        min_auroc=float(_get(params, "evaluate.min_auroc", 0.75)),
    )

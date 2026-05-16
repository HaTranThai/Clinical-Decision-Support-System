"""Configuration loading for MLOps jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
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
    # Train hyperparams
    epochs: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    # Evaluate
    thr_a: float
    min_f1_macro: float
    # Legacy split params (kept for backward compat, no longer used for splitting)
    test_size: float
    val_size: float
    random_seed: int


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
        registered_model_name=str(_get(params, "tracking.registered_model_name", "ecg-cdss-cnn-rr4-morph8")),
        train_records=train_records,
        val_records=val_records,
        test_records=test_records,
        records=all_records,
        epochs=int(_get(params, "train.epochs", 30)),
        batch_size=int(_get(params, "train.batch_size", 128)),
        learning_rate=float(_get(params, "train.learning_rate", 0.001)),
        weight_decay=float(_get(params, "train.weight_decay", 0.0001)),
        thr_a=float(_get(params, "evaluate.thr_a", 0.65)),
        min_f1_macro=float(_get(params, "evaluate.min_f1_macro", 0.75)),
        # Legacy
        test_size=float(_get(params, "split.test_size", 0.2)),
        val_size=float(_get(params, "split.val_size", 0.1)),
        random_seed=int(_get(params, "split.random_seed", 42)),
    )

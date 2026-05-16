"""Model loader — loads an XGBoost booster from a local file or MLflow URI."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import xgboost as xgb

logger = logging.getLogger(__name__)

DEFAULT_IDX_TO_LABEL = {0: "N", 1: "A", 2: "V"}


def load_model(checkpoint_path: str) -> tuple[xgb.Booster, dict[int, str], int]:
    """Load the trained XGBoost model.

    The model file carries metadata as booster attributes:
    - idx_to_label: JSON mapping of class index to label
    - mlflow_run_id: the run that produced it

    Args:
        checkpoint_path: a local .json path, or an MLflow URI
            (runs:/, models:/, mlflow-artifacts:).

    Returns:
        booster: loaded XGBoost booster
        idx_to_label: index to label mapping
        a_idx: index of the "A" class (-1 if absent)
    """
    parsed = urlparse(checkpoint_path)

    if parsed.scheme in {"runs", "models", "mlflow-artifacts"}:
        try:
            import mlflow.xgboost
        except ImportError as exc:
            raise RuntimeError(
                "MODEL_URI points to an MLflow artifact, but mlflow is not "
                "installed in the inference-service image."
            ) from exc
        logger.info(f"Loading XGBoost model from MLflow URI {checkpoint_path}")
        booster = mlflow.xgboost.load_model(checkpoint_path)
    else:
        path = Path(checkpoint_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {checkpoint_path}")
        logger.info(f"Loading XGBoost model from {path}")
        booster = xgb.Booster()
        booster.load_model(str(path))

    idx_to_label_raw = booster.attr("idx_to_label")
    if idx_to_label_raw:
        idx_to_label = {int(k): v for k, v in json.loads(idx_to_label_raw).items()}
    else:
        idx_to_label = dict(DEFAULT_IDX_TO_LABEL)

    a_idx = next((idx for idx, lab in idx_to_label.items() if lab == "A"), -1)

    logger.info(f"Model loaded: idx_to_label={idx_to_label}, a_idx={a_idx}")
    return booster, idx_to_label, a_idx

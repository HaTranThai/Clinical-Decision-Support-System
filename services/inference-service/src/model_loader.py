from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import xgboost as xgb

logger = logging.getLogger(__name__)


def load_model(checkpoint_path: str) -> tuple[xgb.Booster, list[str]]:
    parsed = urlparse(checkpoint_path)

    if parsed.scheme in {"runs", "models", "mlflow-artifacts"}:
        try:
            import mlflow.xgboost
        except ImportError as exc:
            raise RuntimeError(
                "MODEL_URI points to an MLflow artifact, but mlflow is not installed."
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

    feature_names = booster.feature_names
    if not feature_names:
        attr = booster.attr("feature_names")
        if attr:
            feature_names = json.loads(attr)
    if not feature_names:
        raise RuntimeError("Booster has no feature_names; cannot build inference vector.")

    logger.info(f"Model loaded: {len(feature_names)} features.")
    return booster, list(feature_names)

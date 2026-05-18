from __future__ import annotations

import numpy as np
import xgboost as xgb


def _risk_level(risk: float) -> str:
    if risk >= 0.6:
        return "HIGH"
    if risk >= 0.3:
        return "MEDIUM"
    return "LOW"


def predict(booster: xgb.Booster, feature_names: list[str], features_dict: dict) -> dict:
    vector = []
    for name in feature_names:
        value = features_dict.get(name)
        if value is None:
            vector.append(np.nan)
        else:
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                vector.append(np.nan)

    dmatrix = xgb.DMatrix(
        np.asarray([vector], dtype=np.float32),
        feature_names=feature_names,
    )

    best = getattr(booster, "best_iteration", None)
    if best is not None and best > 0:
        preds = booster.predict(dmatrix, iteration_range=(0, best + 1))
    else:
        preds = booster.predict(dmatrix)

    risk = float(preds[0])
    return {
        "risk_score": round(risk, 6),
        "risk_level": _risk_level(risk),
    }

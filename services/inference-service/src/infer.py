"""Inference logic — XGBoost prediction with A-threshold gating."""
from __future__ import annotations

import logging

import numpy as np
import xgboost as xgb

logger = logging.getLogger(__name__)

# RR4 (4 interval features) + M8 (8 morphology features) = 12 tabular features.
# Must match ecg_mlops.data.FEATURE_NAMES used at training time.
FEATURE_NAMES = [f"rr4_{i}" for i in range(4)] + [f"m8_{i}" for i in range(8)]


def predict_beat(
    model: xgb.Booster,
    rr4: list[float],
    m8: list[float],
    idx_to_label: dict[int, str],
    a_idx: int,
    thr_a: float = 0.65,
) -> dict:
    """Run inference on a single beat.

    Args:
        model: loaded XGBoost booster
        rr4: RR4 interval features (4,)
        m8: morphology features (8,)
        idx_to_label: class index to label mapping
        a_idx: index of the "A" class
        thr_a: threshold for A-class gating

    Returns:
        dict with pred_class, confidence, pA, probs, gated_A
    """
    rr4 = list(rr4) if rr4 else [0.0, 0.0, 1.0, 0.0]
    m8 = list(m8) if m8 else [0.0] * 8
    features = np.asarray([rr4 + m8], dtype=np.float32)  # (1, 12)

    dmatrix = xgb.DMatrix(features, feature_names=FEATURE_NAMES)

    best = getattr(model, "best_iteration", None)
    if best is not None and best > 0:
        probs = model.predict(dmatrix, iteration_range=(0, best + 1))[0]
    else:
        probs = model.predict(dmatrix)[0]

    pred_idx = int(np.argmax(probs))
    pred_lab = idx_to_label.get(pred_idx, "N")
    confidence = float(probs[pred_idx])

    pA = float(probs[a_idx]) if a_idx >= 0 else 0.0

    # A-threshold gating: low-confidence A predictions fall back to N
    gated_A = False
    if pred_lab == "A" and pA < thr_a:
        pred_lab = "N"
        gated_A = True

    probs_dict = {lab: round(float(probs[int(idx)]), 4) for idx, lab in idx_to_label.items()}

    return {
        "pred_class": pred_lab,
        "confidence": round(confidence, 4),
        "pA": round(pA, 4),
        "probs": probs_dict,
        "gated_A": gated_A,
    }

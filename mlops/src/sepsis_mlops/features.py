from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import DEMOGRAPHICS, LABEL, SIGNAL_COLUMNS, VITALS

ROLL_STATS = ["rmean", "rmin", "rmax", "rstd", "delta"]


def feature_columns(rolling_window: int = 6) -> list[str]:
    cols: list[str] = list(SIGNAL_COLUMNS)
    cols += list(DEMOGRAPHICS)
    for vital in VITALS:
        cols += [f"{vital}_{stat}" for stat in ROLL_STATS]
    cols += [f"{sig}_tslm" for sig in SIGNAL_COLUMNS]
    return cols


def _time_since_measured(measured: np.ndarray) -> np.ndarray:
    idx = np.arange(len(measured))
    last_seen = np.where(measured, idx, -1)
    last_seen = np.maximum.accumulate(last_seen)
    return np.where(last_seen >= 0, idx - last_seen, np.nan).astype(np.float32)


def engineer_patient(df: pd.DataFrame, patient_id: str, rolling_window: int = 6) -> pd.DataFrame:
    df = df.reset_index(drop=True)
    signal = df[SIGNAL_COLUMNS]
    measured = signal.notna()
    ffilled = signal.ffill()

    cols: dict[str, object] = {}

    for col in SIGNAL_COLUMNS:
        cols[col] = ffilled[col].astype(np.float32).to_numpy()

    for col in DEMOGRAPHICS:
        cols[col] = df[col].astype(np.float32).to_numpy()

    for vital in VITALS:
        series = ffilled[vital]
        roll = series.rolling(rolling_window, min_periods=1)
        cols[f"{vital}_rmean"] = roll.mean().astype(np.float32).to_numpy()
        cols[f"{vital}_rmin"] = roll.min().astype(np.float32).to_numpy()
        cols[f"{vital}_rmax"] = roll.max().astype(np.float32).to_numpy()
        cols[f"{vital}_rstd"] = roll.std().astype(np.float32).to_numpy()
        cols[f"{vital}_delta"] = series.diff().astype(np.float32).to_numpy()

    for col in SIGNAL_COLUMNS:
        cols[f"{col}_tslm"] = _time_since_measured(measured[col].to_numpy())

    cols[LABEL] = df[LABEL].astype(np.int8).to_numpy()
    cols["patient_id"] = patient_id
    return pd.DataFrame(cols)

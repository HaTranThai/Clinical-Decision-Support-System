from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import ALL_COLUMNS, LABEL


@dataclass(frozen=True)
class PatientSplit:
    train: list[Path]
    val: list[Path]
    test: list[Path]


def list_patient_files(raw_dir: Path) -> list[Path]:
    files = sorted(raw_dir.glob("training_set*/*.psv"))
    if not files:
        raise RuntimeError(
            f"No .psv files found under {raw_dir}. "
            "Run download_sepsis.py / the download notebook first."
        )
    return files


def patient_id_of(path: Path) -> str:
    return path.stem


def read_psv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|")
    missing = [c for c in ALL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")
    return df


def patient_is_septic(path: Path) -> bool:
    labels = pd.read_csv(path, sep="|", usecols=[LABEL])[LABEL]
    return bool(labels.max() == 1)


def split_patients(
    files: list[Path],
    septic_flags: list[bool],
    train_frac: float,
    val_frac: float,
    seed: int,
) -> PatientSplit:
    rng = np.random.default_rng(seed)
    files_arr = np.array(files, dtype=object)
    flags = np.array(septic_flags, dtype=bool)

    train: list[Path] = []
    val: list[Path] = []
    test: list[Path] = []

    for flag_value in (True, False):
        group = files_arr[flags == flag_value]
        group = group[rng.permutation(len(group))]
        n = len(group)
        n_train = int(round(n * train_frac))
        n_val = int(round(n * val_frac))
        train.extend(group[:n_train].tolist())
        val.extend(group[n_train:n_train + n_val].tolist())
        test.extend(group[n_train + n_val:].tolist())

    return PatientSplit(train=sorted(train), val=sorted(val), test=sorted(test))


def load_split(processed_dir: Path, split: str) -> pd.DataFrame:
    return pd.read_parquet(processed_dir / f"{split}.parquet")

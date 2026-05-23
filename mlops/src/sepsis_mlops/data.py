from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .schema import ALL_COLUMNS, LABEL

logger = logging.getLogger(__name__)


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


def _unit_hash(key: str, salt: str) -> float:
    digest = hashlib.sha256(f"{salt}:{key}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0x1000000000000)


def assign_split(patient_id: str, train_frac: float, val_frac: float, seed: int) -> str:
    bucket = _unit_hash(patient_id, f"split-{seed}")
    if bucket < train_frac:
        return "train"
    if bucket < train_frac + val_frac:
        return "val"
    return "test"


def train_subrole(patient_id: str, es_frac: float, seed: int) -> str:
    if es_frac <= 0:
        return "fit"
    return "es" if _unit_hash(patient_id, f"es-{seed}") < es_frac else "fit"


def served_patient_ids(statuses: list[str]) -> set[str]:
    dsn = os.environ.get("OPERATIONAL_DB_DSN")
    if not dsn:
        logger.info("OPERATIONAL_DB_DSN not set — skipping operational data, static split only")
        return set()
    try:
        import psycopg2
    except ImportError:
        logger.warning("psycopg2 not available — skipping operational data")
        return set()
    placeholders = ",".join(["%s"] * len(statuses))
    query = f"SELECT DISTINCT source_record FROM icu_stay WHERE status IN ({placeholders})"
    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        logger.warning(f"Could not connect to operational DB ({exc}) — skipping operational data")
        return set()
    try:
        with conn.cursor() as cur:
            cur.execute(query, statuses)
            rows = cur.fetchall()
    finally:
        conn.close()
    ids = {str(r[0]).strip() for r in rows if r[0]}
    logger.info(f"Operational DB reported {len(ids)} distinct served source_records")
    return ids


def build_split(
    files: list[Path],
    served_ids: set[str],
    train_frac: float,
    val_frac: float,
    seed: int,
) -> PatientSplit:
    train: list[Path] = []
    val: list[Path] = []
    test: list[Path] = []
    promoted = 0

    for path in files:
        pid = patient_id_of(path)
        role = assign_split(pid, train_frac, val_frac, seed)
        if role == "val":
            val.append(path)
        elif role == "train":
            train.append(path)
        else:
            if pid in served_ids:
                train.append(path)
                promoted += 1
            else:
                test.append(path)

    if promoted:
        logger.info(f"Promoted {promoted} served test-pool patients into train (operational loop)")

    return PatientSplit(train=sorted(train), val=sorted(val), test=sorted(test))


def load_split(processed_dir: Path, split: str) -> pd.DataFrame:
    return pd.read_parquet(processed_dir / f"{split}.parquet")

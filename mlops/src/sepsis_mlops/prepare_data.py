from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from .config import load_config
from .data import list_patient_files, patient_id_of, patient_is_septic, read_psv, split_patients
from .features import engineer_patient, feature_columns
from .schema import LABEL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _flag_worker(path: Path) -> tuple[Path, bool]:
    return path, patient_is_septic(path)


def _engineer_worker(args: tuple[Path, int]) -> pd.DataFrame:
    path, rolling_window = args
    df = read_psv(path)
    return engineer_patient(df, patient_id_of(path), rolling_window)


def _build_split(files: list[Path], rolling_window: int, n_workers: int) -> pd.DataFrame:
    with Pool(n_workers) as pool:
        frames = pool.map(
            _engineer_worker,
            [(f, rolling_window) for f in files],
            chunksize=64,
        )
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare sepsis feature tables")
    parser.add_argument("--params", default="params.yaml")
    args = parser.parse_args()

    cfg = load_config(args.params)
    n_workers = max(1, min(12, (os.cpu_count() or 4)))

    files = list_patient_files(cfg.raw_dir)
    logger.info(f"Found {len(files)} patient files in {cfg.raw_dir}")

    logger.info("Pass 1: reading labels for stratified split")
    with Pool(n_workers) as pool:
        flag_results = pool.map(_flag_worker, files, chunksize=64)
    ordered_files = [p for p, _ in flag_results]
    septic_flags = [is_sep for _, is_sep in flag_results]
    n_septic = sum(septic_flags)
    logger.info(f"{n_septic}/{len(files)} patients become septic "
                f"({100 * n_septic / len(files):.1f}%)")

    split = split_patients(
        ordered_files, septic_flags, cfg.train_frac, cfg.val_frac, cfg.random_seed
    )

    cfg.processed_dir.mkdir(parents=True, exist_ok=True)
    feat_cols = feature_columns(cfg.rolling_window)
    stats: dict = {}

    for name, split_files in (("train", split.train), ("val", split.val), ("test", split.test)):
        logger.info(f"Pass 2: engineering '{name}' ({len(split_files)} patients)")
        df = _build_split(split_files, cfg.rolling_window, n_workers)
        out_path = cfg.processed_dir / f"{name}.parquet"
        df.to_parquet(out_path, index=False)

        n_pos = int(df[LABEL].sum())
        stats[name] = {
            "n_patients": len(split_files),
            "n_rows": int(len(df)),
            "n_positive": n_pos,
            "positive_rate": round(n_pos / len(df), 5) if len(df) else 0.0,
        }
        logger.info(f"[{name}] {len(df)} rows, {n_pos} positive "
                    f"({stats[name]['positive_rate'] * 100:.2f}%) -> {out_path}")
        del df

    dataset_stats = {
        **stats,
        "n_features": len(feat_cols),
        "feature_columns": feat_cols,
        "total_patients": len(files),
        "rolling_window": cfg.rolling_window,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    stats_path = cfg.processed_dir / "dataset_stats.json"
    stats_path.write_text(json.dumps(dataset_stats, indent=2), encoding="utf-8")
    logger.info(f"Saved {stats_path}")

    print("\n" + "=" * 64)
    print(f"{'Split':<8}{'Patients':>10}{'Rows':>12}{'Positive':>12}{'Pos rate':>11}")
    print("-" * 64)
    for name in ("train", "val", "test"):
        s = stats[name]
        print(f"{name:<8}{s['n_patients']:>10}{s['n_rows']:>12}{s['n_positive']:>12}"
              f"{s['positive_rate'] * 100:>10.2f}%")
    print("=" * 64)
    print(f"Features per row: {len(feat_cols)}")


if __name__ == "__main__":
    main()

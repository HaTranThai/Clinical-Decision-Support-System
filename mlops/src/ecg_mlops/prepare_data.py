"""Prepare patient-level split model-ready arrays from MIT-BIH WFDB records.

Outputs three separate npz files (train/val/test) to avoid data leakage.
The split is fixed at the patient (record) level and defined in params.yaml.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .config import load_config
from .data import IDX_TO_LABEL, build_arrays_for_records, save_arrays

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _class_counts(labels: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(labels, return_counts=True)
    return {IDX_TO_LABEL[int(u)]: int(c) for u, c in zip(unique, counts)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Patient-level ECG data preparation")
    parser.add_argument("--params", default="params.yaml")
    args = parser.parse_args()

    cfg = load_config(args.params)
    out_dir = cfg.processed_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    splits = {
        "train": cfg.train_records,
        "val": cfg.val_records,
        "test": cfg.test_records,
    }

    stats: dict[str, dict] = {}

    for split_name, records in splits.items():
        if not records:
            logger.warning(f"No records defined for split '{split_name}', skipping.")
            continue

        logger.info(f"Building {split_name} arrays from {len(records)} records: {records}")
        arrays = build_arrays_for_records(cfg.data_dir, records)
        out_path = out_dir / f"{split_name}.npz"
        save_arrays(arrays, out_path)

        counts = _class_counts(arrays.labels)
        stats[split_name] = {
            "n_beats": int(arrays.labels.shape[0]),
            "records": records,
            "class_counts": counts,
        }
        logger.info(
            f"  [{split_name}] {arrays.labels.shape[0]} beats — "
            + ", ".join(f"{k}:{v}" for k, v in counts.items())
        )

    dataset_stats = {
        **stats,
        "total_records": len(cfg.train_records) + len(cfg.val_records) + len(cfg.test_records),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    stats_path = out_dir / "dataset_stats.json"
    stats_path.write_text(json.dumps(dataset_stats, indent=2), encoding="utf-8")
    logger.info(f"Saved dataset_stats.json to {stats_path}")

    # Print summary table
    total_beats = sum(v["n_beats"] for v in stats.values())
    print("\n" + "=" * 60)
    print(f"{'Split':<8} {'Records':>7} {'Beats':>8} {'N':>7} {'A':>7} {'V':>7}")
    print("-" * 60)
    for split_name, info in stats.items():
        cc = info["class_counts"]
        print(
            f"{split_name:<8} {len(info['records']):>7} {info['n_beats']:>8} "
            f"{cc.get('N', 0):>7} {cc.get('A', 0):>7} {cc.get('V', 0):>7}"
        )
    print("-" * 60)
    print(f"{'TOTAL':<8} {sum(len(v['records']) for v in stats.values()):>7} {total_beats:>8}")
    print("=" * 60)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mlops" / "src"))

from sepsis_mlops.config import load_config
from sepsis_mlops.data import build_split, list_patient_files, served_patient_ids

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror train/val/test split into folders of symlinks")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--out-dir", default="data/splits")
    args = parser.parse_args()

    cfg = load_config(args.params)
    out_dir = REPO_ROOT / args.out_dir

    files = list_patient_files(cfg.raw_dir)
    served_ids = served_patient_ids(cfg.operational_served_status) if cfg.operational_enabled else set()
    split = build_split(files, served_ids, cfg.train_frac, cfg.val_frac, cfg.random_seed)

    for name, paths in (("train", split.train), ("val", split.val), ("test", split.test)):
        split_dir = out_dir / name
        split_dir.mkdir(parents=True, exist_ok=True)
        for existing in split_dir.glob("*.psv"):
            existing.unlink()
        for path in paths:
            (split_dir / path.name).symlink_to(path.resolve())
        print(f"[{name}] {len(paths)} symlinks -> {split_dir}")

    test_list = out_dir / "test_patients.txt"
    test_list.write_text("\n".join(p.stem for p in split.test) + "\n", encoding="utf-8")
    print(f"Test patient ids written to {test_list}")


if __name__ == "__main__":
    main()

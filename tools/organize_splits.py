from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_psv_index(raw_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in raw_dir.glob("training_set*/*.psv"):
        index[path.stem] = path.resolve()
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror train/val/test split into folders of symlinks")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--raw-dir", default="Data/sepsis-2019")
    parser.add_argument("--out-dir", default="data/splits")
    args = parser.parse_args()

    processed_dir = REPO_ROOT / args.processed_dir
    raw_dir = REPO_ROOT / args.raw_dir
    out_dir = REPO_ROOT / args.out_dir

    psv_index = build_psv_index(raw_dir)
    print(f"Indexed {len(psv_index)} .psv files under {raw_dir}")

    for split in ("train", "val", "test"):
        parquet = processed_dir / f"{split}.parquet"
        patient_ids = sorted(set(pd.read_parquet(parquet, columns=["patient_id"])["patient_id"]))

        split_dir = out_dir / split
        split_dir.mkdir(parents=True, exist_ok=True)
        for existing in split_dir.glob("*.psv"):
            existing.unlink()

        linked = 0
        missing = []
        for pid in patient_ids:
            source = psv_index.get(pid)
            if source is None:
                missing.append(pid)
                continue
            (split_dir / f"{pid}.psv").symlink_to(source)
            linked += 1

        print(f"[{split}] {linked} symlinks -> {split_dir}"
              + (f"  ({len(missing)} missing)" if missing else ""))


if __name__ == "__main__":
    main()

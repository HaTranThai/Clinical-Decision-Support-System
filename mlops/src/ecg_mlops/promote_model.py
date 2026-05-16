"""Promote a checkpoint into the serving artifact location.

This module is a manual fallback / direct-promotion utility.
In the normal MLOps pipeline, promotion is handled by compare_and_register.py
which performs Champion/Challenger comparison via MLflow Model Registry.

Use this script when you need to force-promote a specific checkpoint
without going through the registry comparison logic.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .paths import REPO_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manually promote a checkpoint to the inference-service serving location"
    )
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.json")
    parser.add_argument(
        "--target",
        default=None,
        help="Destination path. Defaults to services/inference-service/artifacts/best_mitbih_v25.json",
    )
    parser.add_argument("--metrics", default="artifacts/evaluation/metrics.json")
    parser.add_argument("--min-f1", type=float, default=0.0, help="Minimum f1_macro required for promotion")
    args = parser.parse_args()

    cfg = load_config(args.params)

    # Validate metrics if available
    metrics: dict = {}
    metrics_path = Path(args.metrics)
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        current_f1 = float(metrics.get("f1_macro", 0.0))
        if args.min_f1 > 0.0 and current_f1 < args.min_f1:
            raise SystemExit(
                f"Model f1_macro={current_f1:.4f} is below --min-f1={args.min_f1:.4f}. "
                "Promotion aborted."
            )
        logger.info(f"Model metrics: accuracy={metrics.get('accuracy', '?')} f1_macro={current_f1:.4f}")
    else:
        logger.warning(f"Metrics file not found at {metrics_path}. Promoting without validation.")

    # Determine target path
    if args.target:
        target_path = Path(args.target)
    else:
        target_dir = REPO_ROOT / "services" / "inference-service" / "artifacts"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "best_mitbih_v25.json"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.checkpoint, target_path)
    logger.info(f"Copied {args.checkpoint} → {target_path}")

    # Write manifest
    manifest = {
        "registered_model_name": cfg.registered_model_name,
        "stage": "manual-promotion",
        "source_checkpoint": str(Path(args.checkpoint).resolve()),
        "serving_checkpoint": str(target_path),
        "metrics": metrics,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = target_path.parent / "model_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()

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
    parser = argparse.ArgumentParser(description="Manually promote a checkpoint to serving")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.json")
    parser.add_argument("--metrics", default="artifacts/evaluation/metrics.json")
    parser.add_argument("--min-auroc", type=float, default=0.0)
    args = parser.parse_args()

    cfg = load_config(args.params)

    metrics: dict = {}
    metrics_path = Path(args.metrics)
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        auroc = float(metrics.get("auroc", 0.0))
        if args.min_auroc > 0.0 and auroc < args.min_auroc:
            raise SystemExit(f"AUROC {auroc:.4f} below --min-auroc {args.min_auroc:.4f}. Aborted.")
        logger.info(f"Checkpoint metrics: AUROC={auroc:.4f}")

    target_dir = REPO_ROOT / "services" / "inference-service" / "artifacts"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "sepsis_model.json"
    target_path.unlink(missing_ok=True)
    shutil.copyfile(args.checkpoint, target_path)
    logger.info(f"Copied {args.checkpoint} -> {target_path}")

    manifest = {
        "registered_model_name": cfg.registered_model_name,
        "stage": "manual-promotion",
        "source_checkpoint": str(Path(args.checkpoint).resolve()),
        "serving_checkpoint": str(target_path),
        "metrics": metrics,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = target_dir / "model_manifest.json"
    manifest_path.unlink(missing_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Wrote model_manifest.json")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import xgboost as xgb
from mlflow.tracking import MlflowClient

from .config import load_config
from .paths import REPO_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SERVING_MODEL_NAME = "sepsis_model.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare challenger vs champion, promote if better")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.json")
    parser.add_argument("--metrics", default="artifacts/evaluation/metrics.json")
    args = parser.parse_args()

    cfg = load_config(args.params)
    metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))

    bst = xgb.Booster()
    bst.load_model(args.checkpoint)
    run_id: str | None = bst.attr("mlflow_run_id")

    challenger_auroc = float(metrics["auroc"])
    challenger_auprc = float(metrics["auprc"])

    model_name = cfg.registered_model_name
    client = MlflowClient()

    try:
        client.create_registered_model(
            model_name,
            description="Sepsis early-warning XGBoost classifier",
        )
        logger.info(f"Created registered model: {model_name}")
    except mlflow.exceptions.MlflowException:
        pass

    mv = None
    if run_id:
        try:
            mv = client.create_model_version(
                name=model_name,
                source=f"runs:/{run_id}/model",
                run_id=run_id,
                description=f"Challenger {datetime.now(timezone.utc).date()}",
            )
            logger.info(f"Registered challenger from run artifact: version {mv.version}")
        except Exception as e:
            logger.warning(f"Could not register from run artifact: {e}")

    if mv is None:
        mv = _register_from_checkpoint(client, model_name, args.checkpoint, metrics)
        logger.info(f"Registered challenger from checkpoint file: version {mv.version}")

    client.set_model_version_tag(model_name, mv.version, "test_auroc", f"{challenger_auroc:.4f}")
    client.set_model_version_tag(model_name, mv.version, "test_auprc", f"{challenger_auprc:.4f}")
    client.set_model_version_tag(model_name, mv.version, "test_sensitivity",
                                 f"{metrics.get('sensitivity', 0.0):.4f}")
    client.set_model_version_tag(model_name, mv.version, "trained_at",
                                 datetime.now(timezone.utc).isoformat())

    champion_auroc = 0.0
    try:
        production = client.get_latest_versions(model_name, stages=["Production"])
        if production:
            champion_auroc = float(production[0].tags.get("test_auroc", 0.0))
    except Exception as e:
        logger.warning(f"Could not fetch champion: {e}")

    logger.info(f"Challenger AUROC={challenger_auroc:.4f} Champion AUROC={champion_auroc:.4f} "
                f"min_auroc={cfg.min_auroc:.4f}")

    if challenger_auroc > champion_auroc and challenger_auroc >= cfg.min_auroc:
        client.transition_model_version_stage(
            model_name, mv.version, "Production", archive_existing_versions=True
        )
        client.set_model_version_tag(model_name, mv.version, "stage_reason", "champion_replacement")

        target_dir = REPO_ROOT / "services" / "inference-service" / "artifacts"
        target_dir.mkdir(parents=True, exist_ok=True)
        serving_path = target_dir / SERVING_MODEL_NAME
        serving_path.unlink(missing_ok=True)
        shutil.copyfile(args.checkpoint, serving_path)

        manifest = {
            "model_name": model_name,
            "version": mv.version,
            "stage": "Production",
            "challenger_auroc": challenger_auroc,
            "champion_auroc": champion_auroc,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "metrics": metrics,
        }
        manifest_path = target_dir / "model_manifest.json"
        manifest_path.unlink(missing_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        logger.info(f"PROMOTED v{mv.version} to Production "
                    f"(AUROC {challenger_auroc:.4f} > champion {champion_auroc:.4f})")
    else:
        client.transition_model_version_stage(model_name, mv.version, "Archived")
        if challenger_auroc < cfg.min_auroc:
            reason = f"below min_auroc ({challenger_auroc:.4f} < {cfg.min_auroc:.4f})"
        else:
            reason = f"not better than champion ({challenger_auroc:.4f} <= {champion_auroc:.4f})"
        client.set_model_version_tag(model_name, mv.version, "stage_reason", reason)
        logger.info(f"Challenger ARCHIVED {reason}")


def _register_from_checkpoint(
    client: MlflowClient,
    model_name: str,
    checkpoint_path: str,
    metrics: dict,
) -> "mlflow.entities.model_registry.ModelVersion":
    mlflow.set_experiment("sepsis-cdss")
    with mlflow.start_run(run_name="challenger-register-fallback") as run:
        mlflow.log_metrics({"test_auroc": metrics["auroc"], "test_auprc": metrics["auprc"]})
        mlflow.log_artifact(checkpoint_path, artifact_path="checkpoint")
        run_id = run.info.run_id

    return client.create_model_version(
        name=model_name,
        source=f"runs:/{run_id}/checkpoint",
        run_id=run_id,
        description=f"Challenger checkpoint fallback {datetime.now(timezone.utc).date()}",
    )


if __name__ == "__main__":
    main()

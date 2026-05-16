"""Champion/Challenger comparison and MLflow Model Registry promotion."""
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

SERVING_MODEL_NAME = "best_mitbih_v25.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare challenger vs champion and promote if better")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--checkpoint", default="artifacts/model/challenger.json")
    parser.add_argument("--metrics", default="artifacts/evaluation/metrics.json")
    args = parser.parse_args()

    cfg = load_config(args.params)
    metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))

    bst = xgb.Booster()
    bst.load_model(args.checkpoint)
    run_id: str | None = bst.attr("mlflow_run_id")

    challenger_f1 = float(metrics["f1_macro"])
    challenger_accuracy = float(metrics["accuracy"])

    model_name = cfg.registered_model_name
    client = MlflowClient()

    # Ensure model exists in registry
    try:
        client.create_registered_model(
            model_name,
            description="ECG Arrhythmia XGBoost (RR4+M8 features) — MIT-BIH 48 records",
        )
        logger.info(f"Created registered model: {model_name}")
    except mlflow.exceptions.MlflowException:
        pass  # Already exists

    # Register challenger version
    mv = None
    if run_id:
        model_uri = f"runs:/{run_id}/model"
        try:
            mv = client.create_model_version(
                name=model_name,
                source=model_uri,
                run_id=run_id,
                description=f"Challenger {datetime.now(timezone.utc).date()}",
            )
            logger.info(f"Registered challenger from run artifact: version {mv.version}")
        except Exception as e:
            logger.warning(f"Could not register from run artifact: {e}. Falling back to checkpoint file.")

    if mv is None:
        mv = _register_from_checkpoint(client, model_name, args.checkpoint, metrics)
        logger.info(f"Registered challenger from checkpoint file: version {mv.version}")

    # Tag metrics on the version
    client.set_model_version_tag(model_name, mv.version, "test_f1_macro", f"{challenger_f1:.4f}")
    client.set_model_version_tag(model_name, mv.version, "test_accuracy", f"{challenger_accuracy:.4f}")
    client.set_model_version_tag(model_name, mv.version, "trained_at", datetime.now(timezone.utc).isoformat())
    for label, pc in metrics.get("per_class", {}).items():
        client.set_model_version_tag(model_name, mv.version, f"test_f1_{label}", f"{pc['f1']:.4f}")

    # Get champion (Production) metrics
    champion_f1 = 0.0
    champion_version = None
    try:
        production_versions = client.get_latest_versions(model_name, stages=["Production"])
        if production_versions:
            champion_version = production_versions[0]
            champion_f1 = float(champion_version.tags.get("test_f1_macro", 0.0))
            if champion_f1 == 0.0:
                try:
                    champ_run = client.get_run(champion_version.run_id)
                    champion_f1 = float(champ_run.data.metrics.get("eval_f1_macro", 0.0))
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Could not fetch champion version: {e}")

    logger.info(
        f"Challenger F1={challenger_f1:.4f} | Champion F1={champion_f1:.4f} | "
        f"min_f1_macro={cfg.min_f1_macro:.4f}"
    )

    if challenger_f1 > champion_f1 and challenger_f1 >= cfg.min_f1_macro:
        client.transition_model_version_stage(
            model_name, mv.version, "Production", archive_existing_versions=True
        )
        client.set_model_version_tag(model_name, mv.version, "stage_reason", "champion_replacement")

        # Copy model to serving location
        target_dir = REPO_ROOT / "services" / "inference-service" / "artifacts"
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.checkpoint, target_dir / SERVING_MODEL_NAME)

        manifest = {
            "model_name": model_name,
            "version": mv.version,
            "stage": "Production",
            "challenger_f1": challenger_f1,
            "champion_f1": champion_f1,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "metrics": metrics,
        }
        (target_dir / "model_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        logger.info(
            f"PROMOTED v{mv.version} to Production "
            f"(F1 {challenger_f1:.4f} > champion {champion_f1:.4f})"
        )
    else:
        client.transition_model_version_stage(model_name, mv.version, "Archived")
        if challenger_f1 < cfg.min_f1_macro:
            reason = f"below min_f1_macro threshold ({challenger_f1:.4f} < {cfg.min_f1_macro:.4f})"
        else:
            reason = f"not better than champion ({challenger_f1:.4f} <= {champion_f1:.4f})"
        client.set_model_version_tag(model_name, mv.version, "stage_reason", reason)
        logger.info(f"Challenger ARCHIVED — {reason}")


def _register_from_checkpoint(
    client: MlflowClient,
    model_name: str,
    checkpoint_path: str,
    metrics: dict,
) -> "mlflow.entities.model_registry.ModelVersion":
    """Fallback: log checkpoint as MLflow artifact and register."""
    mlflow.set_experiment("ecg-cdss-arrhythmia")
    with mlflow.start_run(run_name="challenger-register-fallback") as run:
        mlflow.log_metrics({
            "test_f1_macro": metrics["f1_macro"],
            "test_accuracy": metrics["accuracy"],
        })
        mlflow.log_artifact(checkpoint_path, artifact_path="checkpoint")
        run_id = run.info.run_id

    return client.create_model_version(
        name=model_name,
        source=f"runs:/{run_id}/checkpoint",
        run_id=run_id,
        description=f"Challenger (checkpoint fallback) {datetime.now(timezone.utc).date()}",
    )


if __name__ == "__main__":
    main()

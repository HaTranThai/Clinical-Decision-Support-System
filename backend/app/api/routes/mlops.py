"""MLOps API routes — proxy to MLflow and Airflow."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, require_admin
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

DATASET_STATS_PATH = Path("/app/data/processed/dataset_stats.json")
MODEL_NAME = "ecg-cdss-cnn-rr4-morph8"


# ── Internal HTTP helpers ──────────────────────────────────────────────────────

async def _mlflow_get(path: str, params: dict | None = None) -> dict:
    """GET request to MLflow REST API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{settings.MLFLOW_TRACKING_URI}{path}", params=params)
        r.raise_for_status()
        return r.json()


async def _mlflow_post(path: str, body: dict) -> dict:
    """POST request to MLflow REST API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{settings.MLFLOW_TRACKING_URI}{path}", json=body)
        r.raise_for_status()
        return r.json()


async def _airflow_get(path: str, params: dict | None = None) -> dict:
    """GET request to Airflow REST API with basic auth."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{settings.AIRFLOW_API_URL}{path}",
            params=params,
            auth=(settings.AIRFLOW_USERNAME, settings.AIRFLOW_PASSWORD),
        )
        r.raise_for_status()
        return r.json()


def _ms_to_iso(ms: int | None) -> str | None:
    """Convert epoch milliseconds to ISO-8601 UTC string."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/experiments")
async def get_experiments(_user=Depends(get_current_user)):
    """List recent MLflow runs across all experiments (last 50, newest first)."""
    try:
        exps_data = await _mlflow_get(
            "/api/2.0/mlflow/experiments/search", {"max_results": 10}
        )
        exp_ids = [e["experiment_id"] for e in exps_data.get("experiments", [])]

        if not exp_ids:
            return {"runs": [], "total": 0}

        data = await _mlflow_post(
            "/api/2.0/mlflow/runs/search",
            {
                "experiment_ids": exp_ids,
                "max_results": 50,
                "order_by": ["start_time DESC"],
            },
        )

        runs = []
        for r in data.get("runs", []):
            info = r.get("info", {})
            run_data = r.get("data", {})
            metrics = {m["key"]: m["value"] for m in run_data.get("metrics", [])}
            params = {p["key"]: p["value"] for p in run_data.get("params", [])}

            start_ms = info.get("start_time", 0)
            end_ms = info.get("end_time")
            duration = (
                round((end_ms - start_ms) / 1000)
                if end_ms and start_ms
                else None
            )

            runs.append(
                {
                    "run_id": info.get("run_id"),
                    "run_name": info.get("run_name", ""),
                    "status": info.get("status"),
                    "start_time": _ms_to_iso(start_ms),
                    "end_time": _ms_to_iso(end_ms),
                    "duration_sec": duration,
                    "experiment_id": info.get("experiment_id"),
                    "params": params,
                    "metrics": metrics,
                }
            )

        return {"runs": runs, "total": len(runs)}

    except httpx.HTTPError as exc:
        logger.warning("MLflow unavailable for experiments: %s", exc)
        return {"runs": [], "total": 0, "error": "MLflow unavailable"}


@router.get("/registry")
async def get_registry(_user=Depends(get_current_user)):
    """List all versions of the production model from MLflow Model Registry."""
    try:
        data = await _mlflow_post(
            "/api/2.0/mlflow/model-versions/search",
            {
                "filter": f"name='{MODEL_NAME}'",
                "max_results": 20,
                "order_by": ["version_number DESC"],
            },
        )

        versions = []
        for mv in data.get("model_versions", []):
            versions.append(
                {
                    "version": mv.get("version"),
                    "stage": mv.get("current_stage", "None"),
                    "creation_timestamp": _ms_to_iso(mv.get("creation_timestamp")),
                    "last_updated_timestamp": _ms_to_iso(
                        mv.get("last_updated_timestamp")
                    ),
                    "run_id": mv.get("run_id"),
                    "description": mv.get("description", ""),
                    "tags": {t["key"]: t["value"] for t in mv.get("tags", [])},
                    "source": mv.get("source", ""),
                    "status": mv.get("status", ""),
                }
            )

        return {"model_name": MODEL_NAME, "versions": versions}

    except httpx.HTTPError as exc:
        logger.warning("MLflow registry unavailable: %s", exc)
        return {"model_name": MODEL_NAME, "versions": [], "error": "MLflow unavailable"}


@router.get("/pipeline/status")
async def get_pipeline_status(_user=Depends(get_current_user)):
    """Return the status of the Airflow DAG ecg_daily_retrain."""
    try:
        data = await _airflow_get(
            "/dags/ecg_daily_retrain/dagRuns",
            {"limit": 10, "order_by": "-start_date"},
        )

        dag_runs = data.get("dag_runs", [])

        def _transform_run(r: dict) -> dict:
            return {
                "dag_run_id": r.get("dag_run_id"),
                "state": r.get("state"),
                "start_date": r.get("start_date"),
                "end_date": r.get("end_date"),
                "run_type": r.get("run_type"),
                "logical_date": r.get("logical_date"),
            }

        last_run = _transform_run(dag_runs[0]) if dag_runs else None

        # Best-effort: fetch next scheduled run from DAG detail endpoint
        next_run: str | None = None
        try:
            dag_info = await _airflow_get("/dags/ecg_daily_retrain")
            next_run = dag_info.get("next_dagrun")
        except Exception:
            pass

        return {
            "available": True,
            "dag_id": "ecg_daily_retrain",
            "last_run": last_run,
            "recent_runs": [_transform_run(r) for r in dag_runs[:7]],
            "next_run": next_run,
        }

    except httpx.HTTPError as exc:
        logger.warning("Airflow unavailable: %s", exc)
        return {
            "available": False,
            "last_run": None,
            "recent_runs": [],
            "next_run": None,
        }


@router.get("/dataset/stats")
async def get_dataset_stats(_user=Depends(get_current_user)):
    """Return dataset statistics from the pre-computed JSON file."""
    if DATASET_STATS_PATH.exists():
        return json.loads(DATASET_STATS_PATH.read_text())
    return {"available": False}


@router.post("/registry/{version}/promote")
async def promote_model_version(version: str, _admin=Depends(require_admin)):
    """Promote a model version to Production (archives all existing Production versions)."""
    try:
        await _mlflow_post(
            "/api/2.0/mlflow/model-versions/transition-stage",
            {
                "name": MODEL_NAME,
                "version": version,
                "stage": "Production",
                "archive_existing_versions": True,
            },
        )
        return {"detail": f"Version {version} promoted to Production"}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"MLflow error: {exc}") from exc


@router.post("/registry/{version}/archive")
async def archive_model_version(version: str, _admin=Depends(require_admin)):
    """Move a model version to the Archived stage."""
    try:
        await _mlflow_post(
            "/api/2.0/mlflow/model-versions/transition-stage",
            {
                "name": MODEL_NAME,
                "version": version,
                "stage": "Archived",
            },
        )
        return {"detail": f"Version {version} archived"}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"MLflow error: {exc}") from exc

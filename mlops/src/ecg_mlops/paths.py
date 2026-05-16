"""Shared path helpers for the MLOps pipeline."""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REPLAY_SRC = REPO_ROOT / "services" / "replay-producer" / "src"
INFERENCE_SRC = REPO_ROOT / "services" / "inference-service" / "src"


def add_service_sources() -> None:
    """Make service modules importable without packaging every microservice."""
    for path in (REPLAY_SRC, INFERENCE_SRC):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

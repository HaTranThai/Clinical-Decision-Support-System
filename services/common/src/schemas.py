from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def new_uuid() -> str:
    return str(uuid.uuid4())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PatientVitalsMessage(BaseModel):
    stay_id: str
    patient_id: str
    hour: int
    ts: str
    record: dict


class PatientFeaturesMessage(BaseModel):
    stay_id: str
    patient_id: str
    hour: int
    ts: str
    features: dict


class SepsisPredictionMessage(BaseModel):
    stay_id: str
    patient_id: str
    hour: int
    ts: str
    risk_score: float
    risk_level: str
    model_version: str = "sepsis-xgb-earlywarning"


class SepsisAlertMessage(BaseModel):
    alert_id: str = Field(default_factory=new_uuid)
    stay_id: str
    patient_id: str
    start_time: str = Field(default_factory=now_iso)
    last_update: str = Field(default_factory=now_iso)
    severity: float = 0.0
    status: str = "NEW"
    evidence: dict = Field(default_factory=dict)

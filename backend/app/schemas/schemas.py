from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class ICUStayOut(BaseModel):
    stay_id: str
    patient_id: str | None
    patient_name: str | None
    start_time: str | None
    end_time: str | None
    status: str
    source_record: str | None
    class Config:
        from_attributes = True


class CreateStayRequest(BaseModel):
    patient_name: str
    external_ref: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    source_record: Optional[str] = None


class CreateStayForPatientRequest(BaseModel):
    source_record: Optional[str] = None


class IngestVitalsRequest(BaseModel):
    hour: int
    record: dict


class PatientOut(BaseModel):
    patient_id: str
    name: str | None
    external_ref: str | None
    age: int | None
    gender: str | None
    stay_count: int = 0


class PatientDetailOut(PatientOut):
    stays: list[ICUStayOut] = []


class CreatePatientRequest(BaseModel):
    name: str
    external_ref: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None


class UpdatePatientRequest(BaseModel):
    name: Optional[str] = None
    external_ref: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None


class OverviewItem(BaseModel):
    stay_id: str
    patient_id: str | None
    patient_name: str | None
    source_record: str | None
    status: str
    current_hour: int
    risk_score: float
    risk_level: str
    alert_count: int


class SepsisPredictionOut(BaseModel):
    pred_id: str
    stay_id: str
    hour: int
    risk_score: float
    risk_level: str | None
    created_at: str | None
    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    alert_id: str
    stay_id: str
    patient_id: str | None = None
    patient_name: str | None = None
    source_record: str | None = None
    start_time: str | None
    last_update: str | None
    severity: float | None
    status: str
    evidence_json: dict | None
    class Config:
        from_attributes = True


class AlertActionRequest(BaseModel):
    reason: str | None = None
    note: str | None = None


class AlertActionOut(BaseModel):
    action_id: str
    alert_id: str
    user_id: str
    action_time: str | None
    action_type: str
    reason: str | None
    note: str | None
    class Config:
        from_attributes = True


class AlertDetailOut(AlertOut):
    actions: list[AlertActionOut] = []


class SettingsUpdate(BaseModel):
    alert_risk_threshold: Optional[float] = None
    sustained_hours: Optional[int] = None
    cooldown_hours: Optional[int] = None
    hour_interval_sec: Optional[float] = None


class SettingOut(BaseModel):
    key: str
    value: str | float | int | None


class AlertsHourly(BaseModel):
    hour: int
    count: int


class AnalyticsSummary(BaseModel):
    total_alerts: int
    ack_count: int
    dismiss_count: int
    new_count: int
    dismiss_rate: float
    avg_response_time_sec: float | None


class WSMessage(BaseModel):
    type: str
    data: dict

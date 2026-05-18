from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.base import Alert, ICUStay, Patient, SepsisPrediction
from app.db.session import get_db
from app.schemas.schemas import (
    AlertOut,
    CreateStayRequest,
    ICUStayOut,
    IngestVitalsRequest,
    SepsisPredictionOut,
)
from app.services.kafka_producer import publish

router = APIRouter()

TOPIC_PATIENT_VITALS = "patient_vitals"


async def generate_case_number(db: AsyncSession) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(20):
        code = f"ICU-{today}-{secrets.token_hex(2).upper()}"
        exists = await db.execute(
            select(ICUStay.stay_id).where(ICUStay.source_record == code)
        )
        if exists.scalar_one_or_none() is None:
            return code
    return f"ICU-{today}-{secrets.token_hex(4).upper()}"


def _stay_out(s: ICUStay) -> ICUStayOut:
    return ICUStayOut(
        stay_id=str(s.stay_id),
        patient_id=str(s.patient_id) if s.patient_id else None,
        patient_name=s.patient.name if s.patient else None,
        start_time=str(s.start_time) if s.start_time else None,
        end_time=str(s.end_time) if s.end_time else None,
        status=s.status,
        source_record=s.source_record,
    )


@router.get("", response_model=list[ICUStayOut])
async def list_stays(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = (
        select(ICUStay)
        .options(selectinload(ICUStay.patient))
        .order_by(ICUStay.start_time.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        query = query.where(ICUStay.status == status)
    result = await db.execute(query)
    return [_stay_out(s) for s in result.scalars().all()]


@router.get("/{stay_id}", response_model=ICUStayOut)
async def get_stay(stay_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(ICUStay).options(selectinload(ICUStay.patient)).where(ICUStay.stay_id == stay_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="ICU stay not found")
    return _stay_out(s)


@router.post("", response_model=ICUStayOut)
async def create_stay(
    body: CreateStayRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    patient = Patient(
        patient_id=uuid.uuid4(),
        name=body.patient_name,
        external_ref=body.external_ref,
        age=body.age,
        gender=body.gender,
    )
    db.add(patient)
    stay = ICUStay(
        stay_id=uuid.uuid4(),
        patient_id=patient.patient_id,
        status="RUNNING",
        source_record=body.source_record or await generate_case_number(db),
    )
    db.add(stay)
    await db.flush()
    stay.patient = patient
    return _stay_out(stay)


@router.post("/{stay_id}/vitals")
async def ingest_vitals(
    stay_id: str,
    body: IngestVitalsRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(ICUStay).where(ICUStay.stay_id == stay_id))
    stay = result.scalar_one_or_none()
    if not stay:
        raise HTTPException(status_code=404, detail="ICU stay not found")

    message = {
        "stay_id": stay_id,
        "patient_id": str(stay.patient_id),
        "hour": body.hour,
        "ts": datetime.now(timezone.utc).isoformat(),
        "record": body.record,
    }
    try:
        publish(TOPIC_PATIENT_VITALS, message, key=stay_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Kafka publish failed: {exc}")

    return {"detail": "vitals ingested", "stay_id": stay_id, "hour": body.hour}


@router.post("/{stay_id}/stop")
async def stop_stay(stay_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(ICUStay).where(ICUStay.stay_id == stay_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="ICU stay not found")
    s.status = "ENDED"
    s.end_time = datetime.now(timezone.utc)
    await db.flush()
    return {"detail": "ICU stay stopped"}


@router.get("/{stay_id}/predictions", response_model=list[SepsisPredictionOut])
async def get_stay_predictions(
    stay_id: str,
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(
        select(SepsisPrediction)
        .where(SepsisPrediction.stay_id == stay_id)
        .order_by(SepsisPrediction.hour.asc())
        .limit(limit)
    )
    preds = result.scalars().all()
    return [
        SepsisPredictionOut(
            pred_id=str(p.pred_id),
            stay_id=str(p.stay_id),
            hour=p.hour,
            risk_score=p.risk_score,
            risk_level=p.risk_level,
            created_at=str(p.created_at) if p.created_at else None,
        )
        for p in preds
    ]


@router.get("/{stay_id}/alerts", response_model=list[AlertOut])
async def get_stay_alerts(
    stay_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(
        select(Alert).where(Alert.stay_id == stay_id).order_by(Alert.start_time.desc())
    )
    return [
        AlertOut(
            alert_id=str(a.alert_id),
            stay_id=str(a.stay_id),
            start_time=str(a.start_time) if a.start_time else None,
            last_update=str(a.last_update) if a.last_update else None,
            severity=a.severity,
            status=a.status,
            evidence_json=a.evidence_json,
        )
        for a in result.scalars().all()
    ]

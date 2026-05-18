from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.routes.stays import generate_case_number
from app.db.base import ICUStay, Patient
from app.db.session import get_db
from app.schemas.schemas import (
    CreatePatientRequest,
    CreateStayForPatientRequest,
    ICUStayOut,
    PatientDetailOut,
    PatientOut,
    UpdatePatientRequest,
)

router = APIRouter()


def _patient_out(p: Patient, stay_count: int = 0) -> PatientOut:
    return PatientOut(
        patient_id=str(p.patient_id),
        name=p.name,
        external_ref=p.external_ref,
        age=p.age,
        gender=p.gender,
        stay_count=stay_count,
    )


def _stay_out(s: ICUStay, patient_name: str | None) -> ICUStayOut:
    return ICUStayOut(
        stay_id=str(s.stay_id),
        patient_id=str(s.patient_id) if s.patient_id else None,
        patient_name=patient_name,
        start_time=str(s.start_time) if s.start_time else None,
        end_time=str(s.end_time) if s.end_time else None,
        status=s.status,
        source_record=s.source_record,
    )


@router.get("", response_model=list[PatientOut])
async def list_patients(
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Patient)
    if search:
        like = f"%{search}%"
        query = query.where(Patient.name.ilike(like) | Patient.external_ref.ilike(like))
    patients = (await db.execute(query)).scalars().all()

    count_rows = (
        await db.execute(select(ICUStay.patient_id, func.count()).group_by(ICUStay.patient_id))
    ).all()
    counts = {pid: n for pid, n in count_rows}

    return [_patient_out(p, counts.get(p.patient_id, 0)) for p in patients]


@router.get("/{patient_id}", response_model=PatientDetailOut)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(
        select(Patient).options(selectinload(Patient.stays)).where(Patient.patient_id == patient_id)
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")

    stays = sorted(p.stays, key=lambda s: str(s.start_time or ""), reverse=True)
    base = _patient_out(p, len(stays))
    return PatientDetailOut(**base.model_dump(), stays=[_stay_out(s, p.name) for s in stays])


@router.post("", response_model=PatientOut)
async def create_patient(
    body: CreatePatientRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    p = Patient(
        patient_id=uuid.uuid4(),
        name=body.name,
        external_ref=body.external_ref,
        age=body.age,
        gender=body.gender,
    )
    db.add(p)
    await db.flush()
    return _patient_out(p, 0)


@router.post("/{patient_id}/stays", response_model=ICUStayOut)
async def create_stay_for_patient(
    patient_id: str,
    body: CreateStayForPatientRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")

    stay = ICUStay(
        stay_id=uuid.uuid4(),
        patient_id=p.patient_id,
        status="RUNNING",
        source_record=body.source_record or await generate_case_number(db),
    )
    db.add(stay)
    await db.flush()
    return _stay_out(stay, p.name)


@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: str,
    body: UpdatePatientRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")

    for field in ("name", "external_ref", "age", "gender"):
        value = getattr(body, field)
        if value is not None:
            setattr(p, field, value)
    await db.flush()
    return _patient_out(p, 0)

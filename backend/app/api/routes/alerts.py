from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.base import Alert, AlertAction, User
from app.schemas.schemas import AlertOut, AlertDetailOut, AlertActionOut, AlertActionRequest
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: str | None = None,
    stay_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Alert).order_by(Alert.start_time.desc()).offset(offset).limit(limit)
    if status:
        query = query.where(Alert.status == status)
    if stay_id:
        query = query.where(Alert.stay_id == stay_id)

    result = await db.execute(query)
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


@router.get("/{alert_id}", response_model=AlertDetailOut)
async def get_alert_detail(alert_id: str, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(Alert).options(selectinload(Alert.actions)).where(Alert.alert_id == alert_id)
    )
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertDetailOut(
        alert_id=str(a.alert_id),
        stay_id=str(a.stay_id),
        start_time=str(a.start_time) if a.start_time else None,
        last_update=str(a.last_update) if a.last_update else None,
        severity=a.severity,
        status=a.status,
        evidence_json=a.evidence_json,
        actions=[
            AlertActionOut(
                action_id=str(act.action_id),
                alert_id=str(act.alert_id),
                user_id=str(act.user_id),
                action_time=str(act.action_time) if act.action_time else None,
                action_type=act.action_type,
                reason=act.reason,
                note=act.note,
            )
            for act in a.actions
        ],
    )


@router.post("/{alert_id}/ack")
async def ack_alert(
    alert_id: str,
    body: AlertActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ACK"
    alert.last_update = datetime.now(timezone.utc)

    action = AlertAction(
        alert_id=alert.alert_id,
        user_id=user.user_id,
        action_type="ACK",
        reason=body.reason,
        note=body.note,
    )
    db.add(action)
    await db.flush()
    return {"detail": "Alert acknowledged"}


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    body: AlertActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "DISMISSED"
    alert.last_update = datetime.now(timezone.utc)

    action = AlertAction(
        alert_id=alert.alert_id,
        user_id=user.user_id,
        action_type="DISMISS",
        reason=body.reason,
        note=body.note,
    )
    db.add(action)
    await db.flush()
    return {"detail": "Alert dismissed"}

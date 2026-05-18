from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.base import Alert, ICUStay, SepsisPrediction
from app.db.session import get_db
from app.schemas.schemas import OverviewItem

router = APIRouter()


@router.get("", response_model=list[OverviewItem])
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    stays = (
        await db.execute(
            select(ICUStay)
            .options(selectinload(ICUStay.patient))
            .order_by(ICUStay.start_time.desc())
        )
    ).scalars().all()

    max_hour_sub = (
        select(
            SepsisPrediction.stay_id.label("sid"),
            func.max(SepsisPrediction.hour).label("mh"),
        )
        .group_by(SepsisPrediction.stay_id)
        .subquery()
    )
    latest_preds = (
        await db.execute(
            select(SepsisPrediction).join(
                max_hour_sub,
                (SepsisPrediction.stay_id == max_hour_sub.c.sid)
                & (SepsisPrediction.hour == max_hour_sub.c.mh),
            )
        )
    ).scalars().all()
    latest = {str(p.stay_id): p for p in latest_preds}

    alert_rows = (
        await db.execute(select(Alert.stay_id, func.count()).group_by(Alert.stay_id))
    ).all()
    alert_counts = {str(sid): n for sid, n in alert_rows}

    items: list[OverviewItem] = []
    for s in stays:
        sid = str(s.stay_id)
        lp = latest.get(sid)
        items.append(OverviewItem(
            stay_id=sid,
            patient_id=str(s.patient_id) if s.patient_id else None,
            patient_name=s.patient.name if s.patient else None,
            source_record=s.source_record,
            status=s.status,
            current_hour=lp.hour if lp else 0,
            risk_score=lp.risk_score if lp else 0.0,
            risk_level=lp.risk_level if lp else "LOW",
            alert_count=alert_counts.get(sid, 0),
        ))
    return items

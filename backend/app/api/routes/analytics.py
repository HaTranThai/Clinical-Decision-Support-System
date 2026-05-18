from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, cast, Integer

from app.db.session import get_db
from app.db.base import Alert, AlertAction
from app.schemas.schemas import AnalyticsSummary
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/alerts_hourly")
async def alerts_hourly(
    stay_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    hour_expr = cast(func.extract("hour", Alert.start_time), Integer)
    query = (
        select(hour_expr.label("hour"), func.count().label("count"))
        .group_by(hour_expr)
        .order_by(hour_expr)
    )
    if stay_id:
        query = query.where(Alert.stay_id == stay_id)
    rows = (await db.execute(query)).all()
    return [{"hour": int(r[0]), "count": int(r[1])} for r in rows]


@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    total = (await db.execute(select(func.count(Alert.alert_id)))).scalar() or 0
    ack_count = (await db.execute(
        select(func.count(Alert.alert_id)).where(Alert.status == "ACK")
    )).scalar() or 0
    dismiss_count = (await db.execute(
        select(func.count(Alert.alert_id)).where(Alert.status == "DISMISSED")
    )).scalar() or 0
    new_count = (await db.execute(
        select(func.count(Alert.alert_id)).where(Alert.status == "NEW")
    )).scalar() or 0

    dismiss_rate = dismiss_count / total if total > 0 else 0.0

    avg_response = (await db.execute(text("""
        SELECT AVG(EXTRACT(EPOCH FROM (aa.action_time - a.start_time)))
        FROM alert_action aa
        JOIN alert a ON a.alert_id = aa.alert_id
        WHERE aa.action_type IN ('ACK', 'DISMISS')
    """))).scalar()

    return AnalyticsSummary(
        total_alerts=total,
        ack_count=ack_count,
        dismiss_count=dismiss_count,
        new_count=new_count,
        dismiss_rate=round(dismiss_rate, 3),
        avg_response_time_sec=round(float(avg_response), 1) if avg_response is not None else None,
    )

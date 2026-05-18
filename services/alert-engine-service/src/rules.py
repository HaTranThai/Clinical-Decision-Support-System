from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .config import AlertConfig
from .state import StayState


def check_sepsis_alert(
    state: StayState,
    current_hour: int,
    risk_score: float,
    config: AlertConfig,
) -> Optional[dict]:
    if current_hour - state.last_alert_hour < config.COOLDOWN_HOURS:
        return None

    recent = state.recent(config.SUSTAINED_HOURS)
    if len(recent) < config.SUSTAINED_HOURS:
        return None

    if not all(r.risk_score >= config.ALERT_RISK_THRESHOLD for r in recent):
        return None

    state.last_alert_hour = current_hour
    now = datetime.now(timezone.utc).isoformat()
    severity = max(r.risk_score for r in recent)

    return {
        "status": "NEW",
        "start_time": now,
        "last_update": now,
        "severity": round(float(severity), 6),
        "evidence": {
            "threshold": config.ALERT_RISK_THRESHOLD,
            "sustained_hours": config.SUSTAINED_HOURS,
            "recent": [
                {"hour": r.hour, "risk": round(float(r.risk_score), 6)}
                for r in recent
            ],
        },
    }

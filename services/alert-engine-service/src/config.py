from __future__ import annotations

import os


class AlertConfig:
    def __init__(self):
        self.ALERT_RISK_THRESHOLD = float(os.environ.get("ALERT_RISK_THRESHOLD", "0.6"))
        self.SUSTAINED_HOURS = int(os.environ.get("SUSTAINED_HOURS", "3"))
        self.COOLDOWN_HOURS = int(os.environ.get("COOLDOWN_HOURS", "12"))

    def __repr__(self):
        return (
            f"AlertConfig(ALERT_RISK_THRESHOLD={self.ALERT_RISK_THRESHOLD}, "
            f"SUSTAINED_HOURS={self.SUSTAINED_HOURS}, COOLDOWN_HOURS={self.COOLDOWN_HOURS})"
        )

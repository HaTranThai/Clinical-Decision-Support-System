import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "alert-engine-service"))

from src.config import AlertConfig
from src.rules import check_sepsis_alert
from src.state import StayState


def _config(threshold=0.6, sustained=3, cooldown=12):
    cfg = AlertConfig()
    cfg.ALERT_RISK_THRESHOLD = threshold
    cfg.SUSTAINED_HOURS = sustained
    cfg.COOLDOWN_HOURS = cooldown
    return cfg


def test_alert_triggers_on_sustained_high_risk():
    cfg = _config()
    state = StayState()
    for hour, risk in [(1, 0.7), (2, 0.8), (3, 0.9)]:
        state.add(hour, risk)
    alert = check_sepsis_alert(state, 3, 0.9, cfg)
    assert alert is not None
    assert alert["status"] == "NEW"
    assert alert["severity"] == 0.9
    assert alert["evidence"]["sustained_hours"] == 3


def test_no_alert_when_risk_below_threshold():
    cfg = _config()
    state = StayState()
    for hour, risk in [(1, 0.7), (2, 0.4), (3, 0.8)]:
        state.add(hour, risk)
    assert check_sepsis_alert(state, 3, 0.8, cfg) is None


def test_no_alert_before_enough_history():
    cfg = _config(sustained=3)
    state = StayState()
    state.add(1, 0.9)
    state.add(2, 0.9)
    assert check_sepsis_alert(state, 2, 0.9, cfg) is None


def test_cooldown_blocks_repeat_alert():
    cfg = _config(cooldown=12)
    state = StayState()
    for hour, risk in [(1, 0.7), (2, 0.8), (3, 0.9)]:
        state.add(hour, risk)
    assert check_sepsis_alert(state, 3, 0.9, cfg) is not None
    state.add(4, 0.9)
    assert check_sepsis_alert(state, 4, 0.9, cfg) is None

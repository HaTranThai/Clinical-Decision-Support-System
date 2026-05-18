from __future__ import annotations

import collections
from typing import NamedTuple


class RiskRecord(NamedTuple):
    hour: int
    risk_score: float


class StayState:
    def __init__(self):
        self.history: collections.deque[RiskRecord] = collections.deque(maxlen=2000)
        self.last_alert_hour: int = -10000

    def add(self, hour: int, risk_score: float):
        self.history.append(RiskRecord(hour, risk_score))

    def recent(self, n: int) -> list[RiskRecord]:
        return list(self.history)[-n:]


class StateManager:
    def __init__(self):
        self._stays: dict[str, StayState] = {}

    def get(self, stay_id: str) -> StayState:
        if stay_id not in self._stays:
            self._stays[stay_id] = StayState()
        return self._stays[stay_id]

    def remove(self, stay_id: str):
        self._stays.pop(stay_id, None)

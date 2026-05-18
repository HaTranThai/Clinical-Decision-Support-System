from __future__ import annotations

import pandas as pd

from .schema import ALL_COLUMNS, LABEL


class PatientBuffer:
    def __init__(self, max_hours: int = 2000):
        self._rows: dict[str, list[dict]] = {}
        self._max_hours = max_hours

    def add(self, stay_id: str, record: dict):
        rows = self._rows.setdefault(stay_id, [])
        rows.append(record)
        if len(rows) > self._max_hours:
            del rows[0]

    def frame(self, stay_id: str) -> pd.DataFrame:
        rows = self._rows.get(stay_id, [])
        normalized = []
        for record in rows:
            normalized.append({col: record.get(col, None) for col in ALL_COLUMNS})
        df = pd.DataFrame(normalized, columns=ALL_COLUMNS)
        for col in ALL_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df[LABEL] = df[LABEL].fillna(0)
        return df

    def remove(self, stay_id: str):
        self._rows.pop(stay_id, None)

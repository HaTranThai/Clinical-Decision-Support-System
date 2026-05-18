from __future__ import annotations

import json
import logging
import os

import psycopg2

logger = logging.getLogger(__name__)


def _conn_str() -> str:
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://sepsis_admin:sepsis_secret_2024@postgres:5432/sepsis_cdss",
    )
    return db_url.replace("postgresql+asyncpg://", "postgresql://")


class DBWriter:
    def __init__(self):
        self.conn = None
        try:
            self.conn = psycopg2.connect(_conn_str())
            self.conn.autocommit = True
            logger.info("Database connection established.")
        except Exception as e:
            logger.warning(f"Database connection failed (will retry on write): {e}")

    def _ensure_conn(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(_conn_str())
            self.conn.autocommit = True

    def insert_alert(self, alert: dict):
        try:
            self._ensure_conn()
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO alert (alert_id, stay_id, start_time, last_update, severity, status, evidence_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    alert["alert_id"],
                    alert["stay_id"],
                    alert["start_time"],
                    alert["last_update"],
                    alert["severity"],
                    alert["status"],
                    json.dumps(alert.get("evidence", {})),
                ),
            )
            cur.close()
            logger.info(f"Alert {alert['alert_id']} persisted to DB.")
        except Exception as e:
            logger.error(f"Failed to insert alert: {e}")

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from typing import Optional

from confluent_kafka import Consumer, KafkaError
from sqlalchemy import select

from app.core.config import settings
from app.db.session import async_session_factory
from app.db.base import SepsisPrediction, ModelVersion
from app.services.ws_broadcaster import ws_broadcaster

logger = logging.getLogger(__name__)

TOPIC_VITALS = "patient_vitals"
TOPIC_PREDICTION = "sepsis_prediction"
TOPIC_ALERT = "sepsis_alert"

TOPICS = [TOPIC_VITALS, TOPIC_PREDICTION, TOPIC_ALERT]


class KafkaConsumerService:

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self):
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Kafka consumer service started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Kafka consumer service stopped.")

    async def _persist_prediction(self, value: dict):
        stay_id = value.get("stay_id")
        if not stay_id:
            return
        try:
            async with async_session_factory() as db:
                model_version_id = None
                model_name = value.get("model_version")
                if model_name:
                    result = await db.execute(
                        select(ModelVersion.model_version_id).where(ModelVersion.name == model_name)
                    )
                    model_version_id = result.scalar_one_or_none()
                if model_version_id is None:
                    result = await db.execute(
                        select(ModelVersion.model_version_id).where(ModelVersion.is_active.is_(True))
                    )
                    model_version_id = result.scalars().first()

                stay_uuid = uuid.UUID(str(stay_id))
                hour = int(value.get("hour", 0))
                risk_score = float(value.get("risk_score", 0.0))
                risk_level = value.get("risk_level")

                existing = await db.execute(
                    select(SepsisPrediction).where(
                        SepsisPrediction.stay_id == stay_uuid,
                        SepsisPrediction.hour == hour,
                    )
                )
                pred = existing.scalar_one_or_none()
                if pred:
                    pred.risk_score = risk_score
                    pred.risk_level = risk_level
                    pred.model_version_id = model_version_id
                else:
                    db.add(SepsisPrediction(
                        pred_id=uuid.uuid4(),
                        stay_id=stay_uuid,
                        model_version_id=model_version_id,
                        hour=hour,
                        risk_score=risk_score,
                        risk_level=risk_level,
                    ))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist sepsis_prediction: {e}", exc_info=True)

    def _handle_message(self, topic: str, value: dict):
        stay_id = str(value.get("stay_id", ""))
        if not stay_id or not (self._loop and self._loop.is_running()):
            return

        if topic == TOPIC_VITALS:
            data = {
                "hour": value.get("hour"),
                "ts": value.get("ts"),
                "record": value.get("record"),
            }
            asyncio.run_coroutine_threadsafe(
                ws_broadcaster.broadcast(stay_id, "vitals", data), self._loop
            )
        elif topic == TOPIC_PREDICTION:
            asyncio.run_coroutine_threadsafe(self._persist_prediction(value), self._loop)
            data = {
                "hour": value.get("hour"),
                "ts": value.get("ts"),
                "risk_score": value.get("risk_score"),
                "risk_level": value.get("risk_level"),
            }
            asyncio.run_coroutine_threadsafe(
                ws_broadcaster.broadcast(stay_id, "prediction", data), self._loop
            )
        elif topic == TOPIC_ALERT:
            data = {
                "alert_id": value.get("alert_id"),
                "severity": value.get("severity"),
                "status": value.get("status"),
                "start_time": value.get("start_time"),
            }
            asyncio.run_coroutine_threadsafe(
                ws_broadcaster.broadcast(stay_id, "alert", data), self._loop
            )

    def _consume_loop(self):
        msg_counts: dict[str, int] = {t: 0 for t in TOPICS}

        consumer = None
        for attempt in range(30):
            if not self._running:
                return
            try:
                consumer = Consumer({
                    "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                    "group.id": "backend-ws-group",
                    "auto.offset.reset": "latest",
                    "enable.auto.commit": True,
                    "session.timeout.ms": 30000,
                })
                consumer.subscribe(TOPICS)
                logger.info(f"Kafka consumer subscribed to: {TOPICS}")
                break
            except Exception as e:
                logger.warning(f"Kafka connect attempt {attempt+1}/30 failed: {e}")
                time.sleep(2)

        if consumer is None:
            logger.error("Failed to connect to Kafka after 30 attempts")
            return

        try:
            last_log_time = time.time()
            last_resubscribe_time = time.time()

            while self._running:
                msg = consumer.poll(timeout=0.5)

                now = time.time()
                if now - last_resubscribe_time > 15:
                    consumer.subscribe(TOPICS)
                    last_resubscribe_time = now

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Kafka error: {msg.error()}")
                    continue

                topic = msg.topic()
                if topic not in TOPICS:
                    continue

                try:
                    value = json.loads(msg.value().decode("utf-8"))
                except Exception as e:
                    logger.error(f"Failed to parse message from {topic}: {e}")
                    continue

                msg_counts[topic] = msg_counts.get(topic, 0) + 1
                self._handle_message(topic, value)

                if now - last_log_time > 30:
                    logger.info(
                        f"Kafka msg counts: {msg_counts} | "
                        f"Active WS stays: {ws_broadcaster.active_stays}"
                    )
                    last_log_time = now

            consumer.close()
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}", exc_info=True)

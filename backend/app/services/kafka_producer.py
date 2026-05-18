from __future__ import annotations

import json
import logging

from confluent_kafka import Producer

from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: Producer | None = None


def _get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "backend-ingest",
        })
    return _producer


def publish(topic: str, value: dict, key: str | None = None) -> None:
    producer = _get_producer()
    producer.produce(
        topic,
        value=json.dumps(value).encode("utf-8"),
        key=key.encode("utf-8") if key else None,
    )
    producer.poll(0)
    producer.flush(3)

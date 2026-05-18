from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "src"))

from confluent_kafka import Consumer, Producer
from config import KAFKA_BOOTSTRAP_SERVERS


def create_consumer(group_id: str, topics: list[str]) -> Consumer:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP_SERVERS)
    consumer = Consumer({
        "bootstrap.servers": bootstrap,
        "group.id": group_id,
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    })
    consumer.subscribe(topics)
    return consumer


def create_producer() -> Producer:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP_SERVERS)
    return Producer({
        "bootstrap.servers": bootstrap,
        "client.id": "preprocess-buffer",
    })


def produce(producer: Producer, topic: str, value: dict, key: str | None = None):
    producer.produce(
        topic=topic,
        value=json.dumps(value).encode("utf-8"),
        key=key.encode("utf-8") if key else None,
    )
    producer.poll(0)

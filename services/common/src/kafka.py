"""Shared Kafka producer/consumer helpers."""
from __future__ import annotations

import json
import logging
import time
from typing import Callable, Optional

from confluent_kafka import Consumer, Producer, KafkaError, KafkaException

logger = logging.getLogger(__name__)


def create_producer(bootstrap_servers: str) -> Producer:
    """Create a Kafka producer."""
    conf = {
        "bootstrap.servers": bootstrap_servers,
        "client.id": "sepsis-producer",
        "acks": "1",
    }
    return Producer(conf)


def create_consumer(
    bootstrap_servers: str,
    group_id: str,
    topics: list[str],
    auto_offset_reset: str = "latest",
) -> Consumer:
    """Create a Kafka consumer."""
    conf = {
        "bootstrap.servers": bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": auto_offset_reset,
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 1000,
    }
    consumer = Consumer(conf)
    consumer.subscribe(topics)
    return consumer


def produce_message(producer: Producer, topic: str, value: dict, key: Optional[str] = None):
    """Produce a JSON message to a topic."""
    try:
        producer.produce(
            topic=topic,
            value=json.dumps(value).encode("utf-8"),
            key=key.encode("utf-8") if key else None,
        )
        producer.poll(0)
    except Exception as e:
        logger.error(f"Failed to produce to {topic}: {e}")


def consume_loop(
    consumer: Consumer,
    handler: Callable[[dict], None],
    poll_timeout: float = 1.0,
):
    """Run a consume loop calling handler for each message."""
    logger.info("Starting consume loop...")
    try:
        while True:
            msg = consumer.poll(timeout=poll_timeout)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Kafka error: {msg.error()}")
                continue
            try:
                value = json.loads(msg.value().decode("utf-8"))
                handler(value)
            except Exception as e:
                logger.error(f"Handler error: {e}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Consumer interrupted.")
    finally:
        consumer.close()


def wait_for_kafka(bootstrap_servers: str, max_retries: int = 30, delay: float = 2.0):
    """Wait for Kafka to be ready."""
    for i in range(max_retries):
        try:
            p = Producer({"bootstrap.servers": bootstrap_servers})
            p.list_topics(timeout=5)
            logger.info("Kafka is ready.")
            return
        except Exception:
            logger.info(f"Waiting for Kafka... attempt {i+1}/{max_retries}")
            time.sleep(delay)
    raise RuntimeError("Kafka not available after max retries.")

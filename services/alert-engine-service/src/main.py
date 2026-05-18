from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "src"))

from confluent_kafka import KafkaError
from config import TOPIC_SEPSIS_PREDICTION, TOPIC_SEPSIS_ALERT
from kafka import wait_for_kafka

from .config import AlertConfig
from .state import StateManager
from .rules import check_sepsis_alert
from .kafka_io import create_consumer, create_producer, produce
from .db_writer import DBWriter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("alert-engine")


def main():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    config = AlertConfig()

    logger.info(f"Starting alert engine: {config}")

    wait_for_kafka(bootstrap)

    consumer = create_consumer(
        group_id="alert-engine-group",
        topics=[TOPIC_SEPSIS_PREDICTION],
    )
    producer = create_producer()
    state_mgr = StateManager()
    db_writer = DBWriter()

    processed = 0
    alert_count = 0

    logger.info("Alert engine started. Waiting for predictions...")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Kafka error: {msg.error()}")
                continue

            try:
                value = json.loads(msg.value().decode("utf-8"))
            except Exception as e:
                logger.error(f"Failed to parse: {e}")
                continue

            stay_id = value.get("stay_id", "")
            patient_id = value.get("patient_id", "")
            hour = int(value.get("hour", 0))
            risk_score = float(value.get("risk_score", 0.0))

            state = state_mgr.get(stay_id)
            state.add(hour, risk_score)
            processed += 1

            alert = check_sepsis_alert(state, hour, risk_score, config)
            if alert:
                alert["alert_id"] = str(uuid.uuid4())
                alert["stay_id"] = stay_id
                alert["patient_id"] = patient_id
                produce(producer, TOPIC_SEPSIS_ALERT, alert, key=stay_id)
                db_writer.insert_alert(alert)
                producer.flush()
                alert_count += 1
                logger.warning(
                    f"SEPSIS ALERT: stay={stay_id[:8]}... hour={hour} "
                    f"severity={alert['severity']:.3f}"
                )

            if processed % 100 == 0:
                logger.info(f"Processed {processed} predictions, {alert_count} alerts")

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        consumer.close()
        producer.flush()
        db_writer.close()


if __name__ == "__main__":
    main()

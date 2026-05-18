from __future__ import annotations

import json
import logging
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "src"))

from confluent_kafka import KafkaError
from config import TOPIC_PATIENT_VITALS, TOPIC_PATIENT_FEATURES
from kafka import wait_for_kafka

from .buffer import PatientBuffer
from .features import engineer_patient, feature_columns
from .kafka_io import create_consumer, create_producer, produce

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("preprocess-buffer")

ROLLING_WINDOW = 6


def _clean_value(value):
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def build_features(buffer: PatientBuffer, stay_id: str) -> dict | None:
    df = buffer.frame(stay_id)
    if df.empty:
        return None
    engineered = engineer_patient(df, stay_id, rolling_window=ROLLING_WINDOW)
    last = engineered.iloc[-1]
    cols = feature_columns(ROLLING_WINDOW)
    return {col: _clean_value(last.get(col)) for col in cols}


def main():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    wait_for_kafka(bootstrap)

    consumer = create_consumer(
        group_id="preprocess-buffer-group",
        topics=[TOPIC_PATIENT_VITALS],
    )
    producer = create_producer()
    buffer = PatientBuffer()

    logger.info("Preprocess buffer service started.")
    processed = 0

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
                logger.error(f"Failed to parse message: {e}")
                continue

            stay_id = value.get("stay_id", "")
            record = value.get("record", {})

            buffer.add(stay_id, record)

            try:
                features = build_features(buffer, stay_id)
            except Exception as e:
                logger.error(f"Feature engineering failed for {stay_id}: {e}", exc_info=True)
                continue

            if features is None:
                continue

            features_msg = {
                "stay_id": stay_id,
                "patient_id": value.get("patient_id", ""),
                "hour": value.get("hour", 0),
                "ts": value.get("ts", ""),
                "features": features,
            }
            produce(producer, TOPIC_PATIENT_FEATURES, features_msg, key=stay_id)

            processed += 1
            if processed % 50 == 0:
                logger.info(f"Processed {processed} vitals messages.")

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        consumer.close()
        producer.flush()


if __name__ == "__main__":
    main()

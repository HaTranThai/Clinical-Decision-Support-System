from __future__ import annotations

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "src"))

from confluent_kafka import KafkaError
from config import TOPIC_PATIENT_FEATURES, TOPIC_SEPSIS_PREDICTION
from kafka import wait_for_kafka

from .model_loader import load_model
from .infer import predict
from .kafka_io import create_consumer, create_producer, produce

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("inference-service")

MODEL_VERSION = "sepsis-xgb-earlywarning"


def main():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    checkpoint = os.environ.get("MODEL_URI") or os.environ.get(
        "MODEL_CHECKPOINT", "artifacts/sepsis_model.json"
    )

    logger.info(f"Starting inference service: model={checkpoint}")

    wait_for_kafka(bootstrap)

    booster, feature_names = load_model(checkpoint)

    consumer = create_consumer(
        group_id="inference-service-group",
        topics=[TOPIC_PATIENT_FEATURES],
    )
    producer = create_producer()

    logger.info("Inference service started. Waiting for features...")
    count = 0

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

            try:
                result = predict(booster, feature_names, value.get("features", {}))
            except Exception as e:
                logger.error(f"Inference failed: {e}", exc_info=True)
                continue

            pred_msg = {
                "stay_id": value.get("stay_id", ""),
                "patient_id": value.get("patient_id", ""),
                "hour": value.get("hour", 0),
                "ts": value.get("ts", ""),
                "risk_score": result["risk_score"],
                "risk_level": result["risk_level"],
                "model_version": MODEL_VERSION,
            }
            produce(producer, TOPIC_SEPSIS_PREDICTION, pred_msg, key=value.get("stay_id", ""))

            count += 1
            if count % 50 == 0:
                logger.info(
                    f"Processed {count} | last risk={result['risk_score']:.3f} "
                    f"level={result['risk_level']}"
                )

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        consumer.close()
        producer.flush()


if __name__ == "__main__":
    main()

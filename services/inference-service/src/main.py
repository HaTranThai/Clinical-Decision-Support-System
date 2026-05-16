"""Inference Service — consumes beat events, runs PyTorch model, publishes predictions."""
from __future__ import annotations

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "src"))

from confluent_kafka import KafkaError
from config import TOPIC_ECG_BEAT_READY, TOPIC_ECG_PRED_BEAT
from kafka import wait_for_kafka

from .model_loader import load_model
from .infer import predict_beat
from .kafka_io import create_consumer, create_producer, produce

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("inference-service")


def main():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    checkpoint = os.environ.get("MODEL_URI") or os.environ.get("MODEL_CHECKPOINT", "artifacts/best_mitbih_v25.json")
    thr_a = float(os.environ.get("THR_A", "0.65"))
    model_version = "mitbih_v25"

    logger.info(f"Starting inference service: model={checkpoint}, thr_A={thr_a}")

    # Wait for Kafka
    wait_for_kafka(bootstrap)

    # Load model
    model, idx_to_label, a_idx = load_model(checkpoint)

    # Set up Kafka
    consumer = create_consumer(
        group_id="inference-service-group",
        topics=[TOPIC_ECG_BEAT_READY],
    )
    producer = create_producer()

    logger.info("Inference service started. Waiting for beats...")
    beat_count = 0

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

            # Run inference
            result = predict_beat(
                model=model,
                rr4=value.get("rr4", [0, 0, 1, 0]),
                m8=value.get("m8", [0] * 8),
                idx_to_label=idx_to_label,
                a_idx=a_idx,
                thr_a=thr_a,
            )

            # Build prediction message
            pred_msg = {
                "session_id": value.get("session_id", ""),
                "beat_ts_sec": value.get("beat_ts_sec", 0),
                "pred_class": result["pred_class"],
                "confidence": result["confidence"],
                "pA": result["pA"],
                "model_version": model_version,
                "probs": result["probs"],
                "gated_A": result["gated_A"],
            }

            produce(producer, TOPIC_ECG_PRED_BEAT, pred_msg, key=value.get("session_id", ""))

            beat_count += 1
            if beat_count % 50 == 0:
                logger.info(f"Processed {beat_count} beats | Last: {result['pred_class']} conf={result['confidence']:.3f}")

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        consumer.close()
        producer.flush()


if __name__ == "__main__":
    main()

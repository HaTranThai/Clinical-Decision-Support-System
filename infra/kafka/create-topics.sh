#!/bin/bash
# Create Kafka topics for Sepsis Early-Warning CDSS
KAFKA_BROKER=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}

echo "Creating Kafka topics..."

kafka-topics --create --if-not-exists --bootstrap-server $KAFKA_BROKER \
  --topic patient_vitals --partitions 3 --replication-factor 1

kafka-topics --create --if-not-exists --bootstrap-server $KAFKA_BROKER \
  --topic patient_features --partitions 3 --replication-factor 1

kafka-topics --create --if-not-exists --bootstrap-server $KAFKA_BROKER \
  --topic sepsis_prediction --partitions 3 --replication-factor 1

kafka-topics --create --if-not-exists --bootstrap-server $KAFKA_BROKER \
  --topic sepsis_alert --partitions 1 --replication-factor 1

echo "All topics created."
kafka-topics --list --bootstrap-server $KAFKA_BROKER

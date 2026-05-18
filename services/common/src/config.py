import os


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def get_env_float(key: str, default: float = 0.0) -> float:
    return float(os.environ.get(key, str(default)))


def get_env_int(key: str, default: int = 0) -> int:
    return int(os.environ.get(key, str(default)))


KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

TOPIC_PATIENT_VITALS = "patient_vitals"
TOPIC_PATIENT_FEATURES = "patient_features"
TOPIC_SEPSIS_PREDICTION = "sepsis_prediction"
TOPIC_SEPSIS_ALERT = "sepsis_alert"

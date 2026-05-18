from __future__ import annotations

import glob
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "src"))

from kafka import create_producer, produce_message, wait_for_kafka

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("replay-producer")

TOPIC_PATIENT_VITALS = "patient_vitals"

DEMO_PATIENT_ID = "e0000000-0000-0000-0000-000000000001"


def find_psv_files(data_dir: str) -> list[str]:
    patterns = [
        os.path.join(data_dir, "training_setA", "*.psv"),
        os.path.join(data_dir, "training_setB", "*.psv"),
        os.path.join(data_dir, "training_set*", "*.psv"),
    ]
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    return sorted(set(files))


def read_psv(path: str) -> tuple[list[str], list[list[str]]]:
    with open(path, "r") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip()]
    header = lines[0].split("|")
    rows = [ln.split("|") for ln in lines[1:]]
    return header, rows


def cell_to_value(cell: str):
    cell = cell.strip()
    if cell == "" or cell.lower() == "nan":
        return None
    try:
        f = float(cell)
    except ValueError:
        return None
    if f != f:
        return None
    return f


def build_record(header: list[str], row: list[str]) -> dict:
    record: dict = {}
    for i, col in enumerate(header):
        value = cell_to_value(row[i]) if i < len(row) else None
        record[col] = value
    return record


def get_db_conn():
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://sepsis_admin:sepsis_secret_2024@postgres:5432/sepsis_cdss",
    ).replace("postgresql+asyncpg://", "postgresql://")
    import psycopg2

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    return conn


def insert_patient(patient_id: str, external_ref: str, age, gender):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        age_val = int(age) if age is not None else None
        gender_val = None
        if gender is not None:
            gender_val = "M" if float(gender) >= 0.5 else "F"
        name_val = f"ICU Patient {external_ref}"
        cur.execute(
            """INSERT INTO patient (patient_id, external_ref, name, age, gender)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (patient_id) DO NOTHING""",
            (patient_id, external_ref, name_val, age_val, gender_val),
        )
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not create patient in DB: {e}")


def insert_icu_stay(stay_id: str, patient_id: str, source_record: str):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO icu_stay (stay_id, patient_id, start_time, status, source_record)
               VALUES (%s, %s, %s, 'RUNNING', %s)
               ON CONFLICT DO NOTHING""",
            (stay_id, patient_id, datetime.now(timezone.utc), source_record),
        )
        cur.close()
        conn.close()
        logger.info(f"icu_stay {stay_id} created in DB.")
    except Exception as e:
        logger.warning(f"Could not create icu_stay in DB: {e}")


def end_icu_stay(stay_id: str):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE icu_stay SET status='ENDED', end_time=%s WHERE stay_id=%s",
            (datetime.now(timezone.utc), stay_id),
        )
        cur.close()
        conn.close()
        logger.info(f"icu_stay {stay_id} marked ENDED.")
    except Exception as e:
        logger.warning(f"Could not update icu_stay in DB: {e}")


def main():
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    data_dir = os.environ.get("SEPSIS_DATA_DIR", "/app/data")
    sepsis_record = os.environ.get("SEPSIS_RECORD", "").strip()
    hour_interval = float(os.environ.get("HOUR_INTERVAL_SEC", "1.0"))
    n_patients = int(os.environ.get("N_PATIENTS", "1"))

    logger.info(
        f"Starting replay producer: data_dir={data_dir}, "
        f"hour_interval={hour_interval}s, n_patients={n_patients}"
    )

    wait_for_kafka(bootstrap)

    all_files = find_psv_files(data_dir)
    if not all_files:
        logger.error(f"No .psv files found under {data_dir}")
        sys.exit(1)

    if sepsis_record:
        selected = [f for f in all_files if os.path.basename(f).replace(".psv", "") == sepsis_record]
        if not selected:
            selected = [f for f in all_files if sepsis_record in os.path.basename(f)]
        if not selected:
            logger.error(f"Record {sepsis_record} not found, falling back to random.")
            selected = random.sample(all_files, min(n_patients, len(all_files)))
    else:
        selected = random.sample(all_files, min(n_patients, len(all_files)))

    logger.info(f"Selected patients: {[os.path.basename(f) for f in selected]}")

    producer = create_producer(bootstrap)

    patients = []
    for path in selected:
        header, rows = read_psv(path)
        stay_id = str(uuid.uuid4())
        patient_id = DEMO_PATIENT_ID if len(selected) == 1 else str(uuid.uuid4())
        source_record = os.path.basename(path).replace(".psv", "")
        first = build_record(header, rows[0]) if rows else {}
        insert_patient(patient_id, source_record, first.get("Age"), first.get("Gender"))
        insert_icu_stay(stay_id, patient_id, source_record)
        patients.append({
            "stay_id": stay_id,
            "patient_id": patient_id,
            "source_record": source_record,
            "header": header,
            "rows": rows,
        })

    max_hours = max(len(p["rows"]) for p in patients)

    for hour in range(max_hours):
        for p in patients:
            if hour >= len(p["rows"]):
                continue
            record = build_record(p["header"], p["rows"][hour])
            message = {
                "stay_id": p["stay_id"],
                "patient_id": p["patient_id"],
                "hour": hour,
                "ts": datetime.now(timezone.utc).isoformat(),
                "record": record,
            }
            produce_message(producer, TOPIC_PATIENT_VITALS, message, key=p["stay_id"])
        producer.flush()
        if hour % 10 == 0:
            logger.info(f"Streamed hour {hour}/{max_hours}")
        time.sleep(hour_interval)

    producer.flush()

    for p in patients:
        end_icu_stay(p["stay_id"])

    logger.info("Replay complete.")


if __name__ == "__main__":
    main()

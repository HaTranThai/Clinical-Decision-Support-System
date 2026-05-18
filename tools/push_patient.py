from __future__ import annotations

import argparse
import json
import sys
import time

import requests


def cell_to_value(cell: str):
    cell = cell.strip()
    if cell == "" or cell.lower() == "nan":
        return None
    try:
        value = float(cell)
    except ValueError:
        return None
    if value != value:
        return None
    return value


def read_psv(path: str) -> tuple[list[str], list[list[str]]]:
    with open(path, "r", encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    header = lines[0].split("|")
    rows = [ln.split("|") for ln in lines[1:]]
    return header, rows


def login(api: str, username: str, password: str) -> str:
    resp = requests.post(
        f"{api}/api/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def create_stay(api: str, token: str, args) -> str:
    body = {
        "patient_name": args.patient_name,
        "external_ref": args.external_ref,
        "age": args.age,
        "gender": args.gender,
        "source_record": args.source_record,
    }
    resp = requests.post(
        f"{api}/api/stays",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["stay_id"]


def push_vitals(api: str, token: str, stay_id: str, hour: int, record: dict) -> None:
    resp = requests.post(
        f"{api}/api/stays/{stay_id}/vitals",
        json={"hour": hour, "record": record},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()


def stop_stay(api: str, token: str, stay_id: str) -> None:
    requests.post(
        f"{api}/api/stays/{stay_id}/stop",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Push patient vitals into the Sepsis CDSS")
    parser.add_argument("--api", default="http://localhost:18800")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--patient-name", default="Test Patient")
    parser.add_argument("--external-ref", default=None)
    parser.add_argument("--age", type=int, default=None)
    parser.add_argument("--gender", default=None)
    parser.add_argument("--source-record", default=None)
    parser.add_argument("--stay-id", default=None,
                        help="Push into an existing stay instead of creating a new one")
    parser.add_argument("--psv", default=None,
                        help="Path to a .psv file to stream hour by hour")
    parser.add_argument("--record", default=None,
                        help="JSON of a single hour's vitals to push once")
    parser.add_argument("--hour", type=int, default=0,
                        help="Hour index for a single --record push")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Seconds between hours when streaming a .psv")
    parser.add_argument("--hours", type=int, default=None,
                        help="Limit number of hours streamed from the .psv")
    parser.add_argument("--stop", action="store_true",
                        help="Mark the stay ENDED after streaming")
    args = parser.parse_args()

    token = login(args.api, args.username, args.password)
    print(f"Logged in as {args.username}")

    stay_id = args.stay_id
    if not stay_id:
        stay_id = create_stay(args.api, token, args)
        print(f"Created stay {stay_id} for patient '{args.patient_name}'")
    else:
        print(f"Using existing stay {stay_id}")

    if args.record:
        record = json.loads(args.record)
        push_vitals(args.api, token, stay_id, args.hour, record)
        print(f"Pushed 1 record at hour {args.hour}")
        return

    if not args.psv:
        print("Nothing to stream: pass --psv <file> or --record <json>", file=sys.stderr)
        sys.exit(1)

    header, rows = read_psv(args.psv)
    if args.hours is not None:
        rows = rows[: args.hours]
    print(f"Streaming {len(rows)} hours from {args.psv} (interval {args.interval}s)")

    for hour, row in enumerate(rows):
        record = {
            col: cell_to_value(row[i]) if i < len(row) else None
            for i, col in enumerate(header)
        }
        push_vitals(args.api, token, stay_id, hour, record)
        print(f"  hour {hour + 1}/{len(rows)} pushed", flush=True)
        time.sleep(args.interval)

    if args.stop:
        stop_stay(args.api, token, stay_id)
        print("Stay marked ENDED")

    print(f"Done. stay_id={stay_id}")


if __name__ == "__main__":
    main()

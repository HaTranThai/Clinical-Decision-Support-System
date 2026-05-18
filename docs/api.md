# API Reference — Sepsis Early-Warning CDSS

Base URL: `http://localhost:18800`

All endpoints except `/api/auth/login` and `/api/health` require
`Authorization: Bearer <token>`. Interactive docs: `http://localhost:18800/docs`.

## Authentication

### POST `/api/auth/login`
Login and receive a JWT token.

**Request Body:**
```json
{ "username": "admin", "password": "admin123" }
```

**Response:**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### GET `/api/auth/me`
Get the current user profile.

---

## Overview

### GET `/api/overview`
Triage board — one entry per active ICU stay with the latest sepsis risk.

---

## Patients

### GET `/api/patients`
List patients. **Query:** `?search=<name or external ref>`

### GET `/api/patients/{patient_id}`
Patient detail, including ICU stay history.

### POST `/api/patients`
Create a patient. **Body:** `{ "name", "external_ref?", "age?", "gender?" }`

### PUT `/api/patients/{patient_id}`
Update a patient.

### POST `/api/patients/{patient_id}/stays`
Create a new ICU stay for an existing patient. **Body:** `{ "source_record?" }`
(if omitted, a unique case number `ICU-YYYYMMDD-XXXX` is generated).

---

## ICU Stays

### GET `/api/stays`
List ICU stays. **Query:** `?status=RUNNING|ENDED&limit=50&offset=0`

### GET `/api/stays/{stay_id}`
Stay detail.

### POST `/api/stays`
Create a patient + ICU stay together. **Body:** `{ "patient_name", "age?", "gender?", "source_record?" }`

### POST `/api/stays/{stay_id}/vitals`
Ingest one hour of vitals (published to Kafka `patient_vitals`).
**Body:** `{ "hour": <int>, "record": { ...vital signs... } }`

### POST `/api/stays/{stay_id}/stop`
End an ICU stay (status → `ENDED`).

### GET `/api/stays/{stay_id}/predictions`
Hourly sepsis predictions for the stay.

### GET `/api/stays/{stay_id}/alerts`
Alerts for the stay.

---

## Alerts

### GET `/api/alerts`
List alerts with filters. **Query:** `?status=NEW|ACK|DISMISSED&...`

### GET `/api/alerts/{alert_id}`
Alert detail with actions.

### POST `/api/alerts/{alert_id}/ack`
Acknowledge an alert. **Body:** `{ "reason?", "note?" }`

### POST `/api/alerts/{alert_id}/dismiss`
Dismiss an alert. **Body:** `{ "reason?", "note?" }`

---

## Analytics

### GET `/api/analytics/alerts_hourly`
Alert counts per hour of day.

### GET `/api/analytics/summary`
Aggregate statistics (total alerts, acknowledged, dismissed, etc.).

---

## Admin — Settings

### GET `/api/admin/settings`
Get system settings. Requires Admin role.

### PUT `/api/admin/settings`
Update system settings (sepsis risk threshold, sustained hours, cooldown, stream speed).
Requires Admin role.

---

## Admin — Users

### GET `/api/admin/users`
List all users. Requires Admin role.

### GET `/api/admin/users/roles`
List available roles.

### POST `/api/admin/users`
Create a user. Requires Admin role.

### PUT `/api/admin/users/{user_id}`
Update a user. Requires Admin role. An admin cannot deactivate their own account.

### DELETE `/api/admin/users/{user_id}`
Delete a user. Requires Admin role. An admin cannot delete their own account.

---

## MLOps

### GET `/api/mlops/experiments`
Recent MLflow runs (parameters + metrics).

### GET `/api/mlops/registry`
Versions of the `sepsis-xgb-earlywarning` model from the MLflow Model Registry.

### GET `/api/mlops/pipeline/status`
Status of the Airflow DAG `sepsis_daily_retrain`.

### GET `/api/mlops/dataset/stats`
Dataset statistics (train/val/test row and patient counts).

### POST `/api/mlops/registry/{version}/promote`
Promote a model version to Production. Requires Admin role.

### POST `/api/mlops/registry/{version}/archive`
Archive a model version. Requires Admin role.

---

## Health

### GET `/api/health`
Liveness check.

---

## WebSocket

### WS `/ws/live?stay_id={stay_id}&token={jwt_token}`

The server pushes real-time updates for the subscribed stay:

**Prediction:**
```json
{
  "type": "prediction",
  "data": {
    "stay_id": "uuid",
    "hour": 34,
    "risk_score": 0.89,
    "risk_level": "HIGH"
  }
}
```

**Alert:**
```json
{
  "type": "alert",
  "data": {
    "alert_id": "uuid",
    "stay_id": "uuid",
    "status": "NEW",
    "severity": 0.85
  }
}
```

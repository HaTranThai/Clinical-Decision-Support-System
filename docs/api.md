# Tài liệu API — Hệ thống Cảnh báo sớm Nhiễm khuẩn huyết

URL gốc: `http://localhost:18800`

Mọi endpoint trừ `/api/auth/login` và `/api/health` đều yêu cầu header
`Authorization: Bearer <token>`. Tài liệu tương tác: `http://localhost:18800/docs`.

## Xác thực

### POST `/api/auth/login`
Đăng nhập và nhận JWT token.

**Body:**
```json
{ "username": "admin", "password": "admin123" }
```

**Phản hồi:**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### GET `/api/auth/me`
Lấy thông tin người dùng hiện tại.

---

## Tổng quan

### GET `/api/overview`
Bảng phân loại (triage board) — mỗi mục là một ca ICU đang hoạt động kèm nguy cơ mới nhất.

---

## Bệnh nhân

### GET `/api/patients`
Danh sách bệnh nhân. **Query:** `?search=<tên hoặc mã ngoài>`

### GET `/api/patients/{patient_id}`
Chi tiết bệnh nhân, gồm lịch sử các ca ICU.

### POST `/api/patients`
Tạo bệnh nhân. **Body:** `{ "name", "external_ref?", "age?", "gender?" }`

### PUT `/api/patients/{patient_id}`
Cập nhật bệnh nhân.

### POST `/api/patients/{patient_id}/stays`
Tạo ca ICU mới cho một bệnh nhân đã có. **Body:** `{ "source_record?" }`
(nếu bỏ trống, hệ thống tự sinh mã ca duy nhất `ICU-YYYYMMDD-XXXX`).

---

## Ca ICU

### GET `/api/stays`
Danh sách ca ICU. **Query:** `?status=RUNNING|ENDED&limit=50&offset=0`

### GET `/api/stays/{stay_id}`
Chi tiết một ca.

### POST `/api/stays`
Tạo bệnh nhân + ca ICU cùng lúc. **Body:** `{ "patient_name", "age?", "gender?", "source_record?" }`

### POST `/api/stays/{stay_id}/vitals`
Nạp một giờ chỉ số sinh tồn (đẩy vào Kafka `patient_vitals`).
**Body:** `{ "hour": <int>, "record": { ...chỉ số sinh tồn... } }`

### POST `/api/stays/{stay_id}/stop`
Kết thúc một ca ICU (trạng thái → `ENDED`).

### GET `/api/stays/{stay_id}/predictions`
Lịch sử dự đoán nguy cơ theo giờ của ca.

### GET `/api/stays/{stay_id}/alerts`
Các cảnh báo của ca.

---

## Cảnh báo

### GET `/api/alerts`
Danh sách cảnh báo kèm bộ lọc. **Query:** `?status=NEW|ACK|DISMISSED&...`

### GET `/api/alerts/{alert_id}`
Chi tiết cảnh báo kèm các hành động đã thực hiện.

### POST `/api/alerts/{alert_id}/ack`
Xác nhận (acknowledge) cảnh báo. **Body:** `{ "reason?", "note?" }`

### POST `/api/alerts/{alert_id}/dismiss`
Bỏ qua (dismiss) cảnh báo. **Body:** `{ "reason?", "note?" }`

---

## Phân tích

### GET `/api/analytics/alerts_hourly`
Số lượng cảnh báo theo từng giờ trong ngày.

### GET `/api/analytics/summary`
Thống kê tổng hợp (tổng cảnh báo, đã xác nhận, đã bỏ qua, ...).

---

## Quản trị — Cấu hình

### GET `/api/admin/settings`
Lấy cấu hình hệ thống. Yêu cầu vai trò Admin.

### PUT `/api/admin/settings`
Cập nhật cấu hình hệ thống (ngưỡng nguy cơ sepsis, số giờ duy trì, cooldown, tốc độ phát).
Yêu cầu vai trò Admin.

---

## Quản trị — Người dùng

### GET `/api/admin/users`
Danh sách tất cả người dùng. Yêu cầu vai trò Admin.

### GET `/api/admin/users/roles`
Danh sách các vai trò.

### POST `/api/admin/users`
Tạo người dùng. Yêu cầu vai trò Admin.

### PUT `/api/admin/users/{user_id}`
Cập nhật người dùng. Yêu cầu vai trò Admin. Admin không thể tự vô hiệu hóa tài khoản của mình.

### DELETE `/api/admin/users/{user_id}`
Xóa người dùng. Yêu cầu vai trò Admin. Admin không thể xóa tài khoản của chính mình.

---

## MLOps

### GET `/api/mlops/experiments`
Các run gần đây trên MLflow (tham số + chỉ số).

### GET `/api/mlops/registry`
Các version của model `sepsis-xgb-earlywarning` trong MLflow Model Registry.

### GET `/api/mlops/pipeline/status`
Trạng thái DAG Airflow `sepsis_daily_retrain`.

### GET `/api/mlops/dataset/stats`
Thống kê bộ dữ liệu (số dòng và số bệnh nhân của train/val/test).

### POST `/api/mlops/registry/{version}/promote`
Promote một version mô hình lên Production. Yêu cầu vai trò Admin.

### POST `/api/mlops/registry/{version}/archive`
Archive một version mô hình. Yêu cầu vai trò Admin.

---

## Kiểm tra sức khỏe

### GET `/api/health`
Kiểm tra hệ thống còn sống (liveness).

---

## WebSocket

### WS `/ws/live?stay_id={stay_id}&token={jwt_token}`

Server đẩy cập nhật realtime cho ca đang theo dõi:

**Dự đoán (prediction):**
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

**Cảnh báo (alert):**
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

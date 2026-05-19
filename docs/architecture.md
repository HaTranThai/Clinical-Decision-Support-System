# Kiến trúc Hệ thống — Cảnh báo sớm Nhiễm khuẩn huyết (Sepsis Early-Warning CDSS)

> Tài liệu kiến trúc đầy đủ. Đối tượng đọc: kỹ thuật (developer, DevOps) và người vận hành dự án.

---

## 1. Giới thiệu

### 1.1 Mục tiêu
Sepsis Early-Warning CDSS là hệ thống hỗ trợ quyết định lâm sàng (Clinical Decision Support
System) giúp **phát hiện sớm nguy cơ nhiễm khuẩn huyết (sepsis)** cho bệnh nhân hồi sức tích cực
(ICU). Hệ thống nhận chỉ số sinh tồn theo từng giờ, chạy mô hình học máy để ước lượng nguy cơ,
và phát cảnh báo cho nhân viên y tế **trước khi** bệnh trở nặng.

### 1.2 Bài toán
Sepsis là nguyên nhân tử vong hàng đầu trong ICU; phát hiện sớm vài giờ có thể thay đổi kết cục
điều trị. Bộ dữ liệu **PhysioNet/CinC Challenge 2019** cung cấp ~40.000 bệnh nhân ICU, mỗi bệnh
nhân là một file `.psv` (1 dòng = 1 giờ nằm viện, 41 cột chỉ số). Nhãn `SepsisLabel` được đặt
trước thời điểm khởi phát lâm sàng 6 giờ → mô hình học cách "cảnh báo sớm".

### 1.3 Đặc điểm hệ thống
- **Kiến trúc microservices**, giao tiếp bất đồng bộ qua Apache Kafka
- **Xử lý theo luồng (streaming)**: dữ liệu chảy qua từng service, không xử lý theo lô
- **MLOps đầy đủ**: huấn luyện tái lập được (DVC), tự động hóa (Airflow), quản lý phiên bản
  mô hình (MLflow Model Registry), cơ chế champion/challenger
- **Thời gian thực**: kết quả đẩy xuống giao diện qua WebSocket

---

## 2. Sơ đồ kiến trúc tổng thể

```
                        ┌──────────────────────────────────────────────────────────┐
                        │                    NGUỒN DỮ LIỆU                          │
                        │   Replay Producer  ──hoặc──  tools/push_patient.py         │
                        │   (đọc file .psv PhysioNet/CinC 2019)                      │
                        └───────────────────────────┬──────────────────────────────┘
                                                    │ patient_vitals
                                                    ▼
   ┌─────────────────────────────────────── APACHE KAFKA ───────────────────────────────────────┐
   │   patient_vitals  │  patient_features  │  sepsis_prediction  │  sepsis_alert               │
   └────┬─────────────────────┬──────────────────────┬───────────────────────┬─────────────────┘
        │                     │                      │                       │
        ▼                     ▼                      ▼                       ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Preprocess    │   │ Inference        │   │ Alert Engine     │   │ FastAPI Backend  │
│ Buffer Service│──►│ Service          │──►│ Service          │──►│ (Kafka consumer) │
│ trích đặc trưng│   │ XGBoost suy luận │   │ luật cảnh báo    │   │ + REST + WS      │
└───────────────┘   └──────────────────┘   └────────┬─────────┘   └────────┬─────────┘
                                                     │                     │
                                                     ▼                     ▼ WebSocket
                                            ┌──────────────────┐   ┌──────────────────┐
                                            │   PostgreSQL     │◄──│  React Frontend  │
                                            │  (lưu trạng thái)│   │  (giao diện web) │
                                            └──────────────────┘   └──────────────────┘

   ┌────────────────────────── TẦNG MLOPS (offline) ──────────────────────────┐
   │   DVC pipeline  ──/──  Airflow DAG  ──►  MLflow (tracking + registry)     │
   │   prepare_data → train → evaluate → compare_and_register                 │
   │                              │                                          │
   │                              └──► sepsis_model.json ──► Inference Service│
   └───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Luồng dữ liệu đầu-cuối (end-to-end)

1. **Nạp dữ liệu** — Replay Producer (hoặc script `push_patient.py`, hoặc API backend) đọc chỉ số
   sinh tồn một giờ của bệnh nhân và gửi vào topic `patient_vitals`.
2. **Trích đặc trưng** — Preprocess Buffer Service nhận chỉ số thô, giữ lịch sử theo từng ca,
   tính 114 đặc trưng (forward-fill + thống kê cửa sổ 6 giờ + độ mới), gửi vào `patient_features`.
3. **Suy luận** — Inference Service nạp vector đặc trưng vào mô hình XGBoost, tính điểm nguy cơ
   sepsis (0–1) và mức nguy cơ (LOW/MEDIUM/HIGH), gửi vào `sepsis_prediction`.
4. **Sinh cảnh báo** — Alert Engine Service đọc dự đoán, áp luật cửa sổ trượt; nếu nguy cơ vượt
   ngưỡng đủ lâu thì phát một cảnh báo vào `sepsis_alert` và lưu DB.
5. **Lưu trữ + hiển thị** — Backend tiêu thụ `sepsis_prediction` và `sepsis_alert`, ghi PostgreSQL
   và đẩy realtime xuống giao diện qua WebSocket.
6. **Bác sĩ xử lý** — Trên web, nhân viên y tế xem nguy cơ, xác nhận (ACK) hoặc bỏ qua (DISMISS)
   cảnh báo; hành động được ghi vào bảng `alert_action`.

---

## 4. Apache Kafka — Hàng đợi tin nhắn

Kafka là xương sống giao tiếp; các service không gọi trực tiếp lẫn nhau mà trao đổi qua topic.
Ưu điểm: tách rời (decoupling), chịu lỗi, có thể mở rộng từng service độc lập.

| Topic | Bên gửi | Bên nhận | Nội dung |
|-------|---------|----------|----------|
| `patient_vitals` | Replay Producer / Backend | Preprocess Buffer | Chỉ số sinh tồn thô 1 giờ của một ca ICU |
| `patient_features` | Preprocess Buffer | Inference Service | Vector 114 đặc trưng đã trích xuất |
| `sepsis_prediction` | Inference Service | Alert Engine, Backend | Điểm nguy cơ + mức nguy cơ theo giờ |
| `sepsis_alert` | Alert Engine | Backend (WebSocket) | Sự kiện cảnh báo nhiễm khuẩn huyết |

---

## 5. Chi tiết các service

### 5.1 Replay Producer (`services/replay-producer`)
- Đọc file `.psv` của PhysioNet/CinC 2019 (1 dòng = 1 giờ ICU, 41 cột chỉ số)
- Tạo bản ghi `patient` + `icu_stay` trong DB, rồi phát chỉ số từng giờ vào `patient_vitals`
- Mô phỏng tốc độ phát theo thời gian thực (cấu hình `HOUR_INTERVAL_SEC`)
- Là service tùy chọn — dùng để tự động sinh dữ liệu demo

### 5.2 Preprocess Buffer Service (`services/preprocess-buffer-service`)
- Tiêu thụ `patient_vitals`, giữ **buffer lịch sử** chỉ số theo từng ca ICU
- `features.py` trích **114 đặc trưng**:
  - Tín hiệu gốc đã forward-fill (điền giá trị thiếu bằng giá trị gần nhất)
  - Thống kê cửa sổ trượt 6 giờ (trung bình, độ lệch chuẩn, min, max...)
  - Chỉ báo độ mới (recency) — đã bao lâu kể từ lần đo gần nhất
- Gửi vector đặc trưng vào `patient_features`

### 5.3 Inference Service (`services/inference-service`)
- `model_loader.py` nạp mô hình XGBoost từ file cục bộ `sepsis_model.json` **hoặc** từ URI
  artifact MLflow (`runs:/`, `models:/`, `mlflow-artifacts:/`)
- `infer.py` chạy suy luận: vector 114 đặc trưng → điểm nguy cơ (0–1)
- Quy đổi mức nguy cơ: LOW / MEDIUM / HIGH theo ngưỡng
- Gửi kết quả vào `sepsis_prediction`

### 5.4 Alert Engine Service (`services/alert-engine-service`)
- `state.py` giữ trạng thái lịch sử nguy cơ theo từng ca (deque)
- `rules.py` áp luật cảnh báo:
  - Phát cảnh báo khi nguy cơ ≥ `ALERT_RISK_THRESHOLD` (mặc định **0.6**)
  - Trong `SUSTAINED_HOURS` (mặc định **3**) giờ **liên tục**
  - Áp `COOLDOWN_HOURS` (mặc định **12** giờ) giữa các cảnh báo để tránh quá tải cảnh báo
- `db_writer.py` lưu cảnh báo vào PostgreSQL; phát sự kiện vào `sepsis_alert`

### 5.5 FastAPI Backend (`backend/app`)
Cấu trúc:
- `api/routes/` — các nhóm endpoint: `auth`, `users`, `patients`, `stays`, `overview`,
  `alerts`, `settings`, `analytics`, `mlops`, `health`
- `api/ws/live.py` — WebSocket gateway, đẩy realtime theo từng ca
- `services/kafka_consumer.py` — tiêu thụ `patient_vitals`, `sepsis_prediction`, `sepsis_alert`;
  ghi DB (dự đoán dùng UPSERT theo `(stay_id, hour)` để tránh trùng)
- `services/kafka_producer.py` — phát `patient_vitals` khi nạp chỉ số qua REST API
- `services/ws_broadcaster.py` — quản lý kết nối WebSocket, broadcast theo ca
- `core/security.py` — JWT, băm mật khẩu bcrypt; `core/config.py` — cấu hình; `db/` — ORM + session

### 5.6 React Frontend (`frontend/src`)
Các trang (`pages/`):
- `OverviewPage` — bảng phân loại (triage board), nguy cơ theo từng ca, làm mới 5 giây
- `LiveMonitorPage` — màn hình theo dõi: đồng hồ nguy cơ, đường diễn tiến, chỉ số sinh tồn
- `PatientsPage` / `PatientDetailPage` — quản lý bệnh nhân, lịch sử ca ICU, tạo ca mới
- `SessionsPage` / `SessionDetailPage` — danh sách & chi tiết ca ICU
- `AlertsPage` — danh sách cảnh báo, xác nhận/bỏ qua
- `AnalyticsPage` — thống kê
- `MLOpsDashboardPage` / `ExperimentsPage` / `ModelRegistryPage` — quan sát MLOps
- `AdminSettingsPage` / `AdminUsersPage` — quản trị
- `stores/liveMonitorStore.ts` — Zustand store, gộp dữ liệu realtime theo giờ

---

## 6. Mô hình dữ liệu (PostgreSQL)

```
        role ──< user ──< alert_action >── alert
                  │                          │
                  └──< setting_version       │
                              │              │
                  system_setting             │
                                              │
   patient ──< icu_stay ──< sepsis_prediction │
                       └──< alert ────────────┘
        model_version ──< sepsis_prediction
        model_version ──< alert
```

| Bảng | Vai trò |
|------|---------|
| `role` | Vai trò người dùng (admin, clinician...) |
| `user` | Tài khoản người dùng, gắn `role`, mật khẩu băm bcrypt |
| `patient` | Bệnh nhân (tên, mã ngoài, tuổi, giới tính) |
| `icu_stay` | Một ca/phiên nằm ICU của bệnh nhân; trạng thái RUNNING/ENDED, `source_record` là mã ca |
| `sepsis_prediction` | Dự đoán nguy cơ theo từng giờ của một ca (`hour`, `risk_score`, `risk_level`) |
| `alert` | Cảnh báo sepsis của một ca; `severity`, `status` (NEW/ACK/DISMISSED), `evidence_json` |
| `alert_action` | Hành động của người dùng lên cảnh báo (ACK/DISMISS) kèm lý do, ghi chú |
| `model_version` | Phiên bản mô hình đã triển khai, `artifact_uri`, `metrics_json` |
| `system_setting` | Cấu hình hệ thống dạng key–value (JSON) |
| `setting_version` | Lịch sử thay đổi cấu hình (ai sửa, khi nào, giá trị cũ) — phục vụ audit |

Quan hệ chính: `patient` 1–N `icu_stay`; `icu_stay` 1–N `sepsis_prediction` và 1–N `alert`;
`alert` 1–N `alert_action`.

---

## 7. Mô hình Machine Learning

| Hạng mục | Chi tiết |
|----------|----------|
| Thuật toán | XGBoost (`binary:logistic`) — phân loại nhị phân nguy cơ sepsis |
| Đặc trưng đầu vào | 114 đặc trưng kỹ thuật từ 41 cột chỉ số gốc |
| Kỹ thuật đặc trưng | Forward-fill tín hiệu + thống kê cửa sổ trượt 6 giờ + chỉ báo độ mới |
| Mất cân bằng lớp | Dùng `scale_pos_weight` (tỷ lệ dương ~1.8%) |
| Chia dữ liệu | Theo bệnh nhân, phân tầng theo nhãn, tất định — 70/15/15 |
| Chỉ số đánh giá | AUROC (~0.847), AUPRC (~0.126), Sensitivity, Specificity |
| Cổng chất lượng | `min_auroc` (mặc định 0.75) — không đạt thì không promote |

Việc chia dữ liệu ở **mức bệnh nhân** (mỗi file `.psv` đi trọn vào một split) tránh rò rỉ giữa
các giờ của cùng một người. Khi demo nên dùng bệnh nhân tập test (`data/splits/test/`).

---

## 8. Tầng MLOps

### 8.1 Pipeline 4 bước
```
prepare_data  →  train  →  evaluate  →  compare_and_register
(trích đặc trưng)  (XGBoost)  (test set)   (register + promote)
```

### 8.2 Hai cách chạy pipeline
- **DVC** (`dvc.yaml`) — chạy thủ công, tái lập: `dvc repro`
- **Airflow** (DAG `sepsis_daily_retrain`) — tự động hằng ngày lúc 02:00; mỗi bước chạy như một
  tiến trình con độc lập

### 8.3 MLflow
- **Tracking**: ghi tham số, chỉ số, checkpoint của mỗi lần huấn luyện
- **Model Registry**: quản lý phiên bản mô hình `sepsis-xgb-earlywarning`
- **Champion/Challenger**: model mới (challenger) chỉ thay model đang chạy (champion) khi
  AUROC tốt hơn và đạt `min_auroc`; nếu không thì bị archive

### 8.4 Quan sát trên giao diện
Backend có nhóm endpoint `/api/mlops/*` proxy tới MLflow và Airflow; frontend hiển thị
experiments, model registry, trạng thái pipeline tái huấn luyện.

---

## 9. Cổng dịch vụ (host)

| Dịch vụ | Cổng host | Cổng container | Ghi chú |
|---------|-----------|----------------|---------|
| Frontend | 13000 | 3000 | Ứng dụng web |
| Backend (FastAPI) | 18800 | 8000 | REST API + WebSocket |
| MLflow | 15000 | 5000 | Tracking + Registry UI |
| Airflow webserver | 18080 | 8080 | Giao diện quản lý DAG |
| PostgreSQL | 15432 | 5432 | Cơ sở dữ liệu |
| Kafka | 9092 | 9092 | Hàng đợi tin nhắn |

---

## 10. Cấu trúc thư mục

```
CNM-Final-Project/
├── airflow/              # Dockerfile + DAG sepsis_daily_retrain
│   └── dags/
├── backend/              # FastAPI backend
│   └── app/
│       ├── api/routes/   # các endpoint REST
│       ├── api/ws/       # WebSocket
│       ├── core/         # config, security, logging
│       ├── db/           # ORM models, session
│       ├── schemas/      # Pydantic schemas
│       └── services/     # Kafka consumer/producer, WS broadcaster
├── frontend/             # React + Vite + Ant Design
│   └── src/{pages,components,api,stores,types}
├── services/             # các microservice streaming
│   ├── replay-producer/
│   ├── preprocess-buffer-service/
│   ├── inference-service/
│   ├── alert-engine-service/
│   └── common/           # code dùng chung (kafka, config, schemas)
├── mlops/                # gói sepsis_mlops (pipeline ML)
│   └── src/sepsis_mlops/
├── infra/                # init script cho Kafka, PostgreSQL
├── tools/                # push_patient.py, organize_splits.py
├── docs/                 # tài liệu (file này)
├── Data/sepsis-2019/     # dữ liệu PhysioNet (gitignore)
├── data/                 # parquet đã xử lý, splits (gitignore)
├── docker-compose.yml    # định nghĩa toàn bộ hạ tầng
├── params.yaml           # tham số pipeline ML
└── dvc.yaml              # DAG của DVC
```

---

## 11. Triển khai

Toàn bộ hệ thống đóng gói bằng **Docker Compose** (`docker-compose.yml`), gồm các nhóm service:
- **Hạ tầng**: `postgres`, `kafka`
- **Streaming**: `replay-producer`, `preprocess-buffer`, `inference-service`, `alert-engine`
- **Ứng dụng**: `backend`, `frontend`
- **MLOps**: `mlflow`, `airflow-init`, `airflow-webserver`, `airflow-scheduler`

Khởi động: `docker compose up -d`. Chi tiết vận hành xem `docs/runbook.md`.

---

## 12. Công nghệ sử dụng

| Tầng | Công nghệ |
|------|-----------|
| Frontend | React 18, TypeScript, Vite, Ant Design, ECharts, TanStack Query, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, JWT |
| Service streaming | Python 3.11, XGBoost, pandas, NumPy, confluent-kafka |
| Cơ sở dữ liệu | PostgreSQL |
| Hàng đợi tin nhắn | Apache Kafka |
| MLOps | DVC, MLflow, Apache Airflow |
| Hạ tầng | Docker, Docker Compose |

---

## 13. Bảo mật

- Xác thực bằng **JWT**; mật khẩu băm bằng **bcrypt**
- **Phân quyền theo vai trò (RBAC)**: endpoint quản trị chỉ dành cho Admin
- Admin **không thể tự** vô hiệu hóa/xóa tài khoản của chính mình; chỉ Admin được quản lý
  tài khoản người khác
- Mọi thay đổi cấu hình hệ thống được ghi lịch sử (`setting_version`) phục vụ kiểm toán
- CORS giới hạn theo origin của frontend
- Lỗi hệ thống không lộ stack trace ra phía client

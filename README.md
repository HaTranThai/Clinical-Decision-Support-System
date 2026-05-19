# 🏥 Sepsis Early-Warning CDSS

### Hệ thống AI thời gian thực cảnh báo sớm Nhiễm khuẩn huyết trong ICU

Hệ thống hỗ trợ quyết định lâm sàng (Clinical Decision Support System) ứng dụng học máy để
**dự đoán nguy cơ nhiễm khuẩn huyết (sepsis)** cho bệnh nhân hồi sức tích cực, cảnh báo sớm
cho nhân viên y tế **trước khi** bệnh biểu hiện rõ trên lâm sàng.

Dự án xây dựng theo **kiến trúc microservices**, xử lý dữ liệu **streaming thời gian thực**
qua Apache Kafka, kèm quy trình **MLOps** đầy đủ (DVC · Airflow · MLflow).

---

## 📑 Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Giao diện hệ thống](#2-giao-diện-hệ-thống)
3. [Kiến trúc](#3-kiến-trúc)
4. [Công nghệ sử dụng](#4-công-nghệ-sử-dụng)
5. [Cấu trúc thư mục](#5-cấu-trúc-thư-mục)
6. [Yêu cầu hệ thống](#6-yêu-cầu-hệ-thống)
7. [Cài đặt & Chạy](#7-cài-đặt--chạy)
8. [Hướng dẫn sử dụng & Demo](#8-hướng-dẫn-sử-dụng--demo)
9. [Quy trình MLOps](#9-quy-trình-mlops)
10. [Cổng dịch vụ](#10-cổng-dịch-vụ)
11. [Tài liệu](#11-tài-liệu)

---

## 1. Tổng quan

**Nhiễm khuẩn huyết (sepsis)** là phản ứng mất kiểm soát của cơ thể trước nhiễm trùng, gây
suy đa cơ quan và là một trong những nguyên nhân tử vong hàng đầu tại ICU. Mỗi giờ chậm trễ
trong chẩn đoán làm tăng đáng kể tỷ lệ tử vong — do đó **phát hiện sớm** có ý nghĩa sống còn.

Hệ thống hoạt động như một "trợ lý AI" chạy nền trong ICU:

1. Mỗi **giờ**, nhận chỉ số sinh tồn của bệnh nhân (mạch, huyết áp, nhiệt độ, xét nghiệm…).
2. Trích xuất **114 đặc trưng** chuỗi thời gian.
3. Mô hình **XGBoost** tính **điểm nguy cơ sepsis** (0–1) và mức nguy cơ (LOW/MEDIUM/HIGH).
4. **Bộ luật cảnh báo** phát cảnh báo khi nguy cơ ≥ 0.6 liên tục 3 giờ (cooldown 12 giờ).
5. **Giao diện web** hiển thị nguy cơ và cảnh báo theo thời gian thực cho bác sĩ.

- **Dữ liệu:** PhysioNet/CinC Challenge 2019 (~40.336 bệnh nhân ICU).
- **Hiệu năng mô hình:** AUROC ≈ 0.847 trên tập kiểm thử giữ riêng theo bệnh nhân.

### Tính năng chính

- 🩺 **Theo dõi thời gian thực** — bảng phân loại (triage), đồng hồ nguy cơ, đường diễn tiến.
- 🔔 **Cảnh báo sớm sepsis** — luật cửa sổ trượt + cooldown chống quá tải cảnh báo.
- 👥 **Quản lý bệnh nhân & ca ICU** — tạo, theo dõi, kết thúc ca giám sát.
- 📊 **Phân tích & thống kê** — biểu đồ cảnh báo, tổng quan ICU.
- 🤖 **MLOps** — huấn luyện tái lập (DVC), tự động hóa (Airflow), quản lý mô hình (MLflow).
- 🔐 **Phân quyền** — xác thực JWT, vai trò Clinician/Admin.

---

## 2. Giao diện hệ thống

| | |
|---|---|
| **Bảng phân loại (Triage Board)** | **Màn hình theo dõi bệnh nhân** |
| ![Triage Board](docs/picture/1-9.png) | ![Patient Monitor](docs/picture/1-10.png) |
| **Danh sách cảnh báo Sepsis** | **Bảng điều khiển MLOps** |
| ![Sepsis Alerts](docs/picture/1-11.png) | ![MLOps Dashboard](docs/picture/2-5.png) |

---

## 3. Kiến trúc

Hệ thống gồm hai luồng: **luồng phục vụ trực tuyến (online serving)** xử lý dữ liệu bệnh nhân
theo thời gian thực, và **luồng MLOps (offline)** huấn luyện — quản lý mô hình.

![Kiến trúc hệ thống](docs/picture/architecture.png)

### Luồng dữ liệu thời gian thực

```
Nguồn dữ liệu → patient_vitals → Preprocess Buffer → patient_features
   → Inference Service → sepsis_prediction → Alert Engine → sepsis_alert
   → Backend (lưu DB + đẩy WebSocket) → Frontend
```

Mọi service giao tiếp **bất đồng bộ qua Apache Kafka** với 4 topic:
`patient_vitals` · `patient_features` · `sepsis_prediction` · `sepsis_alert`.

### Các microservice

| Service | Vai trò |
|---------|---------|
| **replay-producer** | Phát lại dữ liệu `.psv` mô phỏng thiết bị theo dõi ICU |
| **preprocess-buffer-service** | Đệm lịch sử theo ca, trích xuất 114 đặc trưng |
| **inference-service** | Nạp mô hình XGBoost, tính điểm nguy cơ sepsis |
| **alert-engine-service** | Áp luật cảnh báo, sinh cảnh báo sepsis |
| **backend** | FastAPI: REST API, WebSocket, Kafka consumer, ORM |
| **frontend** | Giao diện web React |
| **kafka / postgres** | Hàng đợi tin nhắn / Cơ sở dữ liệu |
| **mlflow / airflow** | Theo dõi thí nghiệm & registry / Tự động tái huấn luyện |

### Sơ đồ triển khai

![Triển khai Docker Compose](docs/picture/2-1.png)

---

## 4. Công nghệ sử dụng

| Tầng | Công nghệ |
|------|-----------|
| **Frontend** | React 18 · TypeScript · Vite · Ant Design · ECharts · TanStack Query · Zustand |
| **Backend** | FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 · JWT · WebSocket |
| **Streaming** | Python 3.11 · Apache Kafka · confluent-kafka |
| **Machine Learning** | XGBoost · pandas · NumPy · scikit-learn |
| **MLOps** | DVC · MLflow · Apache Airflow |
| **Cơ sở dữ liệu** | PostgreSQL 15 |
| **Hạ tầng** | Docker · Docker Compose |

---

## 5. Cấu trúc thư mục

```
CNM-Final-Project/
├── airflow/                  DAG sepsis_daily_retrain + Dockerfile
│   └── dags/
├── backend/                  Backend FastAPI
│   └── app/{api,core,db,schemas,services}
├── frontend/                 Giao diện web React + TypeScript
│   └── src/{pages,components,api,stores,types}
├── services/                 Các microservice streaming
│   ├── replay-producer/
│   ├── preprocess-buffer-service/
│   ├── inference-service/
│   ├── alert-engine-service/
│   └── common/               Code dùng chung (kafka, config, schemas)
├── mlops/                    Gói sepsis_mlops (pipeline học máy)
│   └── src/sepsis_mlops/
├── infra/                    Script khởi tạo Kafka, PostgreSQL
├── tools/                    push_patient.py, organize_splits.py
├── docs/                     Tài liệu dự án + báo cáo + hình ảnh
├── Data/sepsis-2019/         Dữ liệu PhysioNet (gitignore)
├── docker-compose.yml        Định nghĩa toàn bộ hạ tầng
├── params.yaml               Tham số pipeline học máy
├── dvc.yaml                  Định nghĩa pipeline DVC
└── download_sepsis.py        Script tải dữ liệu PhysioNet
```

---

## 6. Yêu cầu hệ thống

- **Docker** và **Docker Compose** đã cài đặt.
- **RAM** khuyến nghị ≥ 8 GB (chạy đầy đủ ~11 container).
- **Dữ liệu** PhysioNet/CinC 2019 — nếu chưa có, tải bằng:
  ```bash
  python download_sepsis.py
  ```
  Lệnh này tải ~40.000 file `.psv` vào `Data/sepsis-2019/`.

---

## 7. Cài đặt & Chạy

### 7.1. Cấu hình

```bash
cd CNM-Final-Project
cp .env.example .env          # giá trị mặc định đã chạy được cho môi trường local
```

### 7.2. Khởi động hệ thống

```bash
# Bật toàn bộ hệ thống
docker compose up -d

# Hoặc chỉ bật phần lõi (theo dõi realtime, nhẹ RAM hơn)
docker compose up -d postgres kafka mlflow backend frontend \
  preprocess-buffer inference-service alert-engine
```

Lần đầu chạy mất vài phút để Docker build image. Kiểm tra trạng thái:

```bash
docker compose ps            # tất cả service nên ở trạng thái "running"
```

### 7.3. Truy cập

| Giao diện | Địa chỉ | Tài khoản |
|-----------|---------|-----------|
| **Ứng dụng web** | http://localhost:13000 | `admin` / `admin123` |
| MLflow | http://localhost:15000 | — |
| Airflow | http://localhost:18080 | `admin` / `admin123` |
| API docs (Swagger) | http://localhost:18800/docs | — |

> **Dùng VS Code Remote / máy chủ từ xa:** mở tab **PORTS** → "Forward a Port" → nhập `13000`
> trước khi mở `localhost:13000`.

### 7.4. Dừng hệ thống

```bash
docker compose stop                       # dừng container
docker compose down                       # dừng & xóa container
docker compose down -v                    # xóa cả volume (reset toàn bộ dữ liệu)
```

---

## 8. Hướng dẫn sử dụng & Demo

### 8.1. Bơm dữ liệu một bệnh nhân

Dùng script `tools/push_patient.py` để đưa dữ liệu một bệnh nhân vào hệ thống. Nên chọn bệnh
nhân thuộc **tập test** (mô hình chưa học → kết quả trung thực):

```bash
python tools/push_patient.py \
  --patient-name "Nguyen Van Demo" --age 67 --gender M \
  --psv "data/splits/test/p017347.psv" \
  --interval 5 --stop
```

| Tham số | Ý nghĩa |
|---------|---------|
| `--patient-name` | Tên bệnh nhân (hiển thị trên web) |
| `--psv` | File `.psv` nguồn — đẩy từng giờ dữ liệu |
| `--interval` | Số giây giữa mỗi giờ (mô phỏng realtime) |
| `--hours N` | Chỉ đẩy N giờ đầu |
| `--stay-id` | Đẩy vào ca đã có sẵn thay vì tạo ca mới |
| `--stop` | Tự kết thúc ca (ENDED) sau khi đẩy xong |

> Cần thư viện `requests`: `pip install requests`.

### 8.2. Xem trên web

Mở http://localhost:13000, đăng nhập, rồi:

- **Triage Board** (`/overview`) — toàn bộ ca ICU theo mức nguy cơ, làm mới mỗi 5 giây.
- **Patient Monitor** (`/live`) — đồng hồ nguy cơ, đường diễn tiến, chỉ số sinh tồn, cảnh báo.
- **Sepsis Alerts** (`/alerts`) — danh sách cảnh báo; xác nhận (ACK) / bỏ qua (DISMISS).
- **Patients** (`/patients`) — quản lý bệnh nhân và lịch sử ca ICU.
- **MLOps** (`/mlops`) — thí nghiệm, model registry, trạng thái pipeline.

![Màn hình Đăng nhập](docs/picture/1-8.png)

---

## 9. Quy trình MLOps

Pipeline huấn luyện gồm **4 bước**, chạy được thủ công (DVC) hoặc tự động theo lịch (Airflow):

```
prepare_data → train → evaluate → compare_and_register
```

| Bước | Mô tả |
|------|-------|
| `prepare_data` | Trích đặc trưng, chia train/val/test theo bệnh nhân (70/15/15) |
| `train` | Huấn luyện XGBoost (scale_pos_weight, early stopping), log lên MLflow |
| `evaluate` | Đánh giá AUROC/AUPRC trên tập test giữ riêng |
| `compare_and_register` | So champion/challenger, gate `min_auroc`, đăng ký Model Registry |

- **DAG Airflow** `sepsis_daily_retrain` tự chạy hằng ngày lúc 02:00.
- **MLflow** lưu thí nghiệm, chỉ số và quản lý phiên bản mô hình theo cơ chế champion/challenger.

Chạy thủ công bằng DVC:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e mlops
export MLFLOW_TRACKING_URI=http://localhost:15000
dvc repro
```

Tham số huấn luyện (`max_depth`, `eta`, tỷ lệ chia dữ liệu…) khai báo trong `params.yaml`.

---

## 10. Cổng dịch vụ

| Dịch vụ | Cổng host | Cổng container |
|---------|-----------|----------------|
| Frontend | 13000 | 3000 |
| Backend (FastAPI) | 18800 | 8000 |
| MLflow | 15000 | 5000 |
| Airflow webserver | 18080 | 8080 |
| PostgreSQL | 15432 | 5432 |
| Kafka | 9092 | 9092 |

---

## 11. Tài liệu

Tài liệu chi tiết trong thư mục [`docs/`](docs/):

- [`architecture.md`](docs/architecture.md) — Kiến trúc hệ thống đầy đủ
- [`mlops.md`](docs/mlops.md) — Quy trình MLOps
- [`runbook.md`](docs/runbook.md) — Sổ tay vận hành
- [`api.md`](docs/api.md) — Tài liệu REST API & WebSocket
- [`BaoCao-CNM.docx`](docs/) — Báo cáo đồ án đầy đủ

---

## Thuật ngữ

| Từ | Nghĩa |
|----|-------|
| **Sepsis** | Nhiễm khuẩn huyết — phản ứng nguy hiểm của cơ thể với nhiễm trùng |
| **ICU** | Khoa Hồi sức tích cực |
| **CDSS** | Hệ thống hỗ trợ quyết định lâm sàng |
| **XGBoost** | Mô hình học máy boosting trên cây quyết định |
| **AUROC** | Chỉ số đo độ chính xác mô hình (0.5 = đoán mò, 1.0 = hoàn hảo) |
| **Kafka** | Hàng đợi tin nhắn truyền dữ liệu streaming giữa các service |
| **MLOps** | Quy trình tự động hóa huấn luyện, kiểm thử, triển khai mô hình |
| **champion / challenger** | Mô hình đang phục vụ (champion) vs mô hình mới (challenger) |

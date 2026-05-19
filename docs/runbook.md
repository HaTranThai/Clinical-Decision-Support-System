# Sổ tay vận hành — Hệ thống Cảnh báo sớm Nhiễm khuẩn huyết

## Điều kiện cần

- Đã cài Docker & Docker Compose
- Bộ dữ liệu PhysioNet/CinC Challenge 2019 đặt tại `Data/sepsis-2019/training_setA` và `training_setB`
- Có file model phục vụ `services/inference-service/artifacts/sepsis_model.json`, hoặc chạy
  pipeline MLOps để tạo ra

## Cài đặt

### 1. Cấu hình

```bash
cd CNM-Final-Project
cp .env.example .env
# Sửa .env nếu cần (giá trị mặc định đã chạy được cho môi trường local)
```

### 2. Đặt dữ liệu

Copy bộ dữ liệu PhysioNet/CinC 2019 theo cấu trúc:

```text
Data/sepsis-2019/training_setA/p000001.psv
Data/sepsis-2019/training_setB/p100001.psv
...
```

Để huấn luyện và promote mô hình cục bộ, xem `docs/mlops.md`.

### 3. Build & khởi động

```bash
docker compose up -d
```

Các service lõi: `postgres`, `kafka`, `mlflow`, `backend`, `frontend`,
`preprocess-buffer`, `inference-service`, `alert-engine`.
Service MLOps: `airflow-init` (chạy một lần), `airflow-webserver`, `airflow-scheduler`.
`replay-producer` là tùy chọn — chỉ bật khi muốn tự động phát dữ liệu bệnh nhân demo.

### 4. Các địa chỉ truy cập

| Giao diện | URL | Tài khoản |
|-----------|-----|-----------|
| Ứng dụng web | http://localhost:13000 | admin / admin123 |
| MLflow | http://localhost:15000 | — |
| Airflow | http://localhost:18080 | admin / admin123 |
| Backend API | http://localhost:18800 | JWT |

## Luồng demo

### Bước 1: Đăng nhập
Mở http://localhost:13000 → đăng nhập `admin` / `admin123`.

### Bước 2: Bơm dữ liệu một bệnh nhân

Dùng bệnh nhân trong tập test (mô hình chưa từng học — demo trung thực):

```bash
python tools/push_patient.py \
  --patient-name "Demo Test Patient" \
  --psv "data/splits/test/p017347.psv" \
  --interval 5 --stop
```

Script sẽ đăng nhập, tạo bệnh nhân + ca ICU, rồi bơm chỉ số sinh tồn theo từng giờ.

### Bước 3: Theo dõi realtime
- **Triage Board** (`/overview`) — nguy cơ theo từng ca, làm mới mỗi 5 giây
- **Patient Monitor** (`/live`) — đồng hồ nguy cơ, đường diễn tiến nguy cơ, chỉ số sinh tồn, cảnh báo
- **ICU Stays** (`/stays`) — danh sách ca; nút **Stop** để kết thúc một ca
- **Sepsis Alerts** (`/alerts`) — cảnh báo phát ra khi nguy cơ duy trì trên ngưỡng
- **Analytics** (`/analytics`) — thống kê tổng hợp

### Bước 4: Quản lý bệnh nhân
**Patients** → mở một bệnh nhân → **+ New ICU Stay** để thêm phiên theo dõi mới.

### Bước 5: MLOps
- **MLOps → Dashboard / Experiments / Model Registry** trong ứng dụng web
- Giao diện MLflow: http://localhost:15000
- Giao diện Airflow: http://localhost:18080 — DAG `sepsis_daily_retrain`

## Xử lý sự cố

### Kafka chưa sẵn sàng
Các service có thể khởi động lại vài lần trong lúc Kafka khởi tạo. Đây là hiện tượng bình thường.
Log `Unknown topic or partition` ở lần chạy đầu là vô hại — topic được tạo tự động khi có message
đầu tiên.

### Không có dự đoán / không thấy nguy cơ trên màn hình theo dõi
- Kiểm tra file model phục vụ tồn tại: `services/inference-service/artifacts/sepsis_model.json`
- Xem log inference-service: `docker compose logs inference-service`

### Log task Airflow báo lỗi 403
Webserver và scheduler phải dùng chung `AIRFLOW__WEBSERVER__SECRET_KEY` (đã đặt trong docker-compose).

### Hết RAM khi huấn luyện
Huấn luyện ngốn nhiều RAM. Giải phóng RAM bằng cách tạm dừng các container không cần thiết, hoặc
giảm `n_workers` trong `prepare_data`.

### Sự cố cơ sở dữ liệu
Khởi tạo lại toàn bộ (xóa DB, MLflow và volume Airflow):
```bash
docker compose down -v
docker compose up -d
```

## Dừng hệ thống

```bash
docker compose stop                                       # dừng container
docker compose stop airflow-webserver airflow-scheduler   # chỉ dừng Airflow (tiết kiệm RAM)
docker compose down                                       # dừng & xóa container
docker compose down -v                                    # xóa cả volume (reset toàn bộ dữ liệu)
```

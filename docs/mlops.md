# Quy trình MLOps

Dự án tách riêng phần phục vụ trực tuyến (online serving) và các thao tác mô hình offline.
Cùng một pipeline có thể chạy thủ công (DVC) hoặc theo lịch (Airflow).

## Luồng xử lý

```text
File .psv của PhysioNet/CinC 2019
 -> prepare_data         (trích đặc trưng, chia train/val/test theo bệnh nhân)
 -> train                (huấn luyện XGBoost challenger, log lên MLflow)
 -> evaluate             (đánh giá chỉ số trên tập test giữ riêng)
 -> compare_and_register (kiểm soát bằng min_auroc, register + promote trong MLflow Model Registry)
 -> services/inference-service/artifacts/sepsis_model.json
 -> pipeline phục vụ realtime
```

## Cách chia dữ liệu

Việc chia dữ liệu thực hiện ở **mức bệnh nhân** (mỗi file `.psv` đi trọn vẹn vào một trong
train/val/test), phân tầng (stratified) theo nhãn nhiễm khuẩn huyết, và có tính tất định
(`random_seed` trong `params.yaml`). Tỷ lệ mặc định là 70 / 15 / 15. Cách này tránh rò rỉ dữ liệu
giữa các giờ của cùng một bệnh nhân.

`tools/organize_splits.py` tạo bản sao (symlink) của các split vào `data/splits/{train,val,test}/`
để khi demo có thể chọn bệnh nhân trong tập test (mô hình chưa từng học).

## Cài đặt cục bộ

```bash
cd /home/bbsw/DP/CNM-Final-Project
python -m venv .venv
source .venv/bin/activate
pip install -e mlops
```

Đặt bộ dữ liệu PhysioNet/CinC 2019 vào `Data/sepsis-2019/training_setA` và
`Data/sepsis-2019/training_setB`.

## Tái lập pipeline — bằng DVC

```bash
docker compose up -d mlflow
export MLFLOW_TRACKING_URI=http://localhost:15000
dvc repro
```

Các stage trong `dvc.yaml`: `prepare_data → train → evaluate → compare_and_register`.

## Giới thiệu Apache Airflow

Apache Airflow là một nền tảng mã nguồn mở dùng để **lập lịch và điều phối luồng công việc**
(workflow orchestration). Trong Airflow, một luồng công việc được mô tả bằng một **DAG**
(Directed Acyclic Graph — đồ thị có hướng không chu trình): mỗi đỉnh là một **task** (công
việc), mỗi cạnh là một **quan hệ phụ thuộc** quy định thứ tự chạy. Airflow tự động chạy các
task theo đúng thứ tự, theo lịch định sẵn, đồng thời theo dõi trạng thái, ghi log và tự thử
lại (retry) khi task lỗi.

Các thành phần chính của Airflow gồm: **Scheduler** (bộ lập lịch — quyết định task nào chạy
khi nào), **Webserver** (giao diện web để theo dõi và điều khiển DAG), và **Metadata
Database** (lưu trạng thái các lần chạy). Trong đồ án, ba thành phần này tương ứng với các
container `airflow-scheduler`, `airflow-webserver` và được lưu trạng thái trong PostgreSQL.

**Vì sao đồ án dùng Airflow:** mô hình học máy cần được **tái huấn luyện định kỳ** để cập
nhật theo dữ liệu mới. Thay vì chạy thủ công, Airflow cho phép **tự động hóa** toàn bộ
pipeline (`prepare_data → train → evaluate → compare_and_register`) theo lịch hằng ngày,
bảo đảm các bước chạy đúng thứ tự, có thể theo dõi và xử lý lỗi — đây chính là tinh thần
"tự động hóa" của MLOps. Airflow đóng vai trò bổ sung cho DVC: DVC dùng để chạy thủ công và
bảo đảm tính tái lập, còn Airflow dùng để tự động hóa theo lịch.

## Tái lập pipeline — bằng Airflow

DAG `sepsis_daily_retrain` chạy cùng các bước trên hằng ngày lúc 02:00. Mỗi bước chạy như một
tiến trình con độc lập (`python -m sepsis_mlops.<module>`).

- Giao diện Airflow: http://localhost:18080 (admin / admin123)
- Kích hoạt thủ công: `docker compose exec airflow-scheduler airflow dags trigger sepsis_daily_retrain`

## Model Registry & việc promote

- Tên model đã đăng ký: `sepsis-xgb-earlywarning`
- `compare_and_register` đăng ký challenger vừa huấn luyện thành một version mới
- Để promote lên Production: AUROC phải `>= min_auroc` (trong params.yaml) và cao hơn champion
  hiện tại; nếu không đạt thì version bị archive
- Khi promote, model phục vụ được copy sang `services/inference-service/artifacts/sepsis_model.json`
  kèm file `model_manifest.json`

## Phục vụ bằng artifact theo dõi trên MLflow

Mặc định inference service phục vụ checkpoint cục bộ:

```bash
MODEL_CHECKPOINT=artifacts/sepsis_model.json
```

Cũng hỗ trợ URI artifact của MLflow (`runs:/`, `models:/`, `mlflow-artifacts:/`):

```bash
MODEL_URI=runs:/<run_id>/model
MLFLOW_TRACKING_URI=http://mlflow:5000
```

Khi đặt `MODEL_URI`, nó được ưu tiên hơn `MODEL_CHECKPOINT`.

## Những gì được quản lý phiên bản

- `params.yaml`: cấu hình huấn luyện đảm bảo tái lập
- `dvc.yaml`: DAG dữ liệu, huấn luyện, đánh giá, đăng ký
- MLflow: tham số, chỉ số, checkpoint và model registry
- `services/inference-service/artifacts/model_manifest.json`: metadata của lần promote gần nhất

File `.psv` thô, parquet đã xử lý, checkpoint và thư mục run của MLflow đều bị Git bỏ qua (gitignore).

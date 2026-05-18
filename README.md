# Hệ thống AI Cảnh báo sớm Nhiễm khuẩn huyết (Sepsis Early-Warning CDSS)

> Tài liệu này viết cho người **chưa biết gì** về dự án. Đọc từ trên xuống là hiểu.

---

## 1. Hệ thống này là gì? Giải quyết vấn đề gì?

**Nhiễm khuẩn huyết (sepsis)** là tình trạng cơ thể phản ứng quá mức với nhiễm trùng, có thể gây suy đa tạng và tử vong. Trong ICU (khoa hồi sức), nếu phát hiện **sớm vài giờ** thì bác sĩ kịp can thiệp và cứu được bệnh nhân; phát hiện muộn thì nguy hiểm.

Hệ thống này là một **"trợ lý AI"** chạy nền trong ICU:

- Mỗi **giờ**, nó nhận các chỉ số của bệnh nhân (mạch, huyết áp, nhiệt độ, kết quả xét nghiệm máu...).
- Một mô hình AI tính ra **điểm nguy cơ sepsis** từ 0 đến 1 (càng cao càng nguy hiểm).
- Nếu nguy cơ **cao và kéo dài**, hệ thống **bật cảnh báo** cho bác sĩ.
- Tất cả hiển thị trên một **trang web theo dõi thời gian thực**.

Đây gọi là **CDSS** — *Clinical Decision Support System* — hệ thống hỗ trợ bác sĩ ra quyết định.

Dữ liệu dùng để huấn luyện AI lấy từ cuộc thi **PhysioNet/CinC Challenge 2019** (~40.000 bệnh nhân ICU thật).

---

## 2. Hệ thống hoạt động thế nào? (kể bằng lời)

Tưởng tượng một bệnh nhân nằm ICU. Mỗi giờ:

1. **Thiết bị theo dõi** gửi chỉ số của bệnh nhân vào hệ thống.
2. Hệ thống **tính toán đặc trưng** — biến chỉ số thô thành dạng AI hiểu được (ví dụ: nhịp tim trung bình 6 giờ qua, bao lâu rồi chưa xét nghiệm máu...).
3. **Mô hình AI** đọc các đặc trưng đó → cho ra **điểm nguy cơ sepsis**.
4. **Bộ luật cảnh báo** xem: nếu nguy cơ ≥ 0.6 suốt 3 giờ liền → **phát cảnh báo**.
5. **Trang web** hiển thị mọi thứ ngay lập tức cho bác sĩ.

Sơ đồ:

```
Thiết bị / dữ liệu bệnh nhân
        │  (chỉ số từng giờ)
        ▼
   Tính đặc trưng  ──►  Mô hình AI  ──►  Điểm nguy cơ  ──►  Luật cảnh báo
                                                                  │
                                                                  ▼
                                              Trang web theo dõi (realtime)
```

Các thành phần **trao đổi dữ liệu với nhau qua Kafka** (xem mục Thuật ngữ).

---

## 3. Các thành phần (mỗi cái là gì, làm gì)

Hệ thống gồm nhiều chương trình nhỏ ("service"), mỗi cái chạy trong một **container Docker** riêng:

| Thành phần | Làm gì | Ví dụ dễ hiểu |
|------------|--------|----------------|
| **replay-producer** | Mô phỏng thiết bị theo dõi — đọc hồ sơ bệnh nhân, "phát" lại từng giờ | Như cái máy đo đeo trên người bệnh nhân |
| **preprocess-buffer** | Nhận chỉ số thô, tính ra 114 đặc trưng cho AI | Người thư ký tổng hợp số liệu |
| **inference-service** | Chạy mô hình AI để cho ra điểm nguy cơ | Bộ não chẩn đoán |
| **alert-engine** | Xem điểm nguy cơ, quyết định khi nào cần báo động | Chuông báo động |
| **backend** | Lưu dữ liệu, cung cấp API, đẩy dữ liệu lên web | Trung tâm điều phối |
| **frontend** | Trang web bác sĩ nhìn vào | Màn hình theo dõi |
| **Kafka** | "Đường ống" để các thành phần gửi dữ liệu cho nhau | Hệ thống băng chuyền |
| **PostgreSQL** | Cơ sở dữ liệu — lưu bệnh nhân, dự đoán, cảnh báo | Tủ hồ sơ |
| **MLflow** | Quản lý các phiên bản mô hình AI | Kho lưu model |
| **Airflow** | Tự động huấn luyện lại AI mỗi ngày | Lịch hẹn tự động |

---

## 4. Cài đặt và chạy

### 4.1. Cần có sẵn
- **Docker** và **Docker Compose** (đã cài trên máy).
- **Dữ liệu** PhysioNet 2019. Nếu chưa có, tải bằng:
  ```bash
  python download_sepsis.py
  ```
  Lệnh này tải ~40.000 file vào thư mục `Data/sepsis-2019/`.

### 4.2. Khởi động hệ thống

```bash
# Vào thư mục dự án
cd CNM-Final-Project

# Tạo file cấu hình
cp .env.example .env

# Bật phần lõi (theo dõi realtime)
docker compose up -d kafka postgres mlflow backend frontend \
  replay-producer preprocess-buffer inference-service alert-engine
```

Lần đầu chạy sẽ mất vài phút (Docker tải/dựng image). Đợi đến khi xong.

Muốn bật thêm phần tự huấn luyện (Airflow):
```bash
docker compose up -d airflow-init airflow-webserver airflow-scheduler
```

### 4.3. Kiểm tra đã chạy chưa
```bash
docker compose ps
```
Tất cả service nên ở trạng thái `running`.

### 4.4. Mở các trang

| Mở trình duyệt vào | Để xem gì |
|--------------------|-----------|
| http://localhost:13000 | **Trang web chính** — màn hình theo dõi bệnh nhân |
| http://localhost:15000 | MLflow — kho mô hình AI |
| http://localhost:8080 | Airflow — lịch huấn luyện tự động |
| http://localhost:18800/docs | Tài liệu API (Swagger) |

**Tài khoản đăng nhập web:** `admin` / mật khẩu `admin123`

> **Lưu ý nếu dùng VS Code Remote / máy chủ từ xa:** mở tab **PORTS** ở dưới cùng VS Code → bấm "Forward a Port" → gõ `13000`. Sau đó mới mở được `localhost:13000`.

---

## 5. Cách xem trên trang web

1. Mở http://localhost:13000, đăng nhập `admin` / `admin123`.
2. Vào menu **Patient Monitor** (Màn hình theo dõi).
3. Ô **chọn ca** ở góc trên — gõ tên bệnh nhân để **tìm kiếm**.
4. Chọn một ca → màn hình hiện:
   - **Đồng hồ nguy cơ** — điểm sepsis hiện tại (xanh/cam/đỏ).
   - **Biểu đồ trajectory** — nguy cơ thay đổi theo từng giờ.
   - **Chỉ số sinh hiệu** — mạch, huyết áp... ô nào ngoài ngưỡng bình thường sẽ **đỏ**.
   - **Cảnh báo** — danh sách báo động sepsis.

Các menu khác: **ICU Stays** (danh sách ca), **Sepsis Alerts** (cảnh báo), **Analytics** (thống kê), **MLOps** (quản lý mô hình AI).

---

## 6. Tự đẩy dữ liệu bệnh nhân vào hệ thống

Khi mới chạy, `replay-producer` tự mô phỏng vài bệnh nhân. Nếu bạn muốn **tự đưa dữ liệu** một bệnh nhân cụ thể vào, dùng script `tools/push_patient.py`.

### 6.1. Script này làm gì?

Nó đóng vai "thiết bị gửi chỉ số về server": tạo một ca theo dõi mới rồi đẩy chỉ số từng giờ vào hệ thống. Dữ liệu sẽ chạy qua toàn bộ pipeline và **hiện lên web**.

Chạy từ máy host (không cần dựng lại Docker):
```bash
.venv/bin/python tools/push_patient.py [các tham số]
```

### 6.2. Giải thích TỪNG tham số

| Tham số | Bắt buộc? | Mặc định | Giải thích — khi nào dùng |
|---------|-----------|----------|---------------------------|
| `--patient-name` | Nên có | `Test Patient` | Tên bệnh nhân, sẽ hiện trên web để dễ tìm |
| `--age` | Không | (trống) | Tuổi bệnh nhân |
| `--gender` | Không | (trống) | Giới tính: `M` (nam) hoặc `F` (nữ) |
| `--external-ref` | Không | (trống) | Mã hồ sơ bệnh viện (nếu có) |
| `--source-record` | Không | (trống) | Ghi chú nguồn dữ liệu (vd tên file gốc) |
| `--psv` | Chọn 1 trong 2 | (trống) | Đường dẫn file `.psv` — script sẽ đọc và đẩy **từng giờ** trong file |
| `--record` | Chọn 1 trong 2 | (trống) | Chuỗi JSON chỉ số của **đúng 1 giờ** — dùng khi muốn đẩy tay 1 lần |
| `--hour` | Không | 0 | Số thứ tự giờ, dùng kèm `--record` |
| `--interval` | Không | 2.0 | Nghỉ bao nhiêu **giây** giữa mỗi giờ (chỉ áp dụng với `--psv`). Để 5–10 để xem live dễ |
| `--hours` | Không | (cả file) | Chỉ đẩy N giờ đầu của file (vd `--hours 30`) |
| `--stay-id` | Không | (trống) | Đẩy thêm vào **ca đã có sẵn** thay vì tạo ca mới |
| `--stop` | Không | (tắt) | Tự kết thúc ca (đánh dấu ENDED) sau khi đẩy xong |
| `--api` | Không | `http://localhost:18800` | Địa chỉ backend |
| `--username` / `--password` | Không | `admin` / `admin123` | Tài khoản đăng nhập để lấy quyền |

> **`--psv` hay `--record`?**
> - Dùng `--psv` khi muốn mô phỏng cả một ca nhiều giờ (giống bệnh nhân thật nằm viện).
> - Dùng `--record` khi chỉ muốn thử nhanh 1 giờ chỉ số tự nhập.

### 6.3. Các ví dụ chạy

**Ví dụ 1 — mô phỏng một bệnh nhân nằm viện (stream cả file):**
```bash
.venv/bin/python tools/push_patient.py \
  --patient-name "Nguyen Van A" --age 67 --gender M \
  --psv Data/sepsis-2019/training_setB/p110005.psv --interval 3
```
→ Tạo ca cho "Nguyen Van A", đẩy từng giờ trong file, mỗi 3 giây 1 giờ.

**Ví dụ 2 — chỉ đẩy 30 giờ đầu rồi kết thúc ca:**
```bash
.venv/bin/python tools/push_patient.py \
  --patient-name "Tran Thi B" --age 72 --gender F \
  --psv Data/sepsis-2019/training_setA/p001234.psv --hours 30 --stop
```

**Ví dụ 3 — đẩy tay 1 giờ chỉ số (không cần file):**
```bash
.venv/bin/python tools/push_patient.py --patient-name "BN khan cap" \
  --record '{"HR":124,"O2Sat":91,"Temp":39.3,"SBP":82,"MAP":56,"Resp":28,"Lactate":4.2}' \
  --hour 0
```
→ Các chỉ số: nhịp tim 124, SpO₂ 91%, sốt 39.3°C, huyết áp tụt 82, lactate cao 4.2 → nguy cơ sepsis cao.

**Ví dụ 4 — đẩy thêm giờ tiếp theo vào ca vừa tạo:**
```bash
.venv/bin/python tools/push_patient.py --stay-id <stay-id-in-ra-o-vi-du-3> \
  --record '{"HR":130,"SBP":78,"Lactate":5.0}' --hour 1
```

> Sau khi chạy script, mở web → Patient Monitor → tìm tên bệnh nhân vừa nhập để xem.

### 6.4. Các chỉ số có thể đưa vào `record`

Gửi đầy đủ hoặc chỉ một phần (thiếu thì hệ thống tự coi là "không đo"):

`HR` nhịp tim · `O2Sat` SpO₂ · `Temp` nhiệt độ · `SBP` huyết áp tâm thu · `MAP` huyết áp trung bình · `DBP` huyết áp tâm trương · `Resp` nhịp thở · `Lactate` lactate máu · `WBC` bạch cầu · `Creatinine` · `Platelets` tiểu cầu · `Glucose` đường huyết · ... (tổng 40 chỉ số, xem header file `.psv` để biết hết).

---

## 7. MLOps — phần huấn luyện AI

**MLOps** = quy trình tự động hoá việc huấn luyện, kiểm thử, triển khai mô hình AI.

Mỗi ngày (2h sáng), **Airflow** tự chạy lại 4 bước:

| Bước | Làm gì |
|------|--------|
| `prepare_data` | Đọc 40k hồ sơ, chia thành tập huấn luyện / kiểm tra, tính 114 đặc trưng |
| `train` | Huấn luyện mô hình XGBoost mới |
| `evaluate` | Chấm điểm mô hình mới trên tập kiểm tra (chỉ số **AUROC**) |
| `compare_and_register` | So mô hình mới với mô hình đang dùng. Tốt hơn → thay thế tự động |

Chạy tay (không qua Airflow):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e mlops
export MLFLOW_TRACKING_URI=http://localhost:15000
dvc repro          # chạy cả 4 bước
```

Cấu hình (số vòng huấn luyện, ngưỡng...) nằm trong file `params.yaml`.

---

## 8. Cấu trúc thư mục

```
CNM-Final-Project/
├── Data/sepsis-2019/        Dữ liệu bệnh nhân (file .psv)
├── mlops/src/sepsis_mlops/  Code huấn luyện AI
├── airflow/dags/            Lịch huấn luyện tự động
├── services/
│   ├── common/              Code dùng chung giữa các service
│   ├── replay-producer/     Mô phỏng thiết bị theo dõi
│   ├── preprocess-buffer/   Tính đặc trưng
│   ├── inference-service/   Chạy mô hình AI
│   └── alert-engine/        Luật cảnh báo
├── backend/                 Server API + WebSocket
├── frontend/                Trang web
├── tools/push_patient.py    Script đẩy dữ liệu bệnh nhân
├── infra/postgres/init.sql  Khởi tạo cơ sở dữ liệu
├── docker-compose.yml       Khai báo toàn bộ container
├── params.yaml              Cấu hình huấn luyện AI
├── dvc.yaml                 Định nghĩa pipeline MLOps
└── download_sepsis.py       Script tải dữ liệu
```

---

## 9. Thuật ngữ (giải thích nhanh)

| Từ | Nghĩa |
|----|-------|
| **Sepsis** | Nhiễm khuẩn huyết — phản ứng nguy hiểm của cơ thể với nhiễm trùng |
| **ICU** | Khoa hồi sức tích cực |
| **CDSS** | Hệ thống hỗ trợ bác sĩ ra quyết định lâm sàng |
| **Feature (đặc trưng)** | Con số đã xử lý để AI "hiểu" được (vd: nhịp tim trung bình 6h) |
| **XGBoost** | Loại mô hình AI dựa trên cây quyết định, mạnh với dữ liệu dạng bảng |
| **risk_score** | Điểm nguy cơ sepsis, từ 0 (an toàn) đến 1 (rất nguy hiểm) |
| **AUROC** | Chỉ số đo độ chính xác của mô hình (0.5 = đoán mò, 1.0 = hoàn hảo). Hệ thống đạt ~0.85 |
| **Kafka** | "Đường ống" truyền dữ liệu giữa các service theo thời gian thực |
| **MLflow** | Công cụ lưu và quản lý các phiên bản mô hình AI |
| **Airflow** | Công cụ chạy công việc theo lịch (vd huấn luyện lại mỗi ngày) |
| **Docker / container** | Cách đóng gói mỗi chương trình để chạy độc lập, giống nhau ở mọi máy |
| **WebSocket** | Kênh để server đẩy dữ liệu lên web ngay tức thì (không cần tải lại trang) |
| **`.psv` file** | File dữ liệu 1 bệnh nhân — mỗi dòng là 1 giờ, các cột ngăn bằng dấu `|` |
| **stay (ca theo dõi)** | Một lần bệnh nhân nằm ICU được hệ thống theo dõi |
| **champion / challenger** | Mô hình đang dùng (champion) vs mô hình mới (challenger) đem ra so |

---

## 10. Công nghệ sử dụng

- **AI:** XGBoost · scikit-learn
- **MLOps:** DVC · MLflow · Apache Airflow
- **Backend:** FastAPI · SQLAlchemy · PostgreSQL
- **Frontend:** React · TypeScript · Vite · Ant Design · ECharts
- **Streaming:** Apache Kafka
- **Hạ tầng:** Docker Compose

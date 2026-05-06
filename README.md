# MarketAI Phân tích giá sầu riêng

MarketAI là bản MVP full-stack cho phân tích thị trường sầu riêng dựa trên tài liệu `Nghiên cứu MarketAI_ Dự báo giá sầu riêng.pdf`.

## What is included

- Backend FastAPI với các endpoint phân tích và cảm biến dưới `/api/v1`.
- Đường ống thu thập dữ liệu thật từ các trang giá sầu riêng công khai.
- Lược đồ SQLAlchemy bám theo DDL PostgreSQL/TimescaleDB trong tài liệu.
- SQLite mặc định để chạy demo cục bộ ngay.
- Migration TimescaleDB tại `backend/migrations/001_init_timescale.sql`.
- Dữ liệu mẫu đa biến 120 ngày cho giá, thời tiết, khối lượng và chỉ số độ chín NIR.
- Bộ dự báo 30 ngày có cơ chế dự phòng xác định, sẵn sàng thay bằng `model.keras`.
- Bộ phát hiện đỉnh giá trả về tín hiệu `CẢNH BÁO BÁN`.
- Dashboard React + TypeScript với bảng giá chạy, biểu đồ đa trục, thẻ chỉ số và bảng dữ liệu.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

API docs: `http://127.0.0.1:8010/docs`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Dashboard: `http://127.0.0.1:5173`

## Thu thập dữ liệu giá thật

Scraper hiện hỗ trợ:

- `banggianongsan`: giá theo giống, giá tỉnh miền Tây và giá chợ đầu mối TP.HCM từ `banggianongsan.com`.
- `baonghean`: giá theo vùng và giống cho Tây Nam Bộ, Đông Nam Bộ, Tây Nguyên từ bài viết công khai.

Chạy toàn bộ nguồn:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.ingestion.run
```

Chạy qua API:

```powershell
curl -X POST "http://127.0.0.1:8010/api/v1/ingestion/scrape-prices"
curl "http://127.0.0.1:8010/api/v1/ingestion/scrape-runs"
```

Scraper lưu toàn bộ quan sát mà nguồn công khai có thể parse được. Hệ thống không tự bịa các tổ hợp vùng × giống nếu nguồn chỉ công bố bảng giống hoặc bảng vùng.

## Cơ sở dữ liệu production

Không dùng SQLite cho môi trường public. SQLite chỉ phù hợp demo/local vì ghi đồng thời, backup và migration đều hạn chế hơn PostgreSQL. Với production, dùng PostgreSQL hoặc TimescaleDB:

```powershell
docker compose up -d timescaledb
$env:MARKETAI_DATABASE_URL="postgresql+psycopg://marketai:marketai@127.0.0.1:5432/marketai"
pip install -r backend/requirements.txt
psql "postgresql://marketai:marketai@127.0.0.1:5432/marketai" -f backend/migrations/001_init_timescale.sql
psql "postgresql://marketai:marketai@127.0.0.1:5432/marketai" -f backend/migrations/002_production_indexes.sql
```

Các index production quan trọng cũng được tự tạo trong `app.db.init_db()` để local SQLite không bị chậm, nhưng migration SQL vẫn là nguồn nên dùng khi dựng database mới trên server.

Checklist trước khi mở public:

- Đặt `MARKETAI_DATABASE_URL` sang PostgreSQL/TimescaleDB, không dùng file `marketai.db`.
- Backup database hằng ngày và giữ ít nhất 7 bản gần nhất.
- Chạy migration trước khi start backend.
- Bật log lỗi backend và health check `/health`.
- Không dùng secret mặc định trong `MARKETAI_AUTH_TOKEN_SECRET`.

## Job định kỳ production

Không chạy scheduler định kỳ bên trong web process khi publish public, vì nhiều instance backend có thể làm job chạy chồng. Mặc định `MARKETAI_START_SCHEDULER_IN_API=false`.

Chạy từng job thủ công:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.run_platform_job scrape
.\.venv\Scripts\python.exe -m app.run_platform_job news
.\.venv\Scripts\python.exe -m app.run_platform_job data-quality
.\.venv\Scripts\python.exe -m app.run_platform_job retrain
```

Chạy worker scheduler riêng:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.run_scheduler
```

Chu kỳ mặc định:

- Quét giá nông sản: mỗi 24 giờ.
- Quét tin tức: mỗi 6 giờ.
- Kiểm tra chất lượng dữ liệu: mỗi 24 giờ.
- Huấn luyện lại mô hình/backtest: mỗi 24 giờ, sau khi dữ liệu giá được cập nhật.

Các job có file lock trong `.job_locks` để tránh chạy chồng cùng loại. Khi deploy bằng Docker/Kubernetes, chạy `app.run_scheduler` thành một service/worker riêng, tách khỏi service FastAPI. Nếu chạy trên Render/Railway/Fly.io, cần tạo thêm một worker process riêng cho `python -m app.run_scheduler`; chỉ chạy FastAPI thì dữ liệu sẽ không tự cập nhật.

## Audit hiệu năng sau deploy

Sau khi publish lên domain thật, chạy:

```powershell
python scripts/audit_performance.py https://your-domain.com --threshold-ms 2000
```

Script sẽ đo trang chủ và các API đầu trang. Nếu endpoint nào vượt 2 giây, lệnh trả exit code khác 0 để dùng được trong CI/CD. Nên chạy thêm Lighthouse hoặc WebPageTest trên mobile 4G để xác nhận LCP/TTI, vì local không phản ánh cold start, CDN, TLS và mạng thật.

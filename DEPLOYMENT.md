# Triển Khai Dự Báo Nông Sản Chi Phí Thấp

Mục tiêu của bản deploy hiện tại là giữ frontend tải nhanh qua Caddy/Cloudflare, API ổn định, worker chạy nền để quét giá và tin tức định kỳ, còn dữ liệu chính được lưu bền trong PostgreSQL.

## 1. Kiến Trúc Khuyến Nghị

1. Frontend: build từ thư mục `frontend`, phục vụ bằng Caddy trên VPS và đi qua Cloudflare.
2. Backend/API: một service Docker `api`, expose nội bộ cổng `8010`.
3. Database: PostgreSQL chạy cùng VPS để tiết kiệm chi phí giai đoạn đầu.
4. Worker nền: service Docker `worker`, tách khỏi API để job scrape, kiểm tra dữ liệu và train không làm chậm request người dùng.
5. Reverse proxy: Caddy tự cấp HTTPS cho `dubaonongsan.com`, `www.dubaonongsan.com` và `api.dubaonongsan.com`.

Không nên dùng backend miễn phí có cơ chế sleep nếu muốn trải nghiệm ổn định. Khi backend ngủ, request đầu tiên thường chậm và dễ gây lỗi giao diện.

## 2. Chuẩn Bị Domain Và DNS

Trong Cloudflare DNS:

- `dubaonongsan.com` và `www.dubaonongsan.com`: trỏ về IP VPS hoặc cấu hình theo proxy đang dùng.
- `api.dubaonongsan.com`: tạo bản ghi `A` trỏ về IP VPS.

Khi mới cấp SSL, có thể để bản ghi `api` ở chế độ DNS only trước. Sau khi Caddy cấp chứng chỉ thành công, bật proxy Cloudflare nếu cần.

## 3. Deploy Backend Và Frontend Trên VPS

SSH vào VPS rồi cài Docker nếu máy mới:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Đăng xuất SSH rồi đăng nhập lại để group `docker` có hiệu lực.

Clone hoặc cập nhật repo:

```bash
git clone <repo-url> dubaonongsan
cd dubaonongsan
```

Tạo file môi trường:

```bash
cp deploy/.env.example deploy/.env
cp backend/.env.production.example backend/.env.production
```

Ví dụ `deploy/.env`:

```env
POSTGRES_DB=marketai
POSTGRES_USER=marketai
POSTGRES_PASSWORD=<mat-khau-db-rat-dai>
FRONTEND_DOMAIN=dubaonongsan.com,www.dubaonongsan.com
API_DOMAIN=api.dubaonongsan.com
BACKUP_RCLONE_REMOTE=
BACKUP_RCLONE_CONFIG_B64=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_ENDPOINT=
R2_BUCKET_NAME=dubaonongsan-backups
MARKETAI_BACKUP_REMOTE=
SENTRY_DSN_BACKEND=
MARKETAI_RELEASE=
```

Ví dụ `backend/.env.production`:

```env
MARKETAI_ENVIRONMENT=production
MARKETAI_AUTH_TOKEN_SECRET=<chuoi-bi-mat-rat-dai>
MARKETAI_AUTH_PREVIOUS_TOKEN_SECRETS=
MARKETAI_PUBLIC_API_KEY=<api-key-public-rat-dai>
MARKETAI_IOT_API_KEY=<iot-key-rat-dai>
MARKETAI_CORS_ORIGINS=["https://dubaonongsan.com","https://www.dubaonongsan.com"]
MARKETAI_START_SCHEDULER_IN_API=false
MARKETAI_RATE_LIMIT_STORAGE_URI=redis://redis:6379/0
MARKETAI_NEWS_SCRAPE_INTERVAL_MINUTES=180
MARKETAI_SCRAPE_INTERVAL_MINUTES=120
MARKETAI_DATA_QUALITY_INTERVAL_MINUTES=1440
MARKETAI_RETRAIN_INTERVAL_MINUTES=1440
MARKETAI_SENTRY_DSN=
MARKETAI_SENTRY_TRACES_SAMPLE_RATE=0.1
MARKETAI_SENTRY_PROFILES_SAMPLE_RATE=0.1
MARKETAI_RELEASE=
MARKETAI_TELEGRAM_BOT_TOKEN=
MARKETAI_TELEGRAM_CHAT_ID=
MARKETAI_TELEGRAM_MIN_SEVERITY=info
```

Build frontend trước:

```bash
cd frontend
npm ci
export VITE_MARKETAI_RELEASE=$(git rev-parse --short HEAD)
npm run build
cd ..
```

Build và chạy production compose:

```bash
docker compose -f deploy/docker-compose.prod.yml build api worker
docker compose -f deploy/docker-compose.prod.yml up -d api worker caddy
docker compose -f deploy/docker-compose.prod.yml ps
```

Kiểm tra migration và API:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T api alembic current
curl -fsS https://api.dubaonongsan.com/api/v1/health/scrape
curl -I https://dubaonongsan.com/
```

## 4. Job Nền Sau Khi Publish

Compose production có các service chính:

- `api`: phục vụ web/mobile request.
- `worker`: chạy job nền theo lịch.
- `postgres`: lưu dữ liệu.
- `redis`: rate limit storage.
- `caddy`: HTTPS, static frontend, reverse proxy API.
- `postgres-backup`: backup PostgreSQL hằng ngày.

Lịch mặc định:

- Quét giá nông sản: theo `MARKETAI_SCRAPE_INTERVAL_MINUTES`.
- Quét tin tức: theo `MARKETAI_NEWS_SCRAPE_INTERVAL_MINUTES`.
- Kiểm tra chất lượng dữ liệu: mỗi 24 giờ.
- Đánh giá/train model: mỗi 24 giờ.
- Dọn revoked token: mỗi ngày.

Xem log worker:

```bash
docker compose -f deploy/docker-compose.prod.yml logs -f worker
```

Chạy job thủ công khi cần:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T api curl -X POST \
  -H "Authorization: Bearer <admin-token>" \
  http://localhost:8010/api/v1/platform/jobs/news
```

## 5. Backup Và Khôi Phục

Backup tự động chạy trong service `postgres-backup`, lưu file `.dump` ở `deploy/postgres-backup` và giữ 7 ngày gần nhất.

Offsite backup uu tien Cloudflare R2 qua cac bien trong `deploy/.env`:

```env
R2_ACCESS_KEY_ID=<bucket-scoped-access-key>
R2_SECRET_ACCESS_KEY=<bucket-scoped-secret>
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_BUCKET_NAME=dubaonongsan-backups
```

Khi cac bien R2 co day du, backup se upload vao `r2:<bucket>/daily/`. Nen tao lifecycle rule trong Cloudflare R2: prefix `daily/`, xoa object cu hon 30 ngay.

Neu can dung remote rclone khac, cau hinh `BACKUP_RCLONE_REMOTE` va `BACKUP_RCLONE_CONFIG_B64` trong `deploy/.env`. Khi tat ca bien offsite de trong, service chi backup local nhu hien tai.

Backup thủ công:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T postgres \
  pg_dump -U marketai -d marketai -Fc -f /tmp/backup-manual.dump
docker compose -f deploy/docker-compose.prod.yml cp postgres:/tmp/backup-manual.dump ./backup-manual.dump
```

Backup thu cong qua service backup:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T postgres-backup /usr/local/bin/marketai-postgres-backup
docker compose -f deploy/docker-compose.prod.yml logs --tail=120 postgres-backup
```

Khôi phục vào database mới cần dừng API/worker trước, restore xong mới bật lại:

```bash
docker compose -f deploy/docker-compose.prod.yml stop api worker
docker compose -f deploy/docker-compose.prod.yml exec -T postgres \
  pg_restore -U marketai -d marketai --clean --if-exists /backups/<file>.dump
docker compose -f deploy/docker-compose.prod.yml up -d api worker
```

## 6. Quy Trình Update An Toàn

Trước khi deploy:

```bash
git status --short
git pull --ff-only origin main
cd backend && PYTHONPATH=. pytest -q
cd ../frontend && npm run typecheck && npm run build
```

Deploy:

```bash
cd ..
docker compose -f deploy/docker-compose.prod.yml build api worker
docker compose -f deploy/docker-compose.prod.yml up -d api worker caddy
```

Sau deploy:

```bash
docker compose -f deploy/docker-compose.prod.yml ps
docker compose -f deploy/docker-compose.prod.yml logs --tail=120 api
docker compose -f deploy/docker-compose.prod.yml logs --tail=120 worker
curl -fsS https://api.dubaonongsan.com/api/v1/health/scrape
curl -I https://dubaonongsan.com/
```

Nếu cần rollback:

```bash
git log --oneline -5
git checkout <commit-truoc-do>
cd frontend && npm run build
cd ..
docker compose -f deploy/docker-compose.prod.yml build api worker
docker compose -f deploy/docker-compose.prod.yml up -d api worker caddy
```

## 7. Checklist Trước Khi Mở Public

- Đã đổi toàn bộ secret trong `backend/.env.production`.
- `MARKETAI_AUTH_TOKEN_SECRET` dài ít nhất 32 ký tự và không dùng giá trị mặc định.
- Khi xoay JWT secret, đưa secret cũ vào `MARKETAI_AUTH_PREVIOUS_TOKEN_SECRETS` trong một thời gian chuyển tiếp rồi xóa sau.
- `MARKETAI_CORS_ORIGINS` chỉ chứa domain thật, HTTPS.
- Production không dùng SQLite.
- Redis đang chạy để rate limit không dùng memory local.
- VPS firewall chỉ mở `22`, `80`, `443`.
- `https://api.dubaonongsan.com/api/v1/health/scrape` trả `status=ok`.
- `https://dubaonongsan.com/` trả HTTP 200 và asset JS mới.
- Worker không restart liên tục.
- Backup PostgreSQL có file mới trong `deploy/postgres-backup`.
- Log Caddy/API/worker có rotation, không để file log phình vô hạn.

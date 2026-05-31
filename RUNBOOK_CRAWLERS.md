# Runbook crawler va van hanh du lieu

Cap nhat: 2026-05-26

File nay gom cac buoc xu ly nhanh khi crawler gia nong san, gia phan bon, tin tuc hoac job nen gap loi tren live site.

## 1. Kiem tra tinh trang dich vu

Tren VPS:

```bash
cd /opt/dubaonongsan
docker compose -f deploy/docker-compose.prod.yml ps
docker compose -f deploy/docker-compose.prod.yml logs --tail=120 api
docker compose -f deploy/docker-compose.prod.yml logs --tail=120 worker
```

Neu `api` hoac `worker` khong healthy, uu tien doc log loi Python truoc khi restart.

## 1.1. Bat canh bao ngoai he thong

Backend co hook alert cho job fail. Uu tien Telegram neu co token/chat id; neu khong co Telegram thi fallback sang webhook Slack/Discord/n8n/Make.

```env
MARKETAI_TELEGRAM_BOT_TOKEN=
MARKETAI_TELEGRAM_CHAT_ID=
MARKETAI_TELEGRAM_MIN_SEVERITY=info
MARKETAI_OPS_ALERT_WEBHOOK_URL=https://example.com/marketai-alert
MARKETAI_OPS_ALERT_TIMEOUT_SECONDS=2
```

Khi job nen fail, backend gui Telegram message gom severity, event va context. Neu dung webhook fallback, backend gui JSON dang:

```json
{"event":"platform_job_failed","text":"[ERROR] platform job failed","context":{"job_name":"scrape_world_fertilizer_current","status":"failed"}}
```

Test nhanh trong container API:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T api python -c "from app.services.ops_alerts import send_ops_alert; send_ops_alert('ops_alert_test', {'source':'manual'}, severity='info')"
```

Neu chua cau hinh Telegram/webhook, job van chay binh thuong va loi van duoc ghi vao log JSON cua `api`/`worker`.

## 1.2. Sentry

Sentry duoc bat bang bien moi truong trong `backend/.env.production` va `frontend/.env.production`:

```env
MARKETAI_SENTRY_DSN=
MARKETAI_RELEASE=
VITE_SENTRY_DSN=
VITE_MARKETAI_RELEASE=
```

Backend sample performance/profiling toi da 10% de tranh ton quota. Sentry khong gui PII mac dinh va bo qua HTTP 4xx expected.

## 2. Kiem tra suc khoe crawler

```bash
curl -fsS https://api.dubaonongsan.com/api/v1/health/scrape
curl -fsS https://api.dubaonongsan.com/api/v1/platform/input-prices/health
curl -fsS https://api.dubaonongsan.com/api/v1/platform/world-fertilizer/health
```

Canh bao can xu ly ngay:

- `worker_dead`: worker khong cap nhat duoc trang thai.
- `stale`: du lieu qua han cho phep.
- `latest_run.error_message` co loi parser, timeout hoac 403.

## 3. Chay lai job thu cong

Neu worker van song nhung nguon bi fail, co the chay job qua endpoint admin hoac vao container:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T api python -m app.worker --dry-run
docker compose -f deploy/docker-compose.prod.yml restart worker
```

Sau khi restart, xem log trong 3-5 phut:

```bash
docker compose -f deploy/docker-compose.prod.yml logs -f --tail=120 worker
```

## 4. Khi crawler gia phan bon the gioi fail

Thu tu uu tien:

1. Kiem tra nguon `commoditypriceapi_urea_public_1y` co doi HTML/Next.js payload khong.
2. Neu nguon daily fail, kiem tra `worldbank_pinksheet` con cap nhat du lieu thang khong.
3. Neu chi daily fail, UI van co the dung forecast neo monthly nhung phai de y `is_stale`.
4. Sau khi sua parser, chay test parser tuong ung truoc khi deploy.

## 5. Khi database hoac migration co van de

Khong sua truc tiep schema tren live neu chua backup. Truoc moi migration:

```bash
docker compose -f deploy/docker-compose.prod.yml exec -T postgres pg_dump -U marketai marketai > backup-before-migration.sql
docker compose -f deploy/docker-compose.prod.yml exec -T api alembic current
docker compose -f deploy/docker-compose.prod.yml exec -T api alembic upgrade head
```

Neu migration fail, dung lai va giu log loi. Khong chay lai nhieu lan khi chua ro migration co idempotent hay khong.

## 6. Sau moi lan deploy

Bat buoc smoke test:

```bash
curl -I https://dubaonongsan.com/
curl -fsS https://api.dubaonongsan.com/api/v1/health/scrape
curl -fsS "https://api.dubaonongsan.com/api/v1/advisory/world-fertilizer/forecast?commodity_slug=urea&horizon=30" | head -c 500
```

Neu co sua frontend, kiem tra them desktop va mobile cac trang:

- `/`
- `/tin-tuc`
- `/huong-dan`
- `/khuyen-nghi-bon-phan`
- `/du-bao-gia/phan-bon`
- `/roi-uoc-tinh`

# Triá»ƒn khai NÃ´ng nghiá»‡p sá»‘ chi phÃ­ tháº¥p

Má»¥c tiÃªu: frontend táº£i nhanh qua CDN, API khÃ´ng ngá»§, worker tá»± quÃ©t giÃ¡/tin tá»©c Ä‘á»‹nh ká»³, dá»¯ liá»‡u lÆ°u bá»n trong PostgreSQL.

## Kiáº¿n trÃºc khuyáº¿n nghá»‹

1. Frontend: Cloudflare Pages, miá»…n phÃ­ cho giai Ä‘oáº¡n Ä‘áº§u, build tá»« thÆ° má»¥c `frontend`.
2. Backend/API: má»™t VPS nhá» cháº¡y Docker Compose.
3. Database: PostgreSQL cháº¡y cÃ¹ng VPS Ä‘á»ƒ tiáº¿t kiá»‡m chi phÃ­ ban Ä‘áº§u.
4. Worker ná»n: cháº¡y cÃ¹ng VPS, tÃ¡ch khá»i API Ä‘á»ƒ job quÃ©t giÃ¡, quÃ©t tin, kiá»ƒm tra dá»¯ liá»‡u vÃ  retrain khÃ´ng lÃ m cháº­m request cá»§a ngÆ°á»i dÃ¹ng.
5. Reverse proxy: Caddy tá»± cáº¥p HTTPS cho `api.dubaonongsan.com`.

KhÃ´ng nÃªn dÃ¹ng backend miá»…n phÃ­ cÃ³ cÆ¡ cháº¿ sleep náº¿u muá»‘n táº£i á»•n Ä‘á»‹nh dÆ°á»›i 2 giÃ¢y. Khi backend ngá»§, request Ä‘áº§u tiÃªn thÆ°á»ng cháº­m vÃ  lÃ m há»ng tráº£i nghiá»‡m.

## 1. Chuáº©n bá»‹ domain vÃ  DNS

Trong Cloudflare DNS:

- `dubaonongsan.com` vÃ  `www.dubaonongsan.com`: trá» vá» Cloudflare Pages theo hÆ°á»›ng dáº«n khi add custom domain.
- `api.dubaonongsan.com`: táº¡o báº£n ghi `A` trá» vá» IP VPS.

Khuyáº¿n nghá»‹ lÃºc má»›i cáº¥p SSL: Ä‘á»ƒ `api` á»Ÿ cháº¿ Ä‘á»™ DNS only trÆ°á»›c. Sau khi Caddy cáº¥p chá»©ng chá»‰ thÃ nh cÃ´ng, cÃ³ thá»ƒ báº­t proxy Cloudflare náº¿u cáº§n.

## 2. Deploy backend trÃªn VPS

SSH vÃ o VPS rá»“i cÃ i Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

ÄÄƒng xuáº¥t SSH rá»“i Ä‘Äƒng nháº­p láº¡i Ä‘á»ƒ group `docker` cÃ³ hiá»‡u lá»±c.

Clone repo:

```bash
git clone <repo-url> nong-nghiep-so
cd nong-nghiep-so
```

Táº¡o file mÃ´i trÆ°á»ng:

```bash
cp deploy/.env.example deploy/.env
cp backend/.env.production.example backend/.env.production
```

Sá»­a `deploy/.env`:

```env
POSTGRES_DB=marketai
POSTGRES_USER=marketai
POSTGRES_PASSWORD=<mat-khau-db-rat-dai>
API_DOMAIN=api.dubaonongsan.com
```

Sá»­a `backend/.env.production`:

```env
MARKETAI_AUTH_TOKEN_SECRET=<chuoi-bi-mat-rat-dai>
MARKETAI_PUBLIC_API_KEY=<api-key-public-rat-dai>
MARKETAI_CORS_ORIGINS=["https://dubaonongsan.com","https://www.dubaonongsan.com"]
MARKETAI_START_SCHEDULER_IN_API=false
MARKETAI_NEWS_SCRAPE_INTERVAL_MINUTES=180
MARKETAI_SCRAPE_INTERVAL_MINUTES=1440
MARKETAI_NEWS_SCRAPE_DAILY_HOUR=7
MARKETAI_NEWS_SCRAPE_DAILY_MINUTE=0
MARKETAI_RETRAIN_INTERVAL_MINUTES=1440
```

Cháº¡y backend:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
docker compose --env-file .env -f docker-compose.prod.yml ps
```

Kiá»ƒm tra API:

```bash
curl https://api.dubaonongsan.com/health
```

## 3. Deploy frontend trÃªn Cloudflare Pages

Káº¿t ná»‘i repo vá»›i Cloudflare Pages:

- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `dist`
- Environment variable:

```env
VITE_API_BASE_URL=https://api.dubaonongsan.com
```

Sau khi deploy xong, gáº¯n custom domain `dubaonongsan.com` vÃ  `www.dubaonongsan.com`.

## 4. Job ná»n sau khi publish

Compose production cÃ³ 2 service tÃ¡ch riÃªng:

- `api`: phá»¥c vá»¥ web vÃ  mobile request.
- `worker`: tá»± cháº¡y job ná»n.

Lá»‹ch máº·c Ä‘á»‹nh:

- Quét tin tức: lúc 07:00 mỗi sáng và mỗi 3 giờ.
- QuÃ©t giÃ¡: má»—i 24 giá».
- Kiá»ƒm tra cháº¥t lÆ°á»£ng dá»¯ liá»‡u: má»—i 24 giá».
- Cháº¡y láº¡i Ä‘Ã¡nh giÃ¡ mÃ´ hÃ¬nh: má»—i 24 giá».

Xem log worker:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml logs -f worker
```

Cháº¡y job thá»§ cÃ´ng khi cáº§n:

```bash
docker compose --env-file .env -f docker-compose.prod.yml exec api curl -X POST \
  -H "Authorization: Bearer <admin-token>" \
  http://localhost:8010/api/v1/platform/jobs/news
```

## 5. Tá»‘i Æ°u Ä‘á»ƒ load dÆ°á»›i 2 giÃ¢y

Viá»‡c quan trá»ng nháº¥t lÃºc Ä‘áº§u:

1. Frontend pháº£i náº±m trÃªn Cloudflare Pages/CDN.
2. API khÃ´ng Ä‘Æ°á»£c ngá»§.
3. áº¢nh hero vÃ  áº£nh hÆ°á»›ng dáº«n nÃªn chuyá»ƒn sang WebP/AVIF, kÃ­ch thÆ°á»›c thá»±c táº¿ theo layout, trÃ¡nh áº£nh 2-4 MB.
4. Báº­t gzip/zstd á»Ÿ Caddy, file `deploy/Caddyfile` Ä‘Ã£ cáº¥u hÃ¬nh sáºµn.
5. Giá»¯ API vÃ  DB cÃ¹ng VPS trong giai Ä‘oáº¡n Ä‘áº§u Ä‘á»ƒ giáº£m latency vÃ  chi phÃ­.
6. KhÃ´ng expose PostgreSQL ra internet.

Khi traffic tÄƒng:

- TÃ¡ch PostgreSQL sang managed database.
- ThÃªm Redis cache cho ticker, tin tiÃªu Ä‘iá»ƒm, metadata.
- DÃ¹ng object storage/CDN cho áº£nh bÃ i viáº¿t.
- ThÃªm monitoring uptime vÃ  alert Telegram/email.

## 6. Backup vÃ  cáº­p nháº­t

Backup PostgreSQL:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml exec postgres \
  pg_dump -U marketai marketai > backup-$(date +%F).sql
```

Update code:

```bash
git pull
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

Xem log API:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.prod.yml logs -f api
```

## 7. Checklist trÆ°á»›c khi má»Ÿ public

- ÄÃ£ Ä‘á»•i toÃ n bá»™ secret trong `backend/.env.production`.
- `MARKETAI_CORS_ORIGINS` chá»‰ chá»©a domain tháº­t.
- VPS firewall chá»‰ má»Ÿ `22`, `80`, `443`.
- `api.dubaonongsan.com/health` tráº£ vá» `{"status":"ok"}`.
- Cloudflare Pages Ä‘ang build vá»›i `VITE_API_BASE_URL`.
- Worker cÃ³ log cháº¡y vÃ  khÃ´ng restart liÃªn tá»¥c.
- Frontend Lighthouse/Network khÃ´ng táº£i áº£nh quÃ¡ lá»›n.


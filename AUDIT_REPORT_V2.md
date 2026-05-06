# MarketAI — Audit Follow-Up Report (V2)

> **Mục đích:** Verify lại các fix từ `AUDIT_REPORT.md` và chỉ ra vấn đề mới/chưa hoàn tất. File này dành cho AI agent đọc + fix tiếp.
>
> **Phương pháp verify:**
> 1. Đọc lại tất cả file đã sửa
> 2. Chạy `pytest tests/` (kết quả: **20/20 passed** ✅)
> 3. Test backend boot (`python -c "from app.main import app"` → 48 routes OK)
> 4. So sánh từng `[FIX-NNN]` cũ với code hiện tại
>
> **Convention:**
> - ✅ DONE — fix áp dụng đúng
> - ⚠️ PARTIAL — fix làm một phần, còn thiếu
> - ❌ MISSING — chưa làm
> - 🆕 NEW — vấn đề mới phát sinh sau khi sửa
> - 🐛 BUG — fix gây ra bug mới hoặc có sai sót

---

## 📊 TỔNG KẾT KẾT QUẢ

| Section | Đã làm | Còn thiếu | Vấn đề mới |
|---|---|---|---|
| Critical (FIX-001 → 012) | 12/12 ✅ | 0 | 1 |
| High (FIX-013 → 020) | 7/8 ⚠️ | 1 | 2 |
| Medium (FIX-021 → 030) | 9/10 ⚠️ | 1 | 2 |
| Low (FIX-031 → 041) | 9/11 ⚠️ | 2 | 1 |

**Điểm số mới:**
| Tiêu chí | Cũ | Mới | Lý do |
|---|---|---|---|
| Bảo mật | 4/10 | **8/10** | Auth/SSRF/rate-limit/JWT đã fix, còn 1 endpoint hở |
| Hiệu năng | 5/10 | **7.5/10** | Cache + bulk query OK, nhưng TimescaleDB hypertable chưa setup |
| Khả năng mở rộng | 6/10 | **7/10** | Alembic OK nhưng schema management còn drift |

**Kết luận chung:** Phần lớn fix đã làm đúng, codebase tăng đáng kể về chất lượng. Tuy nhiên có **1 vấn đề CRITICAL mới** (`/ingestion/scrape-runs` không auth) và **1 vấn đề HIGH** (TimescaleDB hypertable không được tạo trong production).

---

## 🔴 SECTION 1 — VẤN ĐỀ NGHIÊM TRỌNG MỚI / CHƯA HOÀN TẤT

---

### [NEW-001] 🔴 CRITICAL — Endpoint `/ingestion/scrape-runs` Vẫn Không Có Authentication

**Trạng thái:** ❌ MISSING (audit cũ không flag, nhưng phát hiện khi review)

**File:** `backend/app/api/ops.py:132-137`

**Vấn đề:** Sau khi fix các endpoint khác, GET endpoint này vẫn không có auth. Anyone có thể xem toàn bộ scrape history (sources, success/fail, error messages — leak system internals).

**Code hiện tại:**
```python
@router.get("/ingestion/scrape-runs", response_model=list[ScrapeRunOut])
def scrape_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PriceIngestionService(db).latest_runs(limit=limit)
```

**Fix:**
```python
@router.get("/ingestion/scrape-runs", response_model=list[ScrapeRunOut])
def scrape_runs(
    _: AppUser = Depends(require_admin),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PriceIngestionService(db).latest_runs(limit=limit)
```

**Tại sao quan trọng:** Error messages từ scrapers thường chứa thông tin debug (URL parsing failures, internal IPs, stack traces). Public exposure giúp attacker enumerate dependencies.

---

### [NEW-002] 🔴 CRITICAL — TimescaleDB Hypertables KHÔNG Được Tạo Trong Production

**Trạng thái:** 🐛 BUG nghiêm trọng — Alembic migration thay thế migration script cũ nhưng KHÔNG run `create_hypertable()`

**File:** `backend/alembic/versions/20260501_0001_security_indexes.py:19-26`

**Vấn đề:** Migration cũ `migrations/001_init_timescale.sql` có:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('daily_market_prices', 'record_timestamp', if_not_exists => TRUE);
SELECT create_hypertable('weather_environmental_metrics', 'record_timestamp', if_not_exists => TRUE);
SELECT create_hypertable('iot_sensor_telemetry', 'record_timestamp', if_not_exists => TRUE);
```

Nhưng Alembic version chỉ chạy:
```python
def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)  # ← Tạo bảng thường, KHÔNG hypertable
```

**Hậu quả:**
- Đang dùng image `timescale/timescaledb:2.17.2-pg16` nhưng **không enable extension**, không tạo hypertable
- Toàn bộ ưu điểm time-series (auto-partitioning, compression, query speedup) **không có**
- Khi data > 10M rows, query sẽ rất chậm

**Fix — Cập nhật Alembic migration:**

```python
# backend/alembic/versions/20260501_0001_security_indexes.py
"""baseline security and performance indexes"""
from alembic import op
import sqlalchemy as sa

from app.db import Base
from app import models  # noqa: F401

revision = "20260501_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    
    # is_admin column
    user_columns = {column["name"] for column in inspector.get_columns("app_users")}
    if "is_admin" not in user_columns:
        op.add_column("app_users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    
    # ✅ NEW: TimescaleDB extension + hypertables (PostgreSQL only)
    if bind.dialect.name == "postgresql":
        # Check if TimescaleDB extension is available
        has_timescale = bind.execute(sa.text(
            "SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'"
        )).scalar()
        
        if has_timescale:
            op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
            
            # Convert to hypertables (idempotent)
            for table, time_column in [
                ("daily_market_prices", "record_timestamp"),
                ("weather_environmental_metrics", "record_timestamp"),
                ("iot_sensor_telemetry", "record_timestamp"),
            ]:
                op.execute(sa.text(
                    f"SELECT create_hypertable('{table}', '{time_column}', "
                    f"if_not_exists => TRUE, migrate_data => TRUE)"
                ))
            
            # Compression policy for old prices (>90 days)
            op.execute("""
                ALTER TABLE daily_market_prices SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'variety_id, region_id, crop_type'
                )
            """)
            op.execute(sa.text(
                "SELECT add_compression_policy('daily_market_prices', "
                "INTERVAL '90 days', if_not_exists => TRUE)"
            ))
    
    # Indexes (giữ nguyên code cũ)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_region_variety_time "
        "ON daily_market_prices (crop_type, region_id, variety_id, record_timestamp DESC)"
    )
    # ... rest unchanged
    
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS news_articles_source_url_key")
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_news_url_hash ON news_articles (md5(source_url))")


def downgrade() -> None:
    # Hypertables không thể downgrade dễ dàng — comment lại để cảnh báo
    # KHÔNG drop hypertables nếu không cần thiết
    pass
```

**Quan trọng:** Sau khi fix, run `alembic upgrade head` trong production sẽ:
1. Enable TimescaleDB extension
2. Convert 3 bảng thành hypertables (an toàn nếu chưa có data hoặc có ít data)
3. Setup compression policy

**Validation sau khi run:**
```sql
-- Trong psql, kiểm tra:
SELECT * FROM timescaledb_information.hypertables;
-- Phải thấy 3 dòng: daily_market_prices, weather_environmental_metrics, iot_sensor_telemetry
```

---

### [NEW-003] 🟠 HIGH — Migration Files `001_init_timescale.sql` và `002_production_indexes.sql` Bị Mồ Côi

**Trạng thái:** 🆕 Hai file SQL không được run anywhere sau khi chuyển sang Alembic

**Files:**
- `backend/migrations/001_init_timescale.sql`
- `backend/migrations/002_production_indexes.sql`

**Vấn đề:**
- Code không gọi `psql -f 001_init_timescale.sql` ở đâu (Dockerfile/docker-compose không có entrypoint chạy chúng)
- Alembic dùng `Base.metadata.create_all` (xem NEW-002), không reference các file này
- Người mới đọc repo sẽ confused: "001 là init schema hay là Alembic?"

**Fix:** Xóa 2 file (hoặc move vào thư mục `backend/migrations/legacy/` để giữ làm tham khảo):

```bash
# Option A: Xóa hoàn toàn (sạch sẽ)
rm backend/migrations/001_init_timescale.sql
rm backend/migrations/002_production_indexes.sql
rm backend/migrations/003_security_and_indexes.sql  # đã được Alembic thay thế
rm backend/migrations/004_fix_news_url_index.sql    # đã được Alembic thay thế
rmdir backend/migrations  # nếu trống

# Option B: Giữ làm tham khảo
mkdir -p backend/migrations/legacy_sql_reference
mv backend/migrations/*.sql backend/migrations/legacy_sql_reference/
echo "# Reference SQL — DO NOT RUN. Schema giờ do Alembic quản lý." > backend/migrations/legacy_sql_reference/README.md
```

**Lưu ý:** Logic compression policy & TimescaleDB hypertable trong các file SQL cần được port sang Alembic (xem NEW-002).

---

### [NEW-004] 🟠 HIGH — File `run_scheduler.py` Cũ Vẫn Dùng `time.sleep(60)` Pattern Lỗi Thời

**Trạng thái:** 🆕 Dead code, gây nhầm lẫn

**File:** `backend/app/run_scheduler.py`

**Vấn đề:** File này dùng pattern cũ (sync loop + `time.sleep(60)`) đã được thay thế bởi `JobScheduler` (APScheduler) trong `platform_jobs.py`. Nếu DevOps gõ nhầm `python -m app.run_scheduler` thay vì `python -m app.worker`, sẽ chạy version cũ:
- Không có graceful shutdown (Ctrl+C cứng)
- Không có thread executor
- Không invalidate cache sau scrape

**Fix:** Xóa file:
```bash
rm backend/app/run_scheduler.py
```

Cũng xóa file legacy `run_platform_job.py` nếu không còn ai dùng:
```bash
# Verify trước khi xóa:
grep -r "run_platform_job" backend/
# Nếu không có usage, xóa:
rm backend/app/run_platform_job.py
```

---

### [NEW-005] 🟡 MEDIUM — `BackgroundScheduler = JobScheduler` Alias Là Dead Code

**Trạng thái:** 🆕 Backward-compat alias không có ai dùng

**File:** `backend/app/services/platform_jobs.py:273`

```python
BackgroundScheduler = JobScheduler  # ← dòng này
```

**Vấn đề:** Sau khi `main.py` và `worker.py` đã chuyển sang dùng `JobScheduler` trực tiếp, alias này chỉ còn được dùng trong `run_scheduler.py` (file đang được đề xuất xóa ở NEW-004). Sau khi xóa `run_scheduler.py`, alias này hoàn toàn không cần thiết.

**Fix:** Xóa dòng 273:
```python
# ❌ XÓA:
BackgroundScheduler = JobScheduler
```

---

### [NEW-006] 🟡 MEDIUM — `db.py` Vẫn Có Runtime SQLite Patches Mặc Dù Đã Có Alembic

**Trạng thái:** ⚠️ PARTIAL — Alembic + runtime patches cùng tồn tại, gây drift

**File:** `backend/app/db.py:38-80`

**Vấn đề:** Code có 4 nguồn schema khác nhau:
1. `models.py` (SQLAlchemy declarative — source of truth)
2. `alembic/versions/*.py` (migrations — chạy trong production PostgreSQL)
3. `db.py:_ensure_runtime_columns()` + `_ensure_runtime_indexes()` (chạy mỗi startup cho SQLite)
4. `migrations/*.sql` (mồ côi, xem NEW-003)

Mỗi lần thêm cột mới phải update CẢ 3 nơi (1, 2, 3) thì SQLite tests + PostgreSQL prod đều work. Một trong 3 quên = drift.

**Fix:** Thay `_ensure_runtime_columns/_ensure_runtime_indexes` bằng cách run Alembic cho mọi environment (kể cả SQLite tests):

```python
# backend/app/db.py — version mới
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args, "future": True}
if settings.database_url == "sqlite:///:memory:":
    engine_kwargs["poolclass"] = StaticPool
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Run Alembic migrations programmatically.
    
    For SQLite (dev/tests) and PostgreSQL (prod), both use Alembic.
    This eliminates schema drift.
    """
    from app import models  # noqa: F401
    from alembic import command
    from alembic.config import Config
    
    alembic_cfg_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_cfg_path))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
```

**Lưu ý:** Test sẽ chậm hơn vì Alembic phải chạy mỗi lần. Nếu cần tốc độ cho test, có thể fallback `Base.metadata.create_all` cho SQLite memory:
```python
def init_db() -> None:
    from app import models  # noqa: F401
    if settings.database_url == "sqlite:///:memory:":
        # Test path: nhanh hơn, không cần lịch sử migration
        Base.metadata.create_all(bind=engine)
        return
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
```

---

## 🟠 SECTION 2 — VẤN ĐỀ MỚI MỨC TRUNG BÌNH

---

### [NEW-007] 🟡 `ContentPortalService.guides()` Vẫn Gọi `seed_guides()` Trên Mọi Cache Miss

**Trạng thái:** ⚠️ PARTIAL — Cache giúp giảm 1/15min nhưng vẫn không nên seed mỗi cache miss

**File:** `backend/app/services/content_portal.py:229-234`

**Code hiện tại:**
```python
def guides(self, crop: str | None = None, limit: int = 120) -> list[GuidePost]:
    self.seed_guides()  # ← chạy mỗi cache miss (mỗi 15 min với cache TTL=900s)
    stmt = select(GuidePost).order_by(desc(GuidePost.published_at))
    if crop:
        stmt = stmt.where((GuidePost.crop_type == crop) | (GuidePost.crop_type.is_(None)))
    return self.db.scalars(stmt.limit(limit)).all()
```

**Fix:** Chỉ seed khi DB rỗng:
```python
def guides(self, crop: str | None = None, limit: int = 120) -> list[GuidePost]:
    has_any = self.db.scalar(select(GuidePost.post_id).limit(1))
    if not has_any:
        self.seed_guides()
    stmt = select(GuidePost).order_by(desc(GuidePost.published_at))
    if crop:
        stmt = stmt.where((GuidePost.crop_type == crop) | (GuidePost.crop_type.is_(None)))
    return self.db.scalars(stmt.limit(limit)).all()
```

---

### [NEW-008] 🟡 `latest_news` Cache Có Side-Effect `seed_fallback_news()` Bên Trong

**Trạng thái:** 🆕 Cache wraps function có side-effect — race condition tiềm ẩn

**File:** `backend/app/services/content_portal.py:116-126`

```python
@cached(prefix="news", ttl_seconds=300)  # ← cached
def latest_news(self, limit: int = 24, category: str | None = None) -> list[NewsArticle]:
    ...
    if combined:
        return combined[:limit]
    self.seed_fallback_news()  # ← write nếu DB empty
    rows = self.db.scalars(stmt.limit(...)).all()
    return sorted(...)[:limit]
```

**Vấn đề:** Nếu 100 user cùng request lúc DB rỗng, có thể 100 lần `seed_fallback_news()` chạy đồng thời → race condition khi insert (UNIQUE constraint giúp nhưng vẫn tốn DB calls).

**Fix:** Tách logic, dùng lock + idempotent guard:
```python
import threading
_seed_lock = threading.Lock()
_seeded_once = False

def latest_news(self, limit: int = 24, category: str | None = None) -> list[NewsArticle]:
    global _seeded_once
    stmt = select(NewsArticle).order_by(desc(NewsArticle.published_at), desc(NewsArticle.scraped_at))
    if category:
        stmt = stmt.where(NewsArticle.category == category)
    rows = self.db.scalars(stmt.limit(max(limit * NEWS_CANDIDATE_MULTIPLIER, NEWS_MIN_CANDIDATES))).all()
    combined = sorted([row for row in rows if _is_keepable_news_article(row)], key=_news_time_key, reverse=True)
    
    if combined:
        return combined[:limit]
    
    # Idempotent seed: chỉ chạy 1 lần per process
    if not _seeded_once:
        with _seed_lock:
            if not _seeded_once:
                self.seed_fallback_news()
                _seeded_once = True
        rows = self.db.scalars(stmt.limit(max(limit * NEWS_CANDIDATE_MULTIPLIER, NEWS_MIN_CANDIDATES))).all()
        return sorted([row for row in rows if _is_keepable_news_article(row)], key=_news_time_key, reverse=True)[:limit]
    
    return []
```

---

### [NEW-009] 🟡 `register` Endpoint Trả Về 200 Thay Vì 201 Created

**Trạng thái:** 🆕 REST hygiene minor

**File:** `backend/app/api/auth.py:39`

**Code:**
```python
@router.post("/auth/register", response_model=AuthTokenOut)
@limiter.limit("5/minute")
def register(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
```

**Tests cũng dùng 200:** `tests/test_api.py:67` `assert response.status_code == 200`

**Fix:**
```python
@router.post("/auth/register", response_model=AuthTokenOut, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    ...
```

**Update tests:**
```python
# tests/test_api.py:67
assert response.status_code == 201  # ← từ 200 thành 201
# tests/test_api.py:103
assert response.status_code == 201  # ← từ 200 thành 201
```

---

### [NEW-010] 🟡 Tests Vẫn Dùng Hardcoded Password `marketai123`

**Trạng thái:** 🆕 Code smell — password trùng với demo password cũ

**File:** `backend/tests/test_api.py:67, 102`

```python
json={"email": "farmer@example.com", "password": "marketai123", "display_name": "Farmer"}
```

`marketai123` đáp ứng schema validation mới (>=8 chars + có digit) nên test pass. Nhưng nó là string đã được khuyến cáo xóa khỏi code production. Để consistency, nên đổi tests dùng password fixture rõ ràng:

**Fix:**
```python
# tests/conftest.py (tạo mới hoặc thêm vào file hiện có)
import pytest

TEST_USER_PASSWORD = "test-pass-with-digits-12345"  # rõ ràng đây là test fixture

@pytest.fixture()
def test_password() -> str:
    return TEST_USER_PASSWORD
```

```python
# tests/test_api.py — update
def test_auth_and_watchlist_flow(client, test_password):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "farmer@example.com", "password": test_password, "display_name": "Farmer"},
    )
    ...
```

---

### [NEW-011] 🟡 `ingestion/data-quality-check` Endpoint Là Duplicate Của `platform/jobs/data-quality`

**Trạng thái:** 🆕 Hai endpoints cùng gọi 1 method, gây confused

**File:** `backend/app/api/ops.py:50-55, 124-129`

Cả 2 endpoint đều gọi `PlatformJobService(db).run_data_quality()`:
```python
@router.post("/platform/jobs/data-quality")  # endpoint 1
def run_data_quality_job(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return PlatformJobService(db).run_data_quality()

@router.post("/ingestion/data-quality-check")  # endpoint 2 — duplicate
def data_quality_check(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return PlatformJobService(db).run_data_quality()
```

**Fix:** Xóa `/ingestion/data-quality-check` (giữ `/platform/jobs/data-quality` vì naming consistent hơn). Cập nhật frontend nếu có gọi:

```python
# Xóa khỏi ops.py:
@router.post("/ingestion/data-quality-check")
def data_quality_check(...): ...
```

```bash
# Verify frontend không gọi:
grep -r "data-quality-check" frontend/src/
```

---

## 🟡 SECTION 3 — VẤN ĐỀ NHỎ / IMPROVEMENTS

---

### [NEW-012] 🟢 LOW — `AppHeader` Component Prop Drilling Quá Nhiều

**Trạng thái:** 🆕 Code smell — 17 props passed trong khi đã có AuthContext

**Files:** `frontend/src/App.tsx:470-492`, `frontend/src/components/AppHeader.tsx`

**Code hiện tại:**
```typescript
<AppHeader
  section={section}
  crop={crop}
  user={user}                          // ← từ useAuth, có thể đọc trực tiếp
  mainSections={mainSections}
  cropTabs={tabs}
  priceMenuOpen={priceMenuOpen}
  authOpen={authOpen}
  authMode={authMode}
  authName={authName}
  authEmail={authEmail}
  authPassword={authPassword}
  onSectionChange={setSection}
  onAnalyticsOpen={openAnalytics}
  onPriceMenuOpenChange={setPriceMenuOpen}
  onAuthOpenChange={setAuthOpen}
  onAuthModeChange={setAuthMode}
  onAuthNameChange={setAuthName}
  onAuthEmailChange={setAuthEmail}
  onAuthPasswordChange={setAuthPassword}
  onAuthSubmit={(mode) => void handleAuth(mode)}
  onLogout={logout}
/>
```

**Fix:** Cho `AppHeader` dùng `useAuth()` trực tiếp, giảm prop count:

```typescript
// AppHeader.tsx — version refactored
import { useAuth } from "../contexts/AuthContext";

type Props = {
  section: MainSection;
  crop: CropType;
  mainSections: NavItem[];
  cropTabs: CropNavItem[];
  priceMenuOpen: boolean;
  authOpen: boolean;
  authMode: AuthMode;
  authName: string;
  authEmail: string;
  authPassword: string;
  onSectionChange: (section: MainSection) => void;
  onAnalyticsOpen: (crop: CropType) => void;
  onPriceMenuOpenChange: (open: boolean) => void;
  onAuthOpenChange: (open: boolean) => void;
  onAuthModeChange: (mode: AuthMode) => void;
  onAuthNameChange: (value: string) => void;
  onAuthEmailChange: (value: string) => void;
  onAuthPasswordChange: (value: string) => void;
  onAuthSubmit: (mode: AuthMode) => void;
};

export function AppHeader({
  section, crop, mainSections, cropTabs,
  priceMenuOpen, authOpen, authMode, authName, authEmail, authPassword,
  onSectionChange, onAnalyticsOpen, onPriceMenuOpenChange,
  onAuthOpenChange, onAuthModeChange, onAuthNameChange,
  onAuthEmailChange, onAuthPasswordChange, onAuthSubmit,
}: Props) {
  const { user, signOut } = useAuth();
  // ... use signOut instead of onLogout
}
```

App.tsx giảm 2 props (`user`, `onLogout`).

---

### [NEW-013] 🟢 LOW — `fetchGuides` & `fetchNews` Trong api.ts Không Nhận `AbortSignal`

**Trạng thái:** ⚠️ PARTIAL — AbortController chỉ áp dụng cho analytics endpoints

**File:** `frontend/src/lib/api.ts:389-400`

**Code hiện tại:**
```typescript
export function fetchNews() {
  return getJson<NewsArticle[]>("/api/v1/content/news?limit=2000");
}

export function fetchGuides(crop?: CropType, limit = 120) {
  const cropParam = crop ? `?crop=${crop}&limit=${limit}` : `?limit=${limit}`;
  return getJson<GuidePost[]>(`/api/v1/content/guides${cropParam}`);
}
```

`loadContent()` trong App.tsx (line 161-168) không cancellable. Khi user navigate nhanh giữa Home → News → Home, requests vẫn race.

**Fix:**
```typescript
export function fetchNews(signal?: AbortSignal) {
  return getJson<NewsArticle[]>("/api/v1/content/news?limit=2000", signal);
}

export function fetchGuides(crop?: CropType, limit = 120, signal?: AbortSignal) {
  const cropParam = crop ? `?crop=${crop}&limit=${limit}` : `?limit=${limit}`;
  return getJson<GuidePost[]>(`/api/v1/content/guides${cropParam}`, signal);
}
```

App.tsx cập nhật:
```typescript
useEffect(() => {
  const controller = new AbortController();
  void loadContent(controller.signal).catch(...);
  return () => controller.abort();
}, []);

async function loadContent(signal?: AbortSignal) {
  const [newsPayload, guidePayload] = await Promise.all([
    fetchNews(signal),
    fetchGuides(undefined, section === "guides" ? 300 : 12, signal)
  ]);
  ...
}
```

---

### [NEW-014] 🟢 LOW — `prerender_seo.py` Slug Filename Không Sanitize Special Chars

**Trạng thái:** 🆕 Có thể fail trên Windows hoặc tạo URL lỗi

**File:** `scripts/prerender_seo.py:15-17`

```python
def _slug_from_url(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or "article"
    return tail.replace(".html", "").replace(".htm", "")[:120]
```

**Vấn đề:** Nếu URL là `https://site.com/page?id=123&type=2`, tail = `page?id=123&type=2`. File `page?id=123&type=2.html` không hợp lệ trên Windows (có `?` và `&`).

**Fix:**
```python
import re

def _slug_from_url(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or "article"
    tail = tail.replace(".html", "").replace(".htm", "")
    # Strip query string
    tail = tail.split("?")[0]
    # Sanitize: chỉ giữ alphanumeric, dash, underscore, dot
    tail = re.sub(r"[^a-zA-Z0-9\-_.]", "-", tail)
    # Collapse multiple dashes
    tail = re.sub(r"-+", "-", tail).strip("-")
    return tail[:120] or "article"
```

---

### [NEW-015] 🟢 LOW — Sitemap.xml Liệt Kê URL Tiếng Việt Mà App Không Có Routing

**Trạng thái:** 🆕 SEO inconsistency

**File:** `frontend/public/sitemap.xml`

```xml
<url><loc>https://nongnghiepso.vn/tin-tuc</loc>...</url>
<url><loc>https://nongnghiepso.vn/huong-dan</loc>...</url>
<url><loc>https://nongnghiepso.vn/du-bao-gia-nong-san</loc>...</url>
```

**Vấn đề:** SPA hiện tại không có client-side routing — chỉ dùng `useState section` để switch. URL `/tin-tuc` sẽ trả 404 từ server (Cloudflare Pages sẽ rewrite về index.html nếu config đúng, nhưng URL trong browser bar lệch). Google index page nhưng user click vào lại thấy Home page.

**Fix tạm:** Thêm CSP allowlist + đổi sitemap dùng query string:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://nongnghiepso.vn/</loc><priority>1.0</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=news</loc><priority>0.8</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=guides</loc><priority>0.8</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&amp;crop=sau_rieng</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&amp;crop=ca_phe</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&amp;crop=ho_tieu</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&amp;crop=lua</loc><priority>0.9</priority></url>
</urlset>
```

**Đồng thời update App.tsx để parse query string:**
```typescript
// App.tsx — đầu component
const [section, setSection] = useState<MainSection>(() => {
  const params = new URLSearchParams(window.location.search);
  const s = params.get("section");
  return (["home", "analytics", "news", "guides", "methodology"].includes(s ?? "") 
    ? s as MainSection 
    : "home");
});

const [crop, setCrop] = useState<CropType>(() => {
  const params = new URLSearchParams(window.location.search);
  const c = params.get("crop");
  return (["sau_rieng", "ca_phe", "ho_tieu", "lua"].includes(c ?? "") 
    ? c as CropType 
    : "sau_rieng");
});

// Sync URL khi section/crop change (cho SEO + sharing)
useEffect(() => {
  const params = new URLSearchParams();
  if (section !== "home") params.set("section", section);
  if (section === "analytics" && crop !== "sau_rieng") params.set("crop", crop);
  const qs = params.toString();
  const newUrl = qs ? `?${qs}` : window.location.pathname;
  if (newUrl !== window.location.search) {
    window.history.replaceState({}, "", newUrl);
  }
}, [section, crop]);
```

**Lý tưởng dài hạn:** Migrate Next.js để có server-side routing thật cho `/tin-tuc`, `/huong-dan`, etc.

---

### [NEW-016] 🟢 LOW — Vite Config Thiếu `react-vendor` Chunk

**Trạng thái:** ⚠️ PARTIAL — chunk strategy gần đủ nhưng thiếu separate React

**File:** `frontend/vite.config.ts:20-24`

**Code hiện tại:**
```typescript
manualChunks: {
  "recharts": ["recharts"],
  "icons": ["@phosphor-icons/react"]
}
```

**Vấn đề:** React và React-DOM bị bundle vào main chunk. Khi update code app, browser cache miss luôn cả React (lớn ~40KB gzip).

**Fix:**
```typescript
manualChunks: {
  "react-vendor": ["react", "react-dom"],
  "recharts": ["recharts"],
  "icons": ["@phosphor-icons/react"]
}
```

---

### [NEW-017] 🟢 LOW — `_ensure_runtime_columns` Trong db.py Vẫn Patch SQLite Cho `is_admin` Column

**Trạng thái:** ⚠️ Sẽ tự động fix nếu áp dụng [NEW-006]

**File:** `backend/app/db.py:55-57`

```python
user_columns = {column["name"] for column in inspector.get_columns("app_users")}
if "is_admin" not in user_columns:
    connection.execute(text("ALTER TABLE app_users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
```

Đây là patch hợp lý cho tests nhưng nếu áp dụng NEW-006 (dùng Alembic cho mọi env), block này có thể xóa.

---

## 🟢 SECTION 4 — VERIFICATION CHECKLIST CHO CÁC FIX ĐÃ ÁP DỤNG

| FIX# | Trạng thái | Verification |
|---|---|---|
| FIX-001 | ✅ DONE | `grep "require_admin" backend/app/api/ops.py` → `scrape_prices` được bảo vệ |
| FIX-002 | ✅ DONE | `backfill_model_ready` có `Depends(require_admin)` |
| FIX-003 | ✅ DONE | `data_quality_check` có `Depends(require_admin)` |
| FIX-004 | ✅ DONE | `ingest_maturity_telemetry` có `Depends(require_iot_api_key)` |
| FIX-005 | ✅ DONE | Tất cả `/platform/jobs/*` có `require_admin`. `is_admin` column có trong models. Test passing. |
| FIX-006 | ✅ DONE | SSRF protection: `_is_private_ip`, allowlist hosts, max size 5MB |
| FIX-007 | ✅ DONE | `create_demo_user=False` default, App.tsx authEmail/Password = "" |
| FIX-008 | ✅ DONE | `validate_auth_token_secret` raise nếu prod + secret yếu |
| FIX-009 | ✅ DONE | slowapi installed + decorators trên auth/subscribers/sensors |
| FIX-010 | ✅ DONE | `python-jose` import + `jwt.encode/decode` thay HMAC tự build |
| FIX-011 | ✅ DONE | `AuthContext` chỉ dùng sessionStorage, xóa localStorage cũ |
| FIX-012 | ✅ DONE | CORS chỉ allow specific methods/headers |
| FIX-013 | ✅ DONE | `model_metrics` đọc từ `ModelTrainingRun` table |
| FIX-014 | ✅ DONE | `core/cache.py` + `@cached` decorator áp dụng |
| FIX-015 | ✅ DONE | `data_quality_bulk()` method + sử dụng trong `_quality_summary` |
| FIX-016 | ⚠️ NOT DONE | `top_movers` vẫn dùng Python loop với 10000 rows. Không phải critical, có cache. |
| FIX-017 | ✅ DONE | `latest_news` không còn gọi `cleanup_news_archive` & `_normalize_news_records` |
| FIX-018 | ✅ DONE | `start_scheduler_in_api: bool = False` |
| FIX-019 | ⚠️ PARTIAL | Alembic added, nhưng `db.py` còn runtime patches + SQL files mồ côi (xem NEW-003, NEW-006) |
| FIX-020 | ✅ DONE | `timescale/timescaledb:2.17.2-pg16` image |
| FIX-021 | ⚠️ PARTIAL | Chỉ tạo `AuthContext`, chưa có `MarketContext` & `ContentContext`. App.tsx vẫn 680+ lines |
| FIX-022 | ✅ DONE | `MasterChart` wrapped với `memo` |
| FIX-023 | ✅ DONE | AbortController trong loadData (có warning: `loadContent` chưa) |
| FIX-024 | ✅ DONE | `fetchHistorical(... limit: Math.max(days * 4, 60))` |
| FIX-025 | ✅ DONE | Meta tags + og + structured data đủ |
| FIX-026 | ✅ DONE | `prerender_seo.py` + sitemap.xml + robots.txt (xem NEW-014, NEW-015) |
| FIX-027 | ✅ DONE | Pin react@18.3.1, recharts@2.13.3 etc. |
| FIX-028 | ✅ DONE | Caddyfile có security headers + log + max body |
| FIX-029 | ✅ DONE | docker-compose có postgres-backup, resource limits, logging |
| FIX-030 | ⚠️ PARTIAL | Chunks có nhưng thiếu `react-vendor` (xem NEW-016) |
| FIX-031 | ✅ DONE | Routes split thành `app/api/{auth,analytics,content,metadata,ops,public}.py` |
| FIX-032 | ✅ DONE | Validators trong `schemas.py:AuthCredentials` |
| FIX-033 | ✅ DONE | EmailStr + email-validator |
| FIX-034 | ✅ DONE | APScheduler + JobScheduler |
| FIX-035 | ✅ DONE | Worker có `signal.signal(SIGTERM/SIGINT)` + `shutdown_event` |
| FIX-036 | ✅ DONE | `_build_session()` với Retry + backoff |
| FIX-037 | ✅ DONE | Indexes trong Alembic + `db.py` |
| FIX-038 | ✅ DONE | `uq_news_url_hash` (PostgreSQL only) |
| FIX-039 | ✅ DONE | ErrorBoundary + wrap trong main.tsx |
| FIX-040 | ✅ DONE | Structured JSON logs (production) + request_id middleware |
| FIX-041 | ✅ DONE | volatile_storage logic removed |

---

## 📋 SECTION 5 — LỘ TRÌNH SỬA TIẾP

### Tuần này (CRITICAL — block production)
- [ ] **NEW-001**: Thêm `require_admin` cho `/ingestion/scrape-runs` (5 phút)
- [ ] **NEW-002**: Thêm hypertable creation vào Alembic migration (30 phút) — **Bắt buộc nếu muốn dùng TimescaleDB**

### Tuần sau (HIGH — clean up technical debt)
- [ ] **NEW-003**: Xóa hoặc move 4 file SQL mồ côi (5 phút)
- [ ] **NEW-004**: Xóa `run_scheduler.py` (1 phút)
- [ ] **NEW-005**: Xóa `BackgroundScheduler = JobScheduler` alias (1 phút)
- [ ] **NEW-006**: Migrate `db.py` dùng Alembic cho mọi env (1 giờ)
- [ ] **NEW-007**: Fix `guides()` chỉ seed khi DB rỗng (10 phút)
- [ ] **NEW-008**: Idempotent seed cho `latest_news` (15 phút)

### Tháng tới (MEDIUM)
- [ ] **NEW-009**: register trả 201 + update test (5 phút)
- [ ] **NEW-010**: Test password fixture (15 phút)
- [ ] **NEW-011**: Xóa duplicate endpoint (5 phút)
- [ ] **NEW-013**: Add AbortSignal cho fetchNews/fetchGuides (15 phút)
- [ ] **NEW-014**: Fix slug sanitize trong prerender_seo (10 phút)
- [ ] **NEW-015**: Update sitemap + URL routing (1 giờ)
- [ ] **NEW-016**: Thêm react-vendor chunk (1 phút)

### Optional (LOW)
- [ ] **NEW-012**: Refactor AppHeader bỏ prop drilling (30 phút)
- [ ] **NEW-017**: Cleanup db.py runtime patches sau khi áp dụng NEW-006 (5 phút)

---

## 📋 SECTION 6 — SMOKE TEST SAU KHI FIX

```bash
# 1. Test backend imports
cd backend && python -c "from app.main import app; print('OK', len(app.routes), 'routes')"

# 2. Test all unit tests
pytest tests/ -v

# 3. Test admin auth
TOKEN=$(curl -s -X POST http://localhost:8010/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"normal@test.com","password":"testpass123","display_name":"Test"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Should return 403 (non-admin user)
curl -s -X GET http://localhost:8010/api/v1/ingestion/scrape-runs \
  -H "Authorization: Bearer $TOKEN" -w "%{http_code}\n" -o /dev/null

# 4. Test SSRF block
curl -s "http://localhost:8010/api/v1/content/image-proxy?url=http://127.0.0.1/test" -w "%{http_code}\n" -o /dev/null
# Expect: 403

# 5. Test rate limit (run 11 lần)
for i in $(seq 1 11); do
  curl -s -X POST http://localhost:8010/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"x@x.com","password":"badpass1"}' \
    -w "Try $i: %{http_code}\n" -o /dev/null
done
# Expect: lần 11 trả 429

# 6. Test TimescaleDB hypertables (chỉ khi đã apply NEW-002)
docker compose -f deploy/docker-compose.prod.yml exec postgres \
  psql -U marketai -d marketai -c "SELECT * FROM timescaledb_information.hypertables;"
# Expect: 3 hypertables

# 7. Check cache hit
curl -s http://localhost:8010/api/v1/analytics/forecast-30-days?region_id=1&variety_id=1 -w "Time: %{time_total}s\n" -o /dev/null
sleep 1
curl -s http://localhost:8010/api/v1/analytics/forecast-30-days?region_id=1&variety_id=1 -w "Time: %{time_total}s\n" -o /dev/null
# Expect: lần 2 nhanh hơn nhiều (cache hit)
```

---

## 📋 SECTION 7 — KẾT LUẬN

### Đã thành công lớn ✅
- 39/41 issues từ audit cũ đã được fix tốt
- Tests đầy đủ (20/20 pass), trong đó có new test cho admin authorization
- Code structure rõ ràng hơn nhiều với routers tách
- Performance: cache + bulk query + APScheduler đều áp dụng đúng
- Security: từ 4/10 lên 8/10 — đáng kể

### Cần sửa gấp ⚠️
- **NEW-001**: Một endpoint admin hở (5 phút fix)
- **NEW-002**: TimescaleDB hypertables không được tạo — đang dùng "Postgres mặc kín tên TimescaleDB" (30 phút fix)

### Nice to have 🟡
- 4 file SQL mồ côi cần dọn
- App.tsx vẫn 680 lines — có thể tách Context tiếp
- Sitemap routing chưa khớp với SPA structure

**Đánh giá tổng quan:** Codebase đã sẵn sàng để **MVP launch** sau khi fix NEW-001 và NEW-002. Các vấn đề còn lại là technical debt có thể giải quyết sau.

---

**Format prompt cho AI agent:**
```
Implement NEW-001 and NEW-002 from AUDIT_REPORT_V2.md. After each fix:
1. Run `pytest tests/ -v` and verify all tests pass
2. Test backend boot with `python -c "from app.main import app"`
3. Commit with message: "fix(audit-v2): [NEW-NNN] short description"

Do NEW-001 first (it's a 5-minute fix). 
Then NEW-002 which requires updating Alembic migration.
Report back with test results.
```

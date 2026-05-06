# MarketAI — Báo Cáo Audit Toàn Diện & Hướng Dẫn Sửa Code

> **Mục đích tài liệu:** File này dành cho AI agent hoặc developer đọc và sửa code theo từng mục. Mỗi vấn đề được đánh số `[FIX-NNN]` để dễ theo dõi. Mức độ ưu tiên: 🔴 Critical → 🟠 High → 🟡 Medium → 🟢 Low.
>
> **Cách dùng:** Sửa theo thứ tự — các fix đánh số nhỏ hơn thường là tiền đề cho các fix sau. Mỗi fix có:
> - **Vấn đề:** mô tả rõ
> - **File ảnh hưởng:** đường dẫn cụ thể
> - **Code hiện tại:** snippet trích dẫn
> - **Code đề xuất:** code thay thế
> - **Lý do:** vì sao phải sửa
>
> **Phạm vi:** Toàn bộ MarketAI (backend FastAPI + frontend React + deployment).

---

## 📊 BẢNG ĐIỂM TỔNG QUAN

| Tiêu chí | Điểm | Lý do |
|---|---|---|
| **Bảo mật** | **4 / 10** | 7 lỗ hổng critical/high (auth missing, SSRF, XSS, brute-force) |
| **Hiệu năng** | **5 / 10** | Backtest chạy mỗi request, không cache, N+1, god component |
| **Khả năng mở rộng** | **6 / 10** | TimescaleDB + Docker tốt, nhưng file-lock, monolith, no Alembic |
| **Code quality** | **7 / 10** | Có test, type hint đầy đủ, nhưng main.py 800 lines, schema drift |
| **SEO** | **3 / 10** | SPA không SSR, không meta tags, không sitemap |

---

## 🔴 SECTION 1 — RED FLAGS (CRITICAL — SỬA NGAY TRƯỚC KHI PUBLIC)

---

### [FIX-001] 🔴 Endpoint `/ingestion/scrape-prices` Không Có Authentication

**Vấn đề:** Bất kỳ ai (anonymous request, không cần login) cũng có thể gọi endpoint này để trigger scrape lên server bên thứ 3 — DoS amplification + tốn resource server.

**File:** `backend/app/main.py:780-785`

**Code hiện tại:**
```python
@app.post(f"{settings.api_prefix}/ingestion/scrape-prices")
def scrape_prices(
    source: str | None = Query(default=None, description="Optional scraper source key"),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PriceIngestionService(db).scrape_and_store(source=source)
```

**Code đề xuất:** (cần FIX-005 trước để có `require_admin`)
```python
@app.post(f"{settings.api_prefix}/ingestion/scrape-prices")
def scrape_prices(
    _: AppUser = Depends(require_admin),
    source: str | None = Query(default=None, description="Optional scraper source key"),
    db: Session = Depends(get_db),
) -> list[dict]:
    return PriceIngestionService(db).scrape_and_store(source=source)
```

**Lý do:** Trigger network calls đến nhiều site bên thứ 3 — nếu để ngỏ, kẻ tấn công có thể dùng server của bạn làm bot DoS các site khác.

---

### [FIX-002] 🔴 Endpoint `/ingestion/backfill-model-ready` Không Có Authentication

**File:** `backend/app/main.py:788-793`

**Code hiện tại:**
```python
@app.post(f"{settings.api_prefix}/ingestion/backfill-model-ready")
def backfill_model_ready(
    crop: str = Query(default="sau_rieng"),
    db: Session = Depends(get_db),
) -> dict:
    return ModelReadyBackfillService(db, crop_type=crop).backfill()
```

**Code đề xuất:**
```python
@app.post(f"{settings.api_prefix}/ingestion/backfill-model-ready")
def backfill_model_ready(
    _: AppUser = Depends(require_admin),
    crop: str = Query(default="sau_rieng"),
    db: Session = Depends(get_db),
) -> dict:
    return ModelReadyBackfillService(db, crop_type=crop).backfill()
```

---

### [FIX-003] 🔴 Endpoint `/ingestion/data-quality-check` Không Có Authentication

**File:** `backend/app/main.py:796-800`

**Code đề xuất:**
```python
@app.post(f"{settings.api_prefix}/ingestion/data-quality-check")
def data_quality_check(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return PlatformJobService(db).run_data_quality()
```

---

### [FIX-004] 🔴 Endpoint `/sensors/maturity-telemetry` Không Có Authentication

**Vấn đề:** Bất kỳ ai cũng có thể inject IoT data giả vào `iot_sensor_telemetry`. Vì `maturity_index` ảnh hưởng tới forecast (qua `_weather_bias`), kẻ tấn công có thể bóp méo dự báo giá.

**File:** `backend/app/main.py:751-777`

**Code đề xuất:** Dùng API key riêng cho IoT devices (không phải user JWT):
```python
def require_iot_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not x_api_key or x_api_key != settings.iot_api_key:
        raise HTTPException(status_code=401, detail="IoT API key không hợp lệ")

@app.post(
    f"{settings.api_prefix}/sensors/maturity-telemetry",
    response_model=SensorTelemetryOut,
    status_code=201,
)
def ingest_maturity_telemetry(
    payload: SensorTelemetryIn,
    _: None = Depends(require_iot_api_key),
    db: Session = Depends(get_db),
) -> SensorTelemetryOut:
    ...
```

Thêm vào `core/config.py`:
```python
iot_api_key: str = Field(default="", description="API key cho IoT devices gửi telemetry")
```

---

### [FIX-005] 🔴 Tất Cả `/platform/jobs/*` Không Phân Biệt Admin vs User Thường

**Vấn đề:** Endpoints `/platform/jobs/scrape`, `/jobs/news`, `/jobs/data-quality`, `/jobs/retrain`, `/platform/jobs` (GET), `/platform/model-runs` (GET), `/content/news/scrape` chỉ check `current_user`. Bất kỳ ai đăng ký tài khoản (mất 5 giây) đều có thể trigger retrain (tốn CPU) hoặc xem job history.

**Files ảnh hưởng:**
- `backend/app/models.py` — thêm field `is_admin`
- `backend/app/services/auth.py` — thêm dependency `require_admin`
- `backend/app/main.py:701-748, 257-262` — áp dụng dependency

**Code thêm vào `models.py`:**
```python
from sqlalchemy import Boolean

class AppUser(Base):
    __tablename__ = "app_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")

    watchlist: Mapped[list["WatchlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
```

**Migration SQL `migrations/003_add_is_admin.sql`:**
```sql
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS ix_app_users_is_admin ON app_users (is_admin) WHERE is_admin = TRUE;
-- Set một admin đầu tiên (THAY EMAIL):
-- UPDATE app_users SET is_admin = TRUE WHERE email = 'admin@nongnghiepso.vn';
```

**Code thêm vào `services/auth.py`:**
```python
def require_admin(user: AppUser = Depends(current_user)) -> AppUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên mới có quyền này")
    return user
```

**Code update `main.py`:** đổi tất cả `Depends(current_user)` thành `Depends(require_admin)` trên 6 endpoints sau:
```python
# Line 257 — scrape news
@app.post(f"{settings.api_prefix}/content/news/scrape")
def scrape_news(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict: ...

# Line 701 — view jobs
@app.get(f"{settings.api_prefix}/platform/jobs", response_model=list[PlatformJobRunOut])
def platform_jobs(_: AppUser = Depends(require_admin), ...) -> list: ...

# Line 710 — view model runs
@app.get(f"{settings.api_prefix}/platform/model-runs", response_model=list[ModelTrainingRunOut])
def platform_model_runs(_: AppUser = Depends(require_admin), ...) -> list: ...

# Line 719, 727, 735, 743 — run jobs
@app.post(f"{settings.api_prefix}/platform/jobs/scrape")
def run_scrape_job(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict: ...

@app.post(f"{settings.api_prefix}/platform/jobs/data-quality")
def run_data_quality_job(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict: ...

@app.post(f"{settings.api_prefix}/platform/jobs/news")
def run_news_scrape_job(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict: ...

@app.post(f"{settings.api_prefix}/platform/jobs/retrain")
def run_retrain_job(_: AppUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict: ...
```

**Frontend:** Thêm `is_admin` vào `AuthUser` type:
```typescript
// frontend/src/lib/api.ts
export type AuthUser = {
  user_id: number;
  email: string;
  display_name: string;
  is_admin: boolean;  // ← thêm
};
```

Trong `App.tsx`, ẩn các nút admin nếu không phải admin:
```typescript
{user?.is_admin ? (
  <button onClick={() => runJob("scrape")}>Chạy scrape</button>
) : null}
```

Cập nhật `_user_out` trong `main.py:105`:
```python
def _user_out(user: AppUser) -> AuthUserOut:
    return AuthUserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
    )
```

Và `schemas.py`:
```python
class AuthUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: str
    display_name: str
    is_admin: bool = False
```

---

### [FIX-006] 🔴 SSRF Vulnerability Trong `/content/image-proxy`

**Vấn đề:** Endpoint check URL có trong `guide_posts.content` rồi mới fetch. Nhưng `guide_posts.content` được populate từ scraping (có thể bị inject từ site bên ngoài). Quan trọng hơn: **không chặn private IP ranges** (127.0.0.1, 10.0.0.0/8, 169.254.169.254 — AWS metadata endpoint, 192.168.0.0/16). Kẻ tấn công có thể:
- Quét port internal network của VPS
- Đánh cắp AWS IAM credentials qua metadata endpoint
- Truy cập dịch vụ nội bộ chỉ bind localhost

**File:** `backend/app/main.py:303-341`

**Code đề xuất:** Thay toàn bộ endpoint:
```python
import ipaddress
import socket

PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/cloud metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

ALLOWED_IMAGE_HOSTS = {
    "hainong.vn",
    "panel.hainong.vn",
    "nongnghiepmoitruong.vn",
    # Thêm các host bạn tin cậy
}

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

def _is_private_ip(host: str) -> bool:
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if any(ip in net for net in PRIVATE_NETWORKS):
                return True
    except (socket.gaierror, ValueError):
        return True  # Fail closed
    return False


@app.get(f"{settings.api_prefix}/content/image-proxy")
def guide_image_proxy(
    url: str = Query(..., min_length=10, max_length=800),
    db: Session = Depends(get_db),
) -> Response:
    image_url = url.strip()
    parsed = urlparse(image_url)
    
    # Validation 1: scheme
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL ảnh không hợp lệ")
    
    # Validation 2: allowlist host (thay vì check DB)
    host = parsed.hostname or ""
    if host not in ALLOWED_IMAGE_HOSTS and not any(host.endswith(f".{h}") for h in ALLOWED_IMAGE_HOSTS):
        raise HTTPException(status_code=403, detail="Host ảnh không được phép")
    
    # Validation 3: chặn private IP ranges (SSRF protection)
    if _is_private_ip(host):
        raise HTTPException(status_code=403, detail="URL trỏ tới network nội bộ")
    
    # Validation 4: cross-check với guide DB (giữ logic cũ)
    known_image = db.scalar(
        select(GuidePost.post_id)
        .where(GuidePost.content.contains(f"IMAGE::{image_url}"))
        .limit(1)
    )
    if known_image is None:
        raise HTTPException(status_code=404, detail="Ảnh không nằm trong thư viện hướng dẫn")
    
    try:
        upstream = requests.get(
            image_url,
            timeout=12,
            stream=True,  # ← stream để check size
            allow_redirects=False,  # ← không follow redirect (chống bypass)
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MarketAI/1.0)",
                "Accept": "image/avif,image/webp,image/apng,image/*",
            },
        )
        upstream.raise_for_status()
        
        # Validation 5: max size
        content_length = int(upstream.headers.get("content-length", 0))
        if content_length > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Ảnh quá lớn")
        
        content = b""
        for chunk in upstream.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_IMAGE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh quá lớn")
    except requests.RequestException as exc:
        raise HTTPException(status_code=404, detail="Không tải được ảnh") from exc
    
    content_type = upstream.headers.get("content-type", "image/jpeg").split(";", 1)[0].strip()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=404, detail="Tệp không phải ảnh")
    
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
```

**Lý do:** SSRF có thể bị dùng để tấn công cloud metadata, scan internal network, hoặc bypass firewall.

---

### [FIX-007] 🔴 Demo Credentials Hardcoded — Tự Tạo Tài Khoản Trong Production

**Vấn đề:** `_ensure_demo_user()` trong `main.py:53-69` chạy khi `seed_on_startup=True` (mặc định). Nó tạo tài khoản `demo@marketai.vn` / `marketai123` — credentials này hardcode trong code và FE form. Nếu deploy production mà quên tắt seed, bất kỳ ai cũng login được.

**Files ảnh hưởng:**
- `backend/app/main.py:53-69`
- `backend/app/core/config.py:14` (`seed_on_startup: bool = True`)
- `frontend/src/App.tsx:144-145`

**Code update `core/config.py`:**
```python
class Settings(BaseSettings):
    ...
    seed_on_startup: bool = False  # ← đổi thành False mặc định
    create_demo_user: bool = False  # ← thêm flag riêng
```

**Code update `main.py:53-69`:**
```python
def _ensure_demo_user(db: Session) -> None:
    if not settings.create_demo_user:
        return
    email = "demo@marketai.vn"
    existing = db.scalar(select(AppUser).where(AppUser.email == email))
    if existing:
        return
    
    # Đọc password từ env, không hardcode
    demo_password = os.getenv("MARKETAI_DEMO_PASSWORD")
    if not demo_password or len(demo_password) < 12:
        raise RuntimeError("MARKETAI_DEMO_PASSWORD phải >= 12 ký tự khi bật create_demo_user")
    
    db.add(
        AppUser(
            email=email,
            display_name="Tài khoản thử",
            password_hash=hash_password(demo_password),
            created_at=datetime.now(UTC),
            is_admin=False,
        )
    )
    db.commit()
```

**Code update `frontend/src/App.tsx:144-145`:**
```typescript
// ❌ XÓA dòng này:
const [authEmail, setAuthEmail] = useState("demo@marketai.vn");
const [authPassword, setAuthPassword] = useState("marketai123");

// ✅ THAY bằng:
const [authEmail, setAuthEmail] = useState("");
const [authPassword, setAuthPassword] = useState("");
```

---

### [FIX-008] 🔴 JWT Secret & Public API Key Có Default Value Trong Code

**Vấn đề:** `core/config.py` có:
```python
auth_token_secret: str = "marketai-local-dev-secret"
public_api_key: str = "marketai-public-demo-key"
```

Nếu deploy production mà quên set env var, app vẫn chạy với secret mặc định — JWT của attacker dễ dàng forge.

**File:** `backend/app/core/config.py:16-18`

**Code đề xuất:**
```python
from pydantic import Field, field_validator

class Settings(BaseSettings):
    ...
    auth_token_secret: str = Field(default="", description="REQUIRED in production")
    public_api_key: str = Field(default="", description="REQUIRED in production")
    iot_api_key: str = Field(default="", description="API key for IoT devices")
    environment: str = Field(default="development", description="development | production")
    
    @field_validator("auth_token_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = info.data.get("environment", "development")
        if env == "production":
            if not v or len(v) < 32:
                raise ValueError("auth_token_secret phải >= 32 ký tự trong production")
            if v in {"marketai-local-dev-secret", "changeme", "secret"}:
                raise ValueError("auth_token_secret là default value, phải đổi")
        if not v:
            return "dev-only-secret-not-for-production-" + "x" * 32
        return v
    
    @field_validator("public_api_key")
    @classmethod
    def validate_public_key(cls, v: str, info) -> str:
        env = info.data.get("environment", "development")
        if env == "production" and (not v or len(v) < 24):
            raise ValueError("public_api_key phải >= 24 ký tự trong production")
        return v or "dev-public-key-not-for-production"
```

**Update `.env.production.example`:**
```bash
MARKETAI_ENVIRONMENT=production
MARKETAI_AUTH_TOKEN_SECRET=  # generate: python -c "import secrets; print(secrets.token_urlsafe(48))"
MARKETAI_PUBLIC_API_KEY=     # generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
MARKETAI_IOT_API_KEY=        # generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
MARKETAI_SEED_ON_STARTUP=false
MARKETAI_CREATE_DEMO_USER=false
MARKETAI_START_SCHEDULER_IN_API=false
```

---

### [FIX-009] 🔴 Không Có Rate Limiting — Brute-Force /auth/login

**Vấn đề:** Login/register/subscribe endpoints không có rate limiting. Attacker có thể thử 10,000 password/phút. bcrypt 12 rounds chỉ làm chậm chứ không chặn.

**Files:**
- `backend/requirements.txt` — thêm `slowapi==0.1.9`
- `backend/app/main.py` — thêm middleware

**Cài thư viện:**
```bash
pip install slowapi==0.1.9
```

**Update `requirements.txt`:**
```
slowapi==0.1.9
```

**Update `main.py` — thêm sau dòng 47:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # Default cho mọi endpoint
    storage_uri="memory://",  # Đơn giản cho MVP; nâng cấp Redis sau
)
```

**Update `main.py` sau khi tạo `app`:**
```python
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)  # ← cần import: from slowapi.middleware import SlowAPIMiddleware
```

**Áp dụng rate limit cho từng endpoint nhạy cảm:**
```python
# main.py:113 — register
@app.post(f"{settings.api_prefix}/auth/register", response_model=AuthTokenOut)
@limiter.limit("5/minute")  # 5 lần/phút per IP
def register(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    ...

# main.py:140 — login
@app.post(f"{settings.api_prefix}/auth/login", response_model=AuthTokenOut)
@limiter.limit("10/minute")  # 10 lần/phút per IP
def login(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    ...

# main.py:274 — subscribe
@app.post(f"{settings.api_prefix}/content/subscribers", response_model=SubscriberOut, status_code=201)
@limiter.limit("3/minute")
def subscribe_to_newsletter(request: Request, payload: SubscriberIn, response: Response, db: Session = Depends(get_db)) -> Subscriber:
    ...

# main.py:751 — IoT telemetry (chống flooding)
@app.post(f"{settings.api_prefix}/sensors/maturity-telemetry", ...)
@limiter.limit("60/minute")  # 1 reading/giây/IP
def ingest_maturity_telemetry(request: Request, ...) -> ...:
    ...
```

**Lưu ý:** `Request` parameter PHẢI được khai báo trong signature thì decorator `@limiter.limit` mới hoạt động.

---

### [FIX-010] 🔴 Custom JWT Implementation — Thay Bằng Thư Viện Chuẩn

**Vấn đề:** `services/auth.py` tự build JWT bằng `hmac` + `base64`. Đúng nguyên tắc bảo mật là **never roll your own crypto**. Custom implementation thiếu:
- Xử lý timing attacks ở nhiều layer
- `not before` (`nbf`) claim
- `audience`/`issuer` claims
- Edge cases base64 padding
- Standardized claim validation

**File:** `backend/app/services/auth.py`

**Cài thư viện:**
```bash
pip install python-jose[cryptography]==3.3.0
```

**Update `requirements.txt`:**
```
python-jose[cryptography]==3.3.0
```

**Code thay thế toàn bộ `services/auth.py`:**
```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models import AppUser

bearer_scheme = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "marketai"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        return False  # Legacy PBKDF2 đã được rehash, từ chối format khác
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def password_needs_rehash(stored_hash: str) -> bool:
    return not stored_hash.startswith(("$2a$", "$2b$", "$2y$"))


def create_access_token(user: AppUser) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.user_id),
        "email": user.email,
        "is_admin": user.is_admin,
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_token_minutes),
        "iss": JWT_ISSUER,
    }
    return jwt.encode(payload, settings.auth_token_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.auth_token_secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token không hợp lệ") from exc


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Cần đăng nhập")
    payload = decode_access_token(credentials.credentials)
    user = db.get(AppUser, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")
    return user


def require_admin(user: AppUser = Depends(current_user)) -> AppUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên có quyền truy cập")
    return user
```

**Lưu ý:** Sau khi sửa, các user cũ với hash PBKDF2 sẽ không login được nữa. Nếu cần backward compat trong dev, giữ lại `_legacy_hash_password` và xử lý tương tự code cũ.

---

### [FIX-011] 🟠 JWT Lưu Trong localStorage — XSS Risk

**Vấn đề:** Frontend lưu JWT token trong `localStorage`. Bất kỳ XSS nào (qua news content, guide content được render bằng `dangerouslySetInnerHTML` hoặc inject từ scraper) đều đọc được token và gửi đi.

**File:** `frontend/src/App.tsx:131-146, 409-414`

**Giải pháp tốt nhất (HIGH):** Migrate sang httpOnly cookie từ backend. Nhưng phức tạp.

**Giải pháp tạm thời (MEDIUM):** Luôn dùng `sessionStorage` (xóa khi đóng tab), bỏ option "remember me" hoặc thay bằng "stay logged in for 24h" qua cookie:

```typescript
// frontend/src/App.tsx — line 131
const [authToken, setAuthToken] = useState(
  () => sessionStorage.getItem("agri_price.token") ?? ""
);
const [user, setUser] = useState<AuthUser | null>(() => {
  try {
    const saved = sessionStorage.getItem("agri_price.user");
    return saved ? (JSON.parse(saved) as AuthUser) : null;
  } catch {
    return null;
  }
});
const [authMode, setAuthMode] = useState<"login" | "register">("login");
const [authName, setAuthName] = useState("");
const [authEmail, setAuthEmail] = useState("");      // ← clear demo
const [authPassword, setAuthPassword] = useState(""); // ← clear demo
// XÓA rememberLogin state
```

```typescript
// frontend/src/App.tsx — handleAuth function
async function handleAuth(mode: "login" | "register") {
  ...
  try {
    const session = mode === "login" ? await login(email, password) : await register(email, password, displayName);
    setAuthToken(session.access_token);
    setUser(session.user);
    sessionStorage.setItem("agri_price.token", session.access_token);
    sessionStorage.setItem("agri_price.user", JSON.stringify(session.user));
    setAuthOpen(false);
    await loadAccountData(session.access_token);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Không đăng nhập được");
  }
}

function logout() {
  setAuthToken("");
  setUser(null);
  setJobs([]);
  setModelRuns([]);
  sessionStorage.removeItem("agri_price.token");
  sessionStorage.removeItem("agri_price.user");
  // Xóa luôn localStorage cũ nếu có
  localStorage.removeItem("agri_price.token");
  localStorage.removeItem("agri_price.user");
}
```

**Bỏ luôn UI checkbox "Ghi nhớ đăng nhập"** — line 596-599.

---

### [FIX-012] 🟠 CORS Quá Permissive

**Vấn đề:** `CORSMiddleware` đang config `allow_methods=["*"]` và `allow_headers=["*"]`. Quá rộng. Nên giới hạn cụ thể.

**File:** `backend/app/main.py:91-97`

**Code đề xuất:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    expose_headers=["Content-Disposition"],  # cho file download
    max_age=3600,
)
```

**Đảm bảo `cors_origins` trong production:**
```python
# core/config.py
cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

@field_validator("cors_origins")
@classmethod
def validate_cors(cls, v: list[str], info) -> list[str]:
    env = info.data.get("environment", "development")
    if env == "production":
        if any("localhost" in origin or "127.0.0.1" in origin for origin in v):
            raise ValueError("cors_origins không được chứa localhost trong production")
        if "*" in v:
            raise ValueError("cors_origins không được dùng wildcard")
    return v
```

---

## 🟠 SECTION 2 — HIGH PRIORITY (HIỆU NĂNG & ARCHITECTURE)

---

### [FIX-013] 🟠 `model-metrics` Endpoint Chạy Backtest Mỗi Request — Cực Kỳ Chậm

**Vấn đề:** Endpoint `GET /analytics/model-metrics` gọi `ForecastEvaluator.backtest()` mỗi request. Trong `evaluator.py:35-65`, hàm này:
1. Query `select(distinct region_id, variety_id) FROM daily_market_prices` (tốn ~50ms)
2. Với mỗi cặp (region, variety) — load 1000 price points
3. Sliding window backtest — tạo hàng trăm dự báo + tính RMSE/MAE

Nếu có 4 region × 4 variety = 16 series, mỗi series trượt ~30 lần × 30 điểm = ~14,400 phép tính per request. Mở Analytics tab = freezes UI 2-5s.

**File:** `backend/app/main.py:490-507`, `backend/app/services/platform_jobs.py:80-108`

**Code đề xuất — Đọc từ DB thay vì compute:**
```python
# main.py — sửa endpoint để đọc từ model_training_runs (đã có)
@app.get(f"{settings.api_prefix}/analytics/model-metrics", response_model=ModelMetrics)
def model_metrics(
    crop: str = Query(default="sau_rieng"),
    db: Session = Depends(get_db),
) -> ModelMetrics:
    """Đọc kết quả từ model_training_runs đã backtest sẵn (chạy bởi scheduler)."""
    latest_run = db.scalar(
        select(ModelTrainingRun)
        .where(ModelTrainingRun.crop_type == crop)
        .where(ModelTrainingRun.status == "thành công")
        .order_by(desc(ModelTrainingRun.started_at))
        .limit(1)
    )
    if latest_run is None:
        # Fallback: trả default (KHÔNG chạy backtest sync)
        return ModelMetrics(
            rmse_usd_per_kg=0.45,
            mae_usd_per_kg=0.32,
            note="Chưa có backtest. Job retrain sẽ chạy theo lịch.",
        )
    rmse_vnd = float(latest_run.rmse_vnd_per_kg) if latest_run.rmse_vnd_per_kg else None
    mae_vnd = float(latest_run.mae_vnd_per_kg) if latest_run.mae_vnd_per_kg else None
    return ModelMetrics(
        rmse_vnd_per_kg=rmse_vnd,
        mae_vnd_per_kg=mae_vnd,
        rmse_usd_per_kg=round(rmse_vnd / 24500, 4) if rmse_vnd else 0.45,
        mae_usd_per_kg=round(mae_vnd / 24500, 4) if mae_vnd else 0.32,
        lookback_days=60,
        forecast_horizon_days=30,
        backtest_samples=latest_run.backtest_samples,
        evaluated_series=latest_run.evaluated_series,
        note=latest_run.note,
    )
```

**Đồng thời:** trong `market_intelligence.py:175-226` (hàm `alerts`), KHÔNG gọi `ForecastEvaluator.backtest()` nữa, dùng cùng pattern đọc từ `ModelTrainingRun`:

```python
# market_intelligence.py — hàm alerts()
def alerts(self, crop: str, region_id: int, variety_id: int) -> list[dict]:
    ...
    # ❌ XÓA: metrics = ForecastEvaluator(self.db, ...).backtest()
    # ✅ THAY bằng:
    latest_run = self.db.scalar(
        select(ModelTrainingRun)
        .where(ModelTrainingRun.crop_type == crop)
        .where(ModelTrainingRun.status == "thành công")
        .order_by(desc(ModelTrainingRun.started_at))
        .limit(1)
    )
    if latest_run and latest_run.rmse_vnd_per_kg:
        alerts.append({
            "level": "Model",
            "title": "Sai số backtest",
            "message": f"RMSE backtest gần nhất khoảng {round(float(latest_run.rmse_vnd_per_kg)):,} VND/kg.",
        })
    ...
```

**Lý do:** Backtest là job offline, không thuộc request hot path.

---

### [FIX-014] 🟠 Không Có Caching — Mọi Request Đều Hit Database

**Vấn đề:** `forecast`, `ticker-prices`, `top-movers`, `heatmap`, `market-index`, `compare-markets`, `data-quality`, `source-health`, `news`, `guides` — tất cả đều query DB mỗi request. Nhiều endpoint trong số này chạy heavy computation trong Python.

**File mới:** `backend/app/core/cache.py`

```python
"""Simple in-memory TTL cache với optional Redis upgrade path."""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class TTLCache:
    def __init__(self, max_entries: int = 512) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            if len(self._store) >= self._max_entries:
                # LRU lite: xóa entry cũ nhất
                oldest = min(self._store.items(), key=lambda kv: kv[1][1])
                del self._store[oldest[0]]
            self._store[key] = (value, time.time() + ttl_seconds)

    def invalidate(self, prefix: str = "") -> int:
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)


_cache = TTLCache()


def cache_key(prefix: str, **params: Any) -> str:
    payload = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


def cached(prefix: str, ttl_seconds: int = 600) -> Callable:
    """Decorator để cache return value của function (sync only)."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build key từ kwargs (bỏ db session)
            key_params = {k: v for k, v in kwargs.items() if k != "db" and k != "_"}
            key = cache_key(f"{prefix}:{func.__name__}", **key_params)
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl_seconds)
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix: str = "") -> int:
    return _cache.invalidate(prefix)
```

**Áp dụng vào main.py — cache các endpoint heavy:**
```python
from app.core.cache import cached, invalidate_cache

# ticker-prices: thay đổi vài lần/ngày, cache 5 phút
@app.get(f"{settings.api_prefix}/analytics/ticker-prices", response_model=list[HistoricalPricePoint])
@cached(prefix="ticker", ttl_seconds=300)
def ticker_prices(crop: str = Query(default="sau_rieng"), limit: int = Query(default=40, ge=1, le=200), db: Session = Depends(get_db)) -> list[dict]:
    ...

# forecast: dữ liệu thay đổi 1 lần/ngày, cache 1 giờ
@app.get(f"{settings.api_prefix}/analytics/forecast-30-days", response_model=list[ForecastPoint])
@cached(prefix="forecast", ttl_seconds=3600)
def forecast_30_days(...):
    ...

# top-movers, heatmap, market-index: cache 15 phút
@cached(prefix="movers", ttl_seconds=900)
def top_movers(...): ...

@cached(prefix="heatmap", ttl_seconds=900)
def heatmap(...): ...

@cached(prefix="index", ttl_seconds=900)
def market_index(...): ...

# News list: cache 5 phút
@cached(prefix="news", ttl_seconds=300)
def news(...): ...

# Data quality: cache 30 phút
@cached(prefix="quality", ttl_seconds=1800)
def data_quality(...): ...
```

**Quan trọng:** Sau khi job scrape/retrain chạy xong, invalidate cache:
```python
# services/platform_jobs.py — sau mỗi job thành công
from app.core.cache import invalidate_cache

def run_scrape(self) -> dict:
    ...
    self._finish_job(job, "thành công", summary)
    invalidate_cache("ticker")
    invalidate_cache("forecast")
    invalidate_cache("movers")
    invalidate_cache("heatmap")
    invalidate_cache("index")
    invalidate_cache("quality")
    return summary

def run_news_scrape(self) -> dict:
    ...
    invalidate_cache("news")
```

---

### [FIX-015] 🟠 N+1 Query Pattern Trong `_quality_summary`

**Vấn đề:** `services/platform_jobs.py:140-142`:
```python
for region in production_regions:
    for variety in varieties:
        quality = service.data_quality(crop, region_id=region.region_id, variety_id=variety.variety_id)
```

Mỗi call `data_quality()` → query 1000 rows từ `daily_market_prices`. Với 4 region × 4 variety = 16 query, mỗi query 1000 rows. Trong job scheduler chạy 4 crops = 64 query/run.

**File:** `backend/app/services/platform_jobs.py:116-170`, `backend/app/services/market_intelligence.py:25-55`

**Code đề xuất — Bulk query một lần, group trong Python:**
```python
# market_intelligence.py — thêm method mới
def data_quality_bulk(self, crop: str, region_ids: list[int], variety_ids: list[int]) -> dict[tuple[int, int], dict]:
    """Tính data_quality cho nhiều cặp (region, variety) bằng 1 query."""
    rows = self.db.execute(
        select(
            DailyMarketPrice.region_id,
            DailyMarketPrice.variety_id,
            DailyMarketPrice.exchange_source,
            DailyMarketPrice.record_timestamp,
        )
        .where(DailyMarketPrice.crop_type == crop)
        .where(DailyMarketPrice.region_id.in_(region_ids))
        .where(DailyMarketPrice.variety_id.in_(variety_ids))
        .order_by(DailyMarketPrice.record_timestamp.desc())
    ).all()
    
    grouped: dict[tuple[int, int], list] = defaultdict(list)
    for row in rows:
        grouped[(row.region_id, row.variety_id)].append(row)
    
    result = {}
    for (region_id, variety_id), pair_rows in grouped.items():
        # Cap 1000 rows per pair (giống logic cũ)
        pair_rows = pair_rows[:1000]
        total = len(pair_rows)
        derived = sum(1 for r in pair_rows if _is_derived_source(r.exchange_source))
        observed = total - derived
        sources = sorted({r.exchange_source for r in pair_rows if r.exchange_source})
        latest = max((r.record_timestamp for r in pair_rows), default=None)
        freshness_days = self._freshness_days(latest)
        score = self._quality_score(total, observed, len(sources), freshness_days)
        result[(region_id, variety_id)] = {
            "score": score,
            "history_points": total,
            "observed_points": observed,
            "synthetic_points": derived,
            "freshness_days": freshness_days,
            "risk_flags": self._risk_flags(score, observed, derived, freshness_days),
        }
    return result
```

**Update `_quality_summary` trong `platform_jobs.py`:**
```python
def _quality_summary(self, crop: str) -> dict:
    service = MarketIntelligenceService(self.db)
    varieties = self.db.scalars(
        select(DurianVariety).where(DurianVariety.crop_type == crop).order_by(DurianVariety.variety_id)
    ).all()
    regions = self.db.scalars(
        select(ProductionRegion)
        .join(DailyMarketPrice, DailyMarketPrice.region_id == ProductionRegion.region_id)
        .where(DailyMarketPrice.crop_type == crop)
        .order_by(ProductionRegion.region_id)
        .distinct()
    ).all()
    production_regions = [r for r in regions if r.province and r.region_name not in {"Thị trường Việt Nam", "Chợ đầu mối TP.HCM"}]
    
    region_ids = [r.region_id for r in production_regions]
    variety_ids = [v.variety_id for v in varieties]
    
    # ✅ MỘT query thay vì 16
    quality_map = service.data_quality_bulk(crop, region_ids, variety_ids)
    
    scores, weak_pairs, stale_pairs, missing_pairs = [], [], [], 0
    for region in production_regions:
        for variety in varieties:
            quality = quality_map.get((region.region_id, variety.variety_id))
            if not quality or not quality["history_points"]:
                missing_pairs += 1
                continue
            scores.append(quality["score"])
            pair = {
                "region_id": region.region_id, "province": region.province,
                "variety_id": variety.variety_id, "variety": variety.name,
                "score": quality["score"], "history_points": quality["history_points"],
                "observed_points": quality["observed_points"], "freshness_days": quality["freshness_days"],
                "risk_flags": quality["risk_flags"],
            }
            if quality["score"] < 80:
                weak_pairs.append(pair)
            if quality["freshness_days"] is None or quality["freshness_days"] > 3:
                stale_pairs.append(pair)
    
    return {
        "crop": crop,
        "pairs_checked": len(production_regions) * len(varieties),
        "missing_pairs": missing_pairs,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "weak_pairs": weak_pairs[:12],
        "stale_pairs": stale_pairs[:12],
    }
```

---

### [FIX-016] 🟠 `top_movers` & `heatmap` Load 10,000 Rows Rồi Process Trong Python

**Vấn đề:** `market_intelligence.py:96-173`:
```python
rows = DataLoader(self.db).historical_prices(crop_type=crop, quality_grade="Loại A", limit=10000)
grouped: dict = defaultdict(list)
for row in rows:
    ...
```

Load 10,000 rows mỗi request, process trong Python — DB-side aggregation sẽ nhanh hơn 10-50x.

**File:** `backend/app/services/market_intelligence.py:96-173`

**Code đề xuất — Dùng SQL aggregation:**
```python
def top_movers(self, crop: str, limit: int = 8) -> dict:
    """Tính gainers/losers bằng SQL window function thay vì load 10k rows."""
    from sqlalchemy import func, text
    
    # Latest price per (variety, region)
    latest_subq = (
        select(
            DailyMarketPrice.variety_id,
            DailyMarketPrice.region_id,
            DailyMarketPrice.max_price_vnd.label("latest_price"),
            DailyMarketPrice.record_timestamp.label("latest_ts"),
            func.row_number().over(
                partition_by=(DailyMarketPrice.variety_id, DailyMarketPrice.region_id),
                order_by=DailyMarketPrice.record_timestamp.desc(),
            ).label("rn"),
        )
        .where(DailyMarketPrice.crop_type == crop)
        .where(DailyMarketPrice.quality_grade == "Loại A")
        .where(DailyMarketPrice.max_price_vnd.is_not(None))
        .subquery()
    )
    
    # 7-day-ago price per (variety, region)  
    previous_subq = (
        select(
            DailyMarketPrice.variety_id,
            DailyMarketPrice.region_id,
            DailyMarketPrice.max_price_vnd.label("previous_price"),
            func.row_number().over(
                partition_by=(DailyMarketPrice.variety_id, DailyMarketPrice.region_id),
                order_by=DailyMarketPrice.record_timestamp.desc(),
            ).label("rn"),
        )
        .where(DailyMarketPrice.crop_type == crop)
        .where(DailyMarketPrice.quality_grade == "Loại A")
        .where(DailyMarketPrice.max_price_vnd.is_not(None))
        .subquery()
    )
    
    rows = self.db.execute(
        select(
            DurianVariety.name.label("variety"),
            ProductionRegion.region_name.label("region"),
            ProductionRegion.province,
            latest_subq.c.latest_price,
            previous_subq.c.previous_price,
            latest_subq.c.latest_ts,
        )
        .join(DurianVariety, DurianVariety.variety_id == latest_subq.c.variety_id)
        .join(ProductionRegion, ProductionRegion.region_id == latest_subq.c.region_id)
        .join(previous_subq, and_(
            previous_subq.c.variety_id == latest_subq.c.variety_id,
            previous_subq.c.region_id == latest_subq.c.region_id,
            previous_subq.c.rn == 8,  # 7 ngày trước (1-indexed)
        ))
        .where(latest_subq.c.rn == 1)
        .where(ProductionRegion.province.is_not(None))
    ).all()
    
    movers = []
    for row in rows:
        if not row.latest_price or not row.previous_price:
            continue
        latest = float(row.latest_price)
        previous = float(row.previous_price)
        change_vnd = latest - previous
        change_pct = change_vnd / previous * 100
        movers.append({
            "variety": row.variety,
            "region": row.region,
            "province": row.province,
            "latest_price_vnd": round(latest, 2),
            "previous_price_vnd": round(previous, 2),
            "change_vnd": round(change_vnd, 2),
            "change_pct": round(change_pct, 2),
            "timestamp": row.latest_ts,
        })
    
    return {
        "gainers": sorted(movers, key=lambda m: m["change_pct"], reverse=True)[:limit],
        "losers": sorted(movers, key=lambda m: m["change_pct"])[:limit],
    }
```

**Lý do:** SQL aggregate xử lý trên index, scan ít rows. Python load 10k rows + groupby là worst case.

---

### [FIX-017] 🟠 `cleanup_news_archive()` & `_normalize_news_records()` Chạy Trên Mỗi GET

**Vấn đề:** `services/content_portal.py:117-128`:
```python
def latest_news(self, limit: int = 24, ...):
    self.cleanup_news_archive()       # ← scan 2000 rows
    self._normalize_news_records()    # ← scan 600 rows + UPDATE if changed
    stmt = select(NewsArticle)...
```

Mỗi request `GET /content/news` (page chính có thể gọi 4-5 lần/phút) → scan + write DB. Cực phí tài nguyên + lock rows.

**File:** `backend/app/services/content_portal.py:116-128`

**Code đề xuất:** Tách cleanup/normalize ra khỏi read path, chỉ chạy trong job:
```python
def latest_news(self, limit: int = 24, category: str | None = None) -> list[NewsArticle]:
    # ❌ XÓA: self.cleanup_news_archive() và self._normalize_news_records()
    stmt = select(NewsArticle).order_by(desc(NewsArticle.published_at), desc(NewsArticle.scraped_at))
    if category:
        stmt = stmt.where(NewsArticle.category == category)
    rows = self.db.scalars(stmt.limit(max(limit * NEWS_CANDIDATE_MULTIPLIER, NEWS_MIN_CANDIDATES))).all()
    combined = sorted([r for r in rows if _is_keepable_news_article(r)], key=_news_time_key, reverse=True)
    if combined:
        return combined[:limit]
    # Chỉ seed fallback khi DB rỗng
    self.seed_fallback_news()
    rows = self.db.scalars(stmt.limit(max(limit * NEWS_CANDIDATE_MULTIPLIER, NEWS_MIN_CANDIDATES))).all()
    return sorted([r for r in rows if _is_keepable_news_article(r)], key=_news_time_key, reverse=True)[:limit]
```

**Trong `scrape_news()` (đã được scheduler gọi 6h/lần) — gọi cleanup ở đây:**
```python
def scrape_news(self) -> dict:
    ...
    cleanup = self.cleanup_news_archive()
    self._normalize_news_records()
    ...
```

---

### [FIX-018] 🟠 Backend Scheduler Chạy Trong Cùng Process API (Mặc Định)

**Vấn đề:** `core/config.py:19`:
```python
start_scheduler_in_api: bool = True
```

Mặc định scheduler chạy trong cùng Python process với FastAPI. Khi scheduler đang scrape (CPU/IO heavy), API requests bị chậm. Chỉ `docker-compose.prod.yml` mới override `MARKETAI_START_SCHEDULER_IN_API: "false"`. Dev và non-Docker prod sẽ bị ảnh hưởng.

**File:** `backend/app/core/config.py:19`

**Code đề xuất:**
```python
start_scheduler_in_api: bool = False  # ← đổi default
```

Update README/DEPLOYMENT.md để hướng dẫn chạy worker riêng:
```bash
# Terminal 1: API
uvicorn app.main:app --port 8010

# Terminal 2: Worker
python -m app.worker
```

---

### [FIX-019] 🟠 SQLite vs PostgreSQL Schema Drift — Không Có Alembic

**Vấn đề:** Có 3 nguồn schema không đồng bộ:
1. `backend/app/models.py` (SQLAlchemy declarative)
2. `backend/migrations/001_init_timescale.sql` (PostgreSQL/TimescaleDB)
3. `backend/app/db.py` (`_ensure_runtime_columns` patches SQLite)

Bất kỳ schema change nào cũng phải update 3 nơi → drift sớm muộn.

**File ảnh hưởng:** Tất cả file trên + thêm Alembic.

**Cài Alembic:**
```bash
pip install alembic==1.14.0
```

**Update `requirements.txt`:**
```
alembic==1.14.0
```

**Setup ban đầu:**
```bash
cd backend
alembic init migrations_alembic
```

**Update `migrations_alembic/env.py`:**
```python
from app.db import Base
from app.core.config import get_settings
import app.models  # noqa - load all models

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings().database_url)
```

**Workflow mới:**
```bash
# Tự động sinh migration từ models.py
alembic revision --autogenerate -m "add is_admin"

# Apply
alembic upgrade head
```

**Xóa khỏi `db.py`:**
```python
# ❌ XÓA toàn bộ _ensure_runtime_columns() và _ensure_runtime_indexes()
def init_db() -> None:
    """Migrations giờ do Alembic quản lý — gọi `alembic upgrade head` trước khi start API."""
    from app import models  # noqa: F401
    # KHÔNG còn create_all hay ALTER TABLE thủ công
```

**Trong production startup script (Dockerfile / entrypoint):**
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8010
```

---

### [FIX-020] 🟠 Docker Compose Dùng `postgres:16-alpine` Nhưng Migration Cần TimescaleDB

**Vấn đề:** `migrations/001_init_timescale.sql:1`:
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

Nhưng `docker-compose.prod.yml:3` dùng:
```yaml
postgres:
  image: postgres:16-alpine
```

Image này **không có** TimescaleDB. Lệnh `CREATE EXTENSION` sẽ fail. Hypertable không được tạo. Performance time-series sẽ tệ.

**File:** `deploy/docker-compose.prod.yml:2-3`

**Code đề xuất:**
```yaml
postgres:
  image: timescale/timescaledb:2.17.2-pg16
  restart: unless-stopped
  environment:
    POSTGRES_DB: ${POSTGRES_DB:-marketai}
    POSTGRES_USER: ${POSTGRES_USER:-marketai}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in deploy/.env}
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./postgres-backup:/backups  # ← thêm cho backup
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-marketai} -d ${POSTGRES_DB:-marketai}"]
    interval: 10s
    timeout: 5s
    retries: 8
  shm_size: 256m  # ← TimescaleDB cần shared memory
```

---

## 🟡 SECTION 3 — MEDIUM PRIORITY (FRONTEND ARCHITECTURE)

---

### [FIX-021] 🟡 App.tsx Là God Component Với 26 useState

**Vấn đề:** `frontend/src/App.tsx` có 26+ useState, ~800 lines, manage cả analytics + news + guides + auth. Mọi state change re-render toàn bộ tree.

**File:** `frontend/src/App.tsx` (toàn bộ)

**Code đề xuất — Tách thành 3 Context:**

**File mới `frontend/src/contexts/AuthContext.tsx`:**
```typescript
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchPlatformJobs, fetchModelRuns, fetchWatchlist, login as apiLogin, register as apiRegister, type AuthUser, type ModelTrainingRun, type PlatformJobRun, type WatchlistItem } from "../lib/api";

type AuthContextValue = {
  token: string;
  user: AuthUser | null;
  jobs: PlatformJobRun[];
  modelRuns: ModelTrainingRun[];
  watchlist: WatchlistItem[];
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY_TOKEN = "agri_price.token";
const STORAGE_KEY_USER = "agri_price.user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(STORAGE_KEY_TOKEN) ?? "");
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY_USER);
      return saved ? JSON.parse(saved) as AuthUser : null;
    } catch { return null; }
  });
  const [jobs, setJobs] = useState<PlatformJobRun[]>([]);
  const [modelRuns, setModelRuns] = useState<ModelTrainingRun[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const [w, j, m] = await Promise.all([
        fetchWatchlist(token),
        user?.is_admin ? fetchPlatformJobs(token) : Promise.resolve([]),
        user?.is_admin ? fetchModelRuns(token) : Promise.resolve([]),
      ]);
      setWatchlist(w);
      setJobs(j);
      setModelRuns(m);
    } catch {
      // silent fail
    }
  }, [token, user]);

  useEffect(() => { void refresh(); }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const session = await apiLogin(email, password);
    setToken(session.access_token);
    setUser(session.user);
    sessionStorage.setItem(STORAGE_KEY_TOKEN, session.access_token);
    sessionStorage.setItem(STORAGE_KEY_USER, JSON.stringify(session.user));
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    const session = await apiRegister(email, password, name);
    setToken(session.access_token);
    setUser(session.user);
    sessionStorage.setItem(STORAGE_KEY_TOKEN, session.access_token);
    sessionStorage.setItem(STORAGE_KEY_USER, JSON.stringify(session.user));
  }, []);

  const logout = useCallback(() => {
    setToken("");
    setUser(null);
    setJobs([]);
    setModelRuns([]);
    setWatchlist([]);
    sessionStorage.removeItem(STORAGE_KEY_TOKEN);
    sessionStorage.removeItem(STORAGE_KEY_USER);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, jobs, modelRuns, watchlist, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside <AuthProvider>");
  return ctx;
}
```

**File mới `frontend/src/contexts/MarketContext.tsx`:**
```typescript
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as api from "../lib/api";

type Section = "home" | "analytics" | "news" | "guides" | "methodology";

type MarketContextValue = {
  section: Section;
  setSection: (s: Section) => void;
  crop: api.CropType;
  setCrop: (c: api.CropType) => void;
  regionId: number;
  setRegionId: (id: number) => void;
  varietyId: number;
  setVarietyId: (id: number) => void;
  data: {
    historical: api.PricePoint[];
    forecast: api.ForecastPoint[];
    signals: api.TradingSignal[];
    metrics: api.ModelMetrics | null;
    quality: api.DataQuality | null;
    topMovers: api.TopMovers;
    heatmap: api.HeatmapCell[];
    alerts: api.StrategyAlert[];
  };
  regions: api.Region[];
  varieties: api.Variety[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

const MarketContext = createContext<MarketContextValue | null>(null);

export function MarketProvider({ children }: { children: ReactNode }) {
  const [section, setSection] = useState<Section>("home");
  const [crop, setCrop] = useState<api.CropType>("sau_rieng");
  const [regionId, setRegionId] = useState(1);
  const [varietyId, setVarietyId] = useState(1);
  const [regions, setRegions] = useState<api.Region[]>([]);
  const [varieties, setVarieties] = useState<api.Variety[]>([]);
  const [data, setData] = useState({
    historical: [] as api.PricePoint[],
    forecast: [] as api.ForecastPoint[],
    signals: [] as api.TradingSignal[],
    metrics: null as api.ModelMetrics | null,
    quality: null as api.DataQuality | null,
    topMovers: { gainers: [], losers: [] } as api.TopMovers,
    heatmap: [] as api.HeatmapCell[],
    alerts: [] as api.StrategyAlert[],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (section !== "analytics") return;
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    try {
      const regionsPayload = await api.fetchRegions(crop);
      const nextRegionId = regionsPayload.some(r => r.region_id === regionId) ? regionId : regionsPayload[0]?.region_id;
      if (!nextRegionId) {
        setError("Chưa có dữ liệu giá cho sản phẩm này.");
        return;
      }
      const varietiesPayload = await api.fetchAvailableVarieties(crop, nextRegionId);
      const nextVarietyId = varietiesPayload.some(v => v.variety_id === varietyId) ? varietyId : varietiesPayload[0]?.variety_id;
      
      setRegions(regionsPayload);
      setVarieties(varietiesPayload);
      if (nextRegionId !== regionId) setRegionId(nextRegionId);
      if (nextVarietyId && nextVarietyId !== varietyId) setVarietyId(nextVarietyId);
      
      if (!nextVarietyId) {
        setError("Chưa có dữ liệu giá cho tỉnh này.");
        return;
      }
      
      const [historical, forecast, signals, metrics, quality, movers, heatmap, alerts] = await Promise.all([
        api.fetchHistorical(crop, nextRegionId, nextVarietyId),
        api.fetchForecast(crop, nextRegionId, nextVarietyId),
        api.fetchSignals(crop, nextRegionId, nextVarietyId),
        api.fetchMetrics(crop, nextRegionId, nextVarietyId),
        api.fetchDataQuality(crop, nextRegionId, nextVarietyId),
        api.fetchTopMovers(crop),
        api.fetchHeatmap(crop),
        api.fetchStrategyAlerts(crop, nextRegionId, nextVarietyId),
      ]);
      setData({ historical, forecast, signals, metrics, quality, topMovers: movers, heatmap, alerts });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Lỗi API");
    } finally {
      setLoading(false);
    }
    return () => controller.abort();
  }, [section, crop, regionId, varietyId]);

  useEffect(() => { void reload(); }, [reload]);

  const value = useMemo<MarketContextValue>(() => ({
    section, setSection, crop, setCrop, regionId, setRegionId, varietyId, setVarietyId,
    data, regions, varieties, loading, error, reload,
  }), [section, crop, regionId, varietyId, data, regions, varieties, loading, error, reload]);

  return <MarketContext.Provider value={value}>{children}</MarketContext.Provider>;
}

export function useMarket() {
  const ctx = useContext(MarketContext);
  if (!ctx) throw new Error("useMarket must be inside <MarketProvider>");
  return ctx;
}
```

**File mới `frontend/src/contexts/ContentContext.tsx`:** (tương tự cho news/guides)

**App.tsx mới (rút gọn còn ~150 lines):**
```typescript
import { lazy, Suspense } from "react";
import { AuthProvider } from "./contexts/AuthContext";
import { MarketProvider, useMarket } from "./contexts/MarketContext";
import { ContentProvider } from "./contexts/ContentContext";
import { TopBar } from "./components/TopBar";
import { SiteFooter } from "./components/SiteFooter";

const HomePage = lazy(() => import("./components/HomePage").then(m => ({ default: m.HomePage })));
const AnalyticsPage = lazy(() => import("./components/AnalyticsPage").then(m => ({ default: m.AnalyticsPage })));
const NewsPortal = lazy(() => import("./components/NewsPortal").then(m => ({ default: m.NewsPortal })));
const GuideLibrary = lazy(() => import("./components/GuideLibrary").then(m => ({ default: m.GuideLibrary })));

function AppShell() {
  const { section } = useMarket();
  return (
    <main className="app-shell">
      <TopBar />
      <Suspense fallback={<div>Đang tải...</div>}>
        {section === "home" && <HomePage />}
        {section === "analytics" && <AnalyticsPage />}
        {section === "news" && <NewsPortal />}
        {section === "guides" && <GuideLibrary />}
      </Suspense>
      <SiteFooter />
    </main>
  );
}

export function App() {
  return (
    <AuthProvider>
      <ContentProvider>
        <MarketProvider>
          <AppShell />
        </MarketProvider>
      </ContentProvider>
    </AuthProvider>
  );
}
```

**Lý do:** Mỗi consumer chỉ subscribe context nó cần. NewsPortal không re-render khi user đổi crop trong analytics.

---

### [FIX-022] 🟡 MasterChart Re-render Mỗi Lần Parent State Change

**Vấn đề:** `MasterChart.tsx:58-86` — mọi tính toán `signalByDate`, `historicalByDate`, `rows` chạy mỗi render. Component không memoized.

**File:** `frontend/src/components/MasterChart.tsx`

**Code đề xuất:**
```typescript
import { memo, useMemo } from "react";
// ... existing imports

export const MasterChart = memo(function MasterChart({ historical, forecast, signals, showPrice, showForecast, showRain, showSignals }: Props) {
  const rows = useMemo<ChartRow[]>(() => {
    const signalByDate = new Map(signals.map(s => [toDateKey(s.timestamp), s.price_vnd]));
    
    // Group historical by date — dùng Map.get/set thay vì spread (O(n) thay O(n²))
    const historicalByDate = new Map<string, PricePoint[]>();
    for (const point of historical) {
      const dateKey = toDateKey(point.timestamp);
      const list = historicalByDate.get(dateKey);
      if (list) list.push(point);
      else historicalByDate.set(dateKey, [point]);
    }
    
    return [
      ...Array.from(historicalByDate.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([dateKey, points]) => {
          const point = pickDailyPoint(points);
          const rain = average(points.map(r => r.precipitation_mm).filter((v): v is number => typeof v === "number"));
          return {
            dateKey,
            price: point.max_price_vnd ?? undefined,
            rain,
            signalPrice: signalByDate.get(dateKey),
          };
        }),
      ...forecast.map(p => ({
        dateKey: toDateKey(p.timestamp),
        forecast: p.forecast_price_vnd,
      })),
    ];
  }, [historical, forecast, signals]);

  const signalDots = useMemo(
    () => rows.filter(r => typeof r.signalPrice === "number"),
    [rows]
  );

  return (
    <section className="chart-section">
      {/* ...existing JSX, thay rows.filter(...).map(...) bằng signalDots.map(...) */}
    </section>
  );
});
```

**Tương tự:** Wrap các component sau với `React.memo`:
- `IntelligencePanels`
- `MarketBrain`
- `MetricsDashboard`
- `TechnicalPanel`
- `DataGrid`
- `TickerTape`

---

### [FIX-023] 🟡 Không Có Request Cancellation — Race Condition Khi Chuyển Tab Nhanh

**Vấn đề:** `App.tsx:184-276` `loadData()` gọi 11 API cùng lúc. Nếu user click crop khác giữa chừng, requests cũ vẫn trả về và overwrite state mới.

**File:** `frontend/src/lib/api.ts`, `frontend/src/contexts/MarketContext.tsx`

**Code đề xuất — Thêm AbortController vào api.ts:**
```typescript
// frontend/src/lib/api.ts
async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(apiUrl(url), { headers: jsonHeaders, signal });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchHistorical(crop: CropType, regionId: number, varietyId: number, qualityGrade?: string, signal?: AbortSignal) {
  const gradeParam = qualityGrade ? `&quality_grade=${encodeURIComponent(qualityGrade)}` : "";
  return getJson<PricePoint[]>(
    `/api/v1/analytics/historical-prices?crop=${crop}&region_id=${regionId}&variety=${varietyId}${gradeParam}&limit=1000`,
    signal
  );
}
// Apply signal cho tất cả các fetch* functions...
```

**Update MarketContext:**
```typescript
const reload = useCallback(async () => {
  if (section !== "analytics") return;
  const controller = new AbortController();
  setLoading(true);
  try {
    // ... pass controller.signal to all fetch calls
    const [historical, forecast, ...] = await Promise.all([
      api.fetchHistorical(crop, nextRegionId, nextVarietyId, undefined, controller.signal),
      api.fetchForecast(crop, nextRegionId, nextVarietyId, controller.signal),
      // ...
    ]);
  } catch (err) {
    if ((err as Error).name === "AbortError") return;  // ignore
    setError(err instanceof Error ? err.message : "Lỗi API");
  } finally {
    setLoading(false);
  }
  return () => controller.abort();
}, [section, crop, regionId, varietyId]);

useEffect(() => {
  const cleanup = reload();
  return () => { cleanup.then(fn => fn?.()); };
}, [reload]);
```

---

### [FIX-024] 🟡 Frontend Không Limit `historical_prices` Theo Days Filter

**Vấn đề:** `api.ts:237-242`:
```typescript
export function fetchHistorical(crop, regionId, varietyId, qualityGrade?) {
  return getJson<PricePoint[]>(
    `/api/v1/analytics/historical-prices?...&limit=1000`  // ← luôn 1000
  );
}
```

User chọn 30 ngày nhưng vẫn fetch 1000 rows → tải 30x dữ liệu thừa.

**File:** `frontend/src/lib/api.ts:237-242`, `frontend/src/contexts/MarketContext.tsx`

**Code đề xuất:**
```typescript
// api.ts
export function fetchHistorical(
  crop: CropType,
  regionId: number,
  varietyId: number,
  options: { qualityGrade?: string; limit?: number; signal?: AbortSignal } = {}
) {
  const { qualityGrade, limit = 200, signal } = options;
  const gradeParam = qualityGrade ? `&quality_grade=${encodeURIComponent(qualityGrade)}` : "";
  return getJson<PricePoint[]>(
    `/api/v1/analytics/historical-prices?crop=${crop}&region_id=${regionId}&variety=${varietyId}${gradeParam}&limit=${limit}`,
    signal
  );
}

// MarketContext — pass days vào limit
const historical = await api.fetchHistorical(crop, nextRegionId, nextVarietyId, {
  limit: Math.max(days * 4, 60),  // 4x days để có buffer cho multiple sources/grades
  signal: controller.signal,
});
```

---

### [FIX-025] 🟡 SEO — index.html Không Có Meta Tags

**Vấn đề:** `frontend/index.html:7` chỉ có `<title>Nông nghiệp số</title>`. Không có description, og:tags, canonical, structured data. Google không hiển thị rich snippet.

**File:** `frontend/index.html`

**Code đề xuất — Thay toàn bộ:**
```html
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    
    <title>Nông Nghiệp Số — Dự Báo Giá Nông Sản Việt Nam</title>
    <meta name="description" content="Theo dõi và dự báo giá sầu riêng, cà phê, hồ tiêu, lúa theo vùng trồng. Cập nhật giá hàng ngày từ các thị trường nông sản chính tại Việt Nam." />
    <meta name="keywords" content="giá sầu riêng, giá cà phê, dự báo giá nông sản, giá hồ tiêu, giá lúa, nông nghiệp số" />
    <meta name="robots" content="index, follow" />
    <meta name="author" content="Nông Nghiệp Số" />
    <link rel="canonical" href="https://nongnghiepso.vn/" />
    
    <!-- Open Graph (Facebook, Zalo) -->
    <meta property="og:type" content="website" />
    <meta property="og:locale" content="vi_VN" />
    <meta property="og:site_name" content="Nông Nghiệp Số" />
    <meta property="og:title" content="Dự Báo Giá Nông Sản Việt Nam" />
    <meta property="og:description" content="Theo dõi giá sầu riêng, cà phê, hồ tiêu, lúa và dự báo 30 ngày theo vùng trồng." />
    <meta property="og:url" content="https://nongnghiepso.vn/" />
    <meta property="og:image" content="https://nongnghiepso.vn/og-cover.jpg" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Nông Nghiệp Số — Dự Báo Giá Nông Sản" />
    <meta name="twitter:description" content="Dự báo giá nông sản Việt Nam, cập nhật hàng ngày." />
    <meta name="twitter:image" content="https://nongnghiepso.vn/og-cover.jpg" />
    
    <!-- Performance hints -->
    <link rel="preconnect" href="https://api.nongnghiepso.vn" />
    <link rel="dns-prefetch" href="https://api.nongnghiepso.vn" />
    
    <!-- Structured data: Organization -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "Nông Nghiệp Số",
      "url": "https://nongnghiepso.vn",
      "logo": "https://nongnghiepso.vn/logo.png",
      "description": "Nền tảng dự báo giá nông sản phi lợi nhuận tại Việt Nam"
    }
    </script>
    
    <!-- WebSite + SearchAction (sitelinks search box) -->
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "Nông Nghiệp Số",
      "url": "https://nongnghiepso.vn"
    }
    </script>
  </head>
  <body>
    <noscript>
      <p>Vui lòng bật JavaScript để xem giá nông sản và dự báo. Bạn cũng có thể truy cập 
      <a href="https://api.nongnghiepso.vn/api/v1/public/prices?crop=sau_rieng">API public</a> 
      với API key.</p>
    </noscript>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Tạo file `frontend/public/sitemap.xml`:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://nongnghiepso.vn/</loc><priority>1.0</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&crop=sau_rieng</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&crop=ca_phe</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&crop=ho_tieu</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=analytics&crop=lua</loc><priority>0.9</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=news</loc><priority>0.7</priority></url>
  <url><loc>https://nongnghiepso.vn/?section=guides</loc><priority>0.7</priority></url>
</urlset>
```

**Tạo file `frontend/public/robots.txt`:**
```
User-agent: *
Allow: /
Disallow: /api/

Sitemap: https://nongnghiepso.vn/sitemap.xml
```

---

### [FIX-026] 🟡 SEO — SPA Không Có SSR/SSG, News & Guides Không Index Được

**Vấn đề:** Toàn bộ app là Vite SPA. Google bot có thể chạy JS nhưng news/guides — tài sản SEO chính của trang nông nghiệp — load qua JavaScript, có thể không được index đầy đủ.

**File:** `frontend/vite.config.ts`, kiến trúc tổng thể

**Giải pháp ngắn hạn (low effort, high SEO impact):**

Tạo script Python pre-render news/guides thành HTML tĩnh, push lên Cloudflare Pages cùng với SPA:

```python
# scripts/prerender_seo.py
"""Pre-render news + guides thành HTML tĩnh để Google index."""
import os
from pathlib import Path
import requests

API_BASE = os.environ.get("API_BASE", "https://api.nongnghiepso.vn")
OUTPUT = Path(__file__).parent.parent / "frontend" / "dist" / "seo"
OUTPUT.mkdir(parents=True, exist_ok=True)

def render_news():
    articles = requests.get(f"{API_BASE}/api/v1/content/news?limit=200").json()
    for article in articles:
        slug = article["source_url"].rstrip("/").split("/")[-1].replace(".html", "")
        html = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>{article["title"]} — Nông Nghiệp Số</title>
  <meta name="description" content="{article["summary"][:160]}" />
  <link rel="canonical" href="{article["source_url"]}" />
  <meta property="og:title" content="{article["title"]}" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="{article["source_url"]}" />
  <meta http-equiv="refresh" content="0; url={article["source_url"]}" />
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "headline": "{article["title"]}",
    "datePublished": "{article["published_at"] or article["scraped_at"]}",
    "publisher": {{ "@type": "Organization", "name": "{article["source_name"]}" }}
  }}
  </script>
</head>
<body>
  <h1>{article["title"]}</h1>
  <p>{article["summary"]}</p>
  <p>Nguồn: <a href="{article["source_url"]}">{article["source_name"]}</a></p>
</body>
</html>"""
        (OUTPUT / "news" / f"{slug}.html").parent.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "news" / f"{slug}.html").write_text(html, encoding="utf-8")

def render_guides():
    guides = requests.get(f"{API_BASE}/api/v1/content/guides?limit=200").json()
    for guide in guides:
        html = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>{guide["title"]} — Hướng Dẫn Kỹ Thuật Nông Nghiệp Số</title>
  <meta name="description" content="{guide["summary"][:160]}" />
  <link rel="canonical" href="https://nongnghiepso.vn/guides/{guide["slug"]}" />
</head>
<body>
  <article>
    <h1>{guide["title"]}</h1>
    <p>{guide["summary"]}</p>
    <div>{guide["content"]}</div>
    <footer>Tác giả: {guide["author"]} · Đăng: {guide["published_at"]}</footer>
  </article>
</body>
</html>"""
        (OUTPUT / "guides" / f"{guide['slug']}.html").parent.mkdir(parents=True, exist_ok=True)
        (OUTPUT / "guides" / f"{guide['slug']}.html").write_text(html, encoding="utf-8")

if __name__ == "__main__":
    render_news()
    render_guides()
    print(f"✓ SEO HTML generated in {OUTPUT}")
```

**Chạy trong CI/CD (GitHub Actions hoặc cron):**
```yaml
# .github/workflows/seo-prerender.yml
- name: Pre-render SEO HTML
  run: python scripts/prerender_seo.py
- name: Deploy to Cloudflare Pages
  run: ...
```

**Giải pháp dài hạn (HIGH effort):** Migrate sang Next.js với SSG cho news/guides + ISR (Incremental Static Regeneration) revalidate mỗi 6h. Estimated effort: 3-5 ngày.

---

### [FIX-027] 🟡 Frontend Dependencies Toàn `latest` — Không Reproducible

**Vấn đề:** `frontend/package.json` dùng `"react": "latest"` cho mọi dep. Build hôm nay khác build hôm sau, không phù hợp production.

**File:** `frontend/package.json`

**Code đề xuất:**
```json
{
  "name": "marketai-durian-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "tsc && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@phosphor-icons/react": "^2.1.10",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.13.3"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.2",
    "vite": "^6.0.3"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}
```

**Quan trọng:** Sau khi sửa, chạy `npm install` để regenerate `package-lock.json` và **commit lock file**.

---

## 🟡 SECTION 4 — DEPLOYMENT & OPERATIONAL

---

### [FIX-028] 🟡 Caddyfile Thiếu Security Headers & Rate Limit

**File:** `deploy/Caddyfile`

**Code đề xuất:**
```
{
    # Tắt admin endpoint (chỉ cần khi debug)
    admin off
    
    # Email cho Let's Encrypt
    email admin@nongnghiepso.vn
    
    # Servers options
    servers {
        max_header_size 16KB
        timeouts {
            read_body 30s
            read_header 10s
            write 30s
            idle 120s
        }
    }
}

{$API_DOMAIN} {
    encode zstd gzip
    
    # Rate limiting tại proxy level (cần plugin caddy-ratelimit)
    # Nếu không cài plugin, comment block này
    # rate_limit {
    #     zone auth_zone {
    #         key {remote_host}
    #         events 30
    #         window 1m
    #     }
    #     match {
    #         path /api/v1/auth/*
    #     }
    # }
    
    # Limit request size (chống upload bomb)
    request_body {
        max_size 5MB
    }
    
    reverse_proxy api:8010 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        
        # Health check
        health_uri /health
        health_interval 30s
        health_timeout 5s
    }
    
    header {
        # Security headers
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        Content-Security-Policy "default-src 'none'; frame-ancestors 'none'"
        
        # Xóa server fingerprint
        -Server
        -X-Powered-By
    }
    
    # Logging
    log {
        output file /var/log/caddy/api.log {
            roll_size 100MB
            roll_keep 7
        }
        format json
        level INFO
    }
}
```

---

### [FIX-029] 🟡 Docker Compose Production — Thiếu Backup & Monitoring

**File:** `deploy/docker-compose.prod.yml`

**Code đề xuất — Thêm services:**
```yaml
services:
  postgres:
    image: timescale/timescaledb:2.17.2-pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-marketai}
      POSTGRES_USER: ${POSTGRES_USER:-marketai}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in deploy/.env}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres-backup:/backups
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-marketai} -d ${POSTGRES_DB:-marketai}"]
      interval: 10s
      timeout: 5s
      retries: 8
    shm_size: 256m
    logging:
      driver: "json-file"
      options: { max-size: "10m", max-file: "5" }
  
  api:
    build: { context: ../backend }
    restart: unless-stopped
    env_file: [../backend/.env.production]
    environment:
      MARKETAI_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-marketai}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-marketai}
      MARKETAI_START_SCHEDULER_IN_API: "false"
      MARKETAI_JOB_LOCK_DIR: /app/.job_locks
      MARKETAI_ENVIRONMENT: production
    depends_on:
      postgres: { condition: service_healthy }
    expose: ["8010"]
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8010/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits: { cpus: "1.5", memory: 1G }
        reservations: { cpus: "0.25", memory: 256M }
    logging:
      driver: "json-file"
      options: { max-size: "10m", max-file: "5" }
  
  worker:
    build: { context: ../backend }
    restart: unless-stopped
    command: ["python", "-m", "app.worker"]
    env_file: [../backend/.env.production]
    environment:
      MARKETAI_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-marketai}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-marketai}
      MARKETAI_START_SCHEDULER_IN_API: "false"
      MARKETAI_JOB_LOCK_DIR: /app/.job_locks
      MARKETAI_ENVIRONMENT: production
    volumes:
      - job_locks:/app/.job_locks
    depends_on:
      postgres: { condition: service_healthy }
    deploy:
      resources:
        limits: { cpus: "1.5", memory: 1G }
  
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    environment:
      API_DOMAIN: ${API_DOMAIN:-api.nongnghiepso.vn}
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - caddy_logs:/var/log/caddy
    depends_on:
      api: { condition: service_healthy }
  
  # NEW: Daily PostgreSQL backup
  postgres-backup:
    image: postgres:16-alpine
    restart: unless-stopped
    depends_on:
      postgres: { condition: service_healthy }
    environment:
      PGPASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./postgres-backup:/backups
    entrypoint: |
      sh -c '
      while true; do
        DATE=$$(date +%Y%m%d-%H%M%S)
        pg_dump -h postgres -U ${POSTGRES_USER:-marketai} -d ${POSTGRES_DB:-marketai} -Fc -f /backups/backup-$$DATE.dump
        # Giữ 7 ngày backup
        find /backups -name "backup-*.dump" -mtime +7 -delete
        sleep 86400
      done'

volumes:
  postgres_data:
  caddy_data:
  caddy_config:
  caddy_logs:
  job_locks:
```

---

### [FIX-030] 🟡 Vite Build Không Có Code Splitting Strategy

**File:** `frontend/vite.config.ts`

**Code đề xuất:**
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8010",
      "/health": "http://127.0.0.1:8010"
    }
  },
  build: {
    target: "es2022",
    sourcemap: true,  // cho Sentry
    minify: "esbuild",
    cssMinify: "esbuild",
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "recharts": ["recharts"],
          "icons": ["@phosphor-icons/react"],
        },
      },
    },
  },
  // Khi cần phân tích bundle: npm install -D rollup-plugin-visualizer
});
```

---

## 🟢 SECTION 5 — LOW PRIORITY (CODE QUALITY & POLISH)

---

### [FIX-031] 🟢 main.py 800+ Lines — Tách Routers

**Vấn đề:** Tất cả 40+ endpoints trong 1 file. Khó maintain khi grow.

**File:** `backend/app/main.py`

**Cấu trúc đề xuất:**
```
backend/app/
├── routers/
│   ├── __init__.py
│   ├── auth.py        # /auth/*
│   ├── analytics.py   # /analytics/*
│   ├── content.py     # /content/*
│   ├── metadata.py    # /metadata/*
│   ├── platform.py    # /platform/* (admin)
│   ├── ingestion.py   # /ingestion/* (admin)
│   ├── public.py      # /public/* (api key)
│   ├── sensors.py     # /sensors/* (iot key)
│   └── watchlist.py   # /watchlist/*
├── main.py            # chỉ còn ~80 lines: app setup + lifespan + include_routers
```

**Mỗi router file pattern:**
```python
# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas import AuthCredentials, AuthTokenOut, AuthUserOut
# ...

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=AuthTokenOut)
def login(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    ...
```

**main.py mới:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.routers import auth, analytics, content, metadata, platform, ingestion, public, sensors, watchlist

settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
# ... CORS middleware
# ... rate limiter

API_PREFIX = settings.api_prefix
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(content.router, prefix=API_PREFIX)
# ...
```

---

### [FIX-032] 🟢 Pydantic Validators Duplicate Logic Trong main.py

**Vấn đề:** `main.py:115-119` validate email/password ngay trong handler, trùng với Pydantic validator trong schemas.py:80-86. Pydantic đã raise `422` rồi.

**File:** `backend/app/main.py:113-137`

**Code đề xuất:**
```python
# schemas.py — bổ sung validator password
class AuthCredentials(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)  # ← tăng từ 6 → 8
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Email không hợp lệ")
        return email
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Mật khẩu cần tối thiểu 8 ký tự")
        if not re.search(r"\d", value):
            raise ValueError("Mật khẩu cần ít nhất 1 chữ số")
        return value
```

```python
# main.py — bỏ check thủ công
@router.post("/register", response_model=AuthTokenOut)
@limiter.limit("5/minute")
def register(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    # ❌ XÓA: if not email or "@" not in email: ...
    # ❌ XÓA: if len(payload.password) < 6: ...
    # Pydantic đã validate xong
    user = AppUser(
        email=payload.email,  # đã được normalize bởi Pydantic
        display_name=payload.display_name or payload.email.split("@", 1)[0],
        password_hash=hash_password(payload.password),
        created_at=datetime.now(UTC),
    )
    ...
```

---

### [FIX-033] 🟢 Email Validation — Dùng Pydantic EmailStr Thay Vì Regex

**File:** `backend/requirements.txt`, `backend/app/schemas.py`

**Cài thư viện:**
```bash
pip install email-validator
```

**Update `requirements.txt`:**
```
email-validator==2.2.0
```

**Update `schemas.py`:**
```python
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class AuthCredentials(BaseModel):
    email: EmailStr  # ← thay str + regex
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)

class SubscriberIn(BaseModel):
    email: EmailStr
    source: str | None = Field(default="footer", max_length=120)
```

---

### [FIX-034] 🟢 BackgroundScheduler Dùng `time.sleep(60)` Trong Thread — Không Robust

**Vấn đề:** `services/platform_jobs.py:194-232` dùng simple loop + `time.sleep(60)`. Nếu một job chạy 5 phút, các job khác bị delay tương ứng. Không có way để gracefully shutdown.

**File:** `backend/app/services/platform_jobs.py:194-232`

**Code đề xuất — Dùng APScheduler:**
```bash
pip install apscheduler==3.11.0
```

```python
# requirements.txt
apscheduler==3.11.0
```

```python
# services/platform_jobs.py — thay BackgroundScheduler
from apscheduler.schedulers.background import BackgroundScheduler as APBackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

class JobScheduler:
    _scheduler: APBackgroundScheduler | None = None

    @classmethod
    def start_once(cls) -> None:
        if cls._scheduler is not None:
            return
        settings = get_settings()
        cls._scheduler = APBackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=2)},
            job_defaults={"coalesce": True, "max_instances": 1},
        )
        
        cls._scheduler.add_job(
            cls._run_with_session, "interval",
            minutes=settings.scrape_interval_minutes,
            args=["scrape"], id="scrape_prices",
            next_run_time=datetime.now(UTC) + timedelta(minutes=2),
        )
        cls._scheduler.add_job(
            cls._run_with_session, "interval",
            minutes=settings.news_scrape_interval_minutes,
            args=["news"], id="scrape_news",
            next_run_time=datetime.now(UTC) + timedelta(minutes=3),
        )
        cls._scheduler.add_job(
            cls._run_with_session, "interval",
            minutes=settings.data_quality_interval_minutes,
            args=["data_quality"], id="data_quality",
        )
        cls._scheduler.add_job(
            cls._run_with_session, "interval",
            minutes=settings.retrain_interval_minutes,
            args=["retrain"], id="retrain",
        )
        cls._scheduler.start()

    @classmethod
    def shutdown(cls) -> None:
        if cls._scheduler:
            cls._scheduler.shutdown(wait=True)

    @staticmethod
    def _run_with_session(job: str) -> None:
        with SessionLocal() as db:
            service = PlatformJobService(db)
            try:
                if job == "scrape":
                    service.run_scrape()
                elif job == "news":
                    service.run_news_scrape()
                elif job == "data_quality":
                    service.run_data_quality()
                elif job == "retrain":
                    service.run_retrain()
            except Exception:
                logger.exception("Scheduled job %s failed", job)
```

---

### [FIX-035] 🟢 Worker Process Dùng `time.sleep(3600)` — Không Graceful Shutdown

**File:** `backend/app/worker.py`

**Code đề xuất:**
```python
import logging
import signal
import sys
import threading

from app.core.config import get_settings
from app.db import SessionLocal, init_db
from app.seed import normalize_vietnamese_labels, seed_database
from app.services.content_portal import ContentPortalService
from app.services.crop_catalog import ensure_crop_catalog
from app.services.platform_jobs import JobScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("marketai.worker")

shutdown_event = threading.Event()


def bootstrap() -> None:
    settings = get_settings()
    init_db()
    if not settings.seed_on_startup:
        return
    with SessionLocal() as db:
        seed_database(db)
        normalize_vietnamese_labels(db)
        ensure_crop_catalog(db)
        content = ContentPortalService(db)
        content.seed_guides()
        content.seed_fallback_news()


def handle_shutdown(signum, frame):
    logger.info("Received shutdown signal, stopping...")
    shutdown_event.set()


def main() -> None:
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    bootstrap()
    JobScheduler.start_once()
    logger.info("MarketAI worker started.")
    
    shutdown_event.wait()
    
    logger.info("Stopping job scheduler...")
    JobScheduler.shutdown()
    logger.info("Worker stopped cleanly.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

---

### [FIX-036] 🟢 Scrapers — Không Có Retry Logic & Timeout Per-Source

**File:** `backend/app/ingestion/http.py`, `backend/app/ingestion/service.py`

**Code đề xuất — Thêm retry với backoff:**
```python
# ingestion/http.py
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MarketAI/1.0; +https://nongnghiepso.vn/bot)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=2,  # 2s, 4s, 8s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(DEFAULT_HEADERS)
    return session


_SESSION = _build_session()


def fetch_html(url: str, timeout: int = 20) -> str:
    response = _SESSION.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text
```

**Update `ingestion/service.py:30-49`:** thêm timeout per-source và logging:
```python
import logging
logger = logging.getLogger(__name__)

try:
    logger.info("Starting scrape: %s", scraper.source)
    result = scraper.scrape()
    inserted, updated = self.store(result)
    logger.info("Scrape success: %s — found=%d inserted=%d updated=%d", 
                scraper.source, len(result.observations), inserted, updated)
except requests.Timeout as exc:
    logger.warning("Scrape timeout: %s", scraper.source)
    # ... existing error handling
except Exception as exc:
    logger.exception("Scrape failed: %s", scraper.source)
    # ... existing error handling
```

---

### [FIX-037] 🟢 Missing Indexes Cho Query Patterns Phổ Biến

**File mới:** `backend/migrations/003_additional_indexes.sql`

```sql
-- Composite index cho metadata/regions query (line main.py:219-241)
CREATE INDEX IF NOT EXISTS ix_daily_market_prices_crop_region 
    ON daily_market_prices (crop_type, region_id);

-- Partial index: chỉ index "Loại A" (quality_grade phổ biến nhất)
CREATE INDEX IF NOT EXISTS ix_daily_market_prices_grade_a_recent 
    ON daily_market_prices (crop_type, variety_id, region_id, record_timestamp DESC)
    WHERE quality_grade = 'Loại A';

-- Cho cleanup_news_archive query
CREATE INDEX IF NOT EXISTS ix_news_articles_scraped 
    ON news_articles (scraped_at DESC);

-- Watchlist lookup by user
CREATE INDEX IF NOT EXISTS ix_watchlist_user_created 
    ON watchlist_items (user_id, created_at DESC);

-- Subscribers email lookup (đã unique nhưng explicit index giúp)
CREATE INDEX IF NOT EXISTS ix_subscribers_source 
    ON subscribers (source, created_at DESC);

-- TimescaleDB: enable compression cho prices > 90 days
ALTER TABLE daily_market_prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'variety_id, region_id, crop_type'
);
SELECT add_compression_policy('daily_market_prices', INTERVAL '90 days', if_not_exists => TRUE);

-- TimescaleDB: data retention sau 2 năm (optional, tùy nhu cầu)
-- SELECT add_retention_policy('daily_market_prices', INTERVAL '2 years', if_not_exists => TRUE);
```

---

### [FIX-038] 🟢 News Article URL Quá Dài — VARCHAR(800) UNIQUE Có Thể Lỗi

**Vấn đề:** PostgreSQL btree index có giới hạn ~2700 bytes per row. UNIQUE INDEX trên `VARCHAR(800)` UTF-8 (3 bytes/char) = 2400 bytes — gần ngưỡng. Nếu URL có ký tự multi-byte sẽ fail.

**File:** `backend/app/models.py:169`

**Code đề xuất:**
```python
class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        # Dùng hash unique constraint thay vì btree
        Index("uq_news_url_hash", text("md5(source_url)"), unique=True),
    )
    article_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str] = mapped_column(String(800))  # ← bỏ unique=True
    # ... rest unchanged
```

**Migration:**
```sql
-- migrations/004_fix_news_url_index.sql
DROP INDEX IF EXISTS news_articles_source_url_key;
CREATE UNIQUE INDEX uq_news_url_hash ON news_articles (md5(source_url));
```

---

### [FIX-039] 🟢 Frontend Không Có Error Boundary

**Vấn đề:** Nếu MasterChart hoặc IntelligencePanels throw exception (e.g., `recharts` runtime error), toàn bộ app crash với màn hình trắng.

**File mới:** `frontend/src/components/ErrorBoundary.tsx`
```typescript
import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode; fallback?: (err: Error) => ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
    // TODO: send to Sentry
  }

  render() {
    if (this.state.error) {
      return this.props.fallback?.(this.state.error) ?? (
        <div className="error-boundary">
          <h3>Đã có lỗi xảy ra</h3>
          <p>Vui lòng tải lại trang. Nếu vẫn lỗi, báo cho admin.</p>
          <button onClick={() => this.setState({ error: null })}>Thử lại</button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

**Wrap toàn app:**
```typescript
// App.tsx
import { ErrorBoundary } from "./components/ErrorBoundary";

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        ...
      </AuthProvider>
    </ErrorBoundary>
  );
}
```

**Wrap từng heavy section:**
```typescript
<ErrorBoundary fallback={() => <div>Biểu đồ lỗi, đang thử lại...</div>}>
  <MasterChart {...props} />
</ErrorBoundary>
```

---

### [FIX-040] 🟢 Không Có Logging Structured Cho Production

**Vấn đề:** Backend chỉ có một số chỗ dùng `logger`. Không có request ID, không có structured JSON logs (khó parse trong tools như Datadog/Loki).

**File:** `backend/app/main.py`

**Code đề xuất:**
```python
import logging
import logging.config
import time
import uuid
from fastapi import Request

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
        },
        "default": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if settings.environment == "production" else "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if settings.environment == "production" else "DEBUG",
    },
})
logger = logging.getLogger("marketai")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    
    response.headers["X-Request-ID"] = request_id
    
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
        }
    )
    return response
```

---

### [FIX-041] 🟢 Bỏ `volatile_storage` Logic Đối Xứng — Code Phức Tạp Vô Ích

**Vấn đề:** `App.tsx:409-414` lưu vào persistent rồi xóa khỏi volatile. Sau khi đã tách AuthContext (FIX-021), không cần logic này nữa.

**File:** Đã được fix gián tiếp bởi FIX-011 + FIX-021.

---

## 📋 SECTION 6 — LỘ TRÌNH THỰC HIỆN ĐỀ XUẤT

### Tuần 1 — Critical Security (BẮT BUỘC trước public)
- [ ] FIX-005 (admin role) → unblock FIX-001, 002, 003, 005
- [ ] FIX-001, 002, 003 (auth missing endpoints)
- [ ] FIX-004 (IoT API key)
- [ ] FIX-006 (SSRF)
- [ ] FIX-007 (demo credentials)
- [ ] FIX-008 (env validation)
- [ ] FIX-009 (rate limiting)
- [ ] FIX-011 (sessionStorage)

**Estimated: 2-3 ngày**

### Tuần 2 — Performance Wins
- [ ] FIX-010 (python-jose)
- [ ] FIX-012 (CORS)
- [ ] FIX-013 (model-metrics caching)
- [ ] FIX-014 (in-memory cache)
- [ ] FIX-015 (bulk data quality)
- [ ] FIX-017 (cleanup news ra khỏi read path)
- [ ] FIX-018 (default scheduler off)

**Estimated: 3-4 ngày**

### Tuần 3 — Database & Infrastructure
- [ ] FIX-019 (Alembic)
- [ ] FIX-020 (TimescaleDB image)
- [ ] FIX-029 (Docker compose backup)
- [ ] FIX-028 (Caddyfile security)
- [ ] FIX-037 (additional indexes)
- [ ] FIX-038 (news URL hash index)

**Estimated: 2-3 ngày**

### Tuần 4 — Frontend Architecture
- [ ] FIX-021 (Context providers)
- [ ] FIX-022 (memo MasterChart)
- [ ] FIX-023 (AbortController)
- [ ] FIX-024 (limit historical query)
- [ ] FIX-025 (SEO meta tags)
- [ ] FIX-027 (pin deps)
- [ ] FIX-030 (vite chunks)
- [ ] FIX-039 (ErrorBoundary)

**Estimated: 3-5 ngày**

### Tuần 5+ — Polish & Long-Term
- [ ] FIX-016 (SQL aggregation top_movers)
- [ ] FIX-026 (SEO prerender)
- [ ] FIX-031 (router split)
- [ ] FIX-032 (validators consolidation)
- [ ] FIX-033 (EmailStr)
- [ ] FIX-034 (APScheduler)
- [ ] FIX-035 (worker graceful shutdown)
- [ ] FIX-036 (scraper retry)
- [ ] FIX-040 (structured logs)

---

## 📋 SECTION 7 — CHECKLIST TRƯỚC KHI DEPLOY PRODUCTION

```bash
# Backend env vars
[ ] MARKETAI_ENVIRONMENT=production
[ ] MARKETAI_AUTH_TOKEN_SECRET (>= 48 chars random)
[ ] MARKETAI_PUBLIC_API_KEY (>= 32 chars random)
[ ] MARKETAI_IOT_API_KEY (>= 32 chars random)
[ ] MARKETAI_DATABASE_URL (postgresql+psycopg, không phải sqlite)
[ ] MARKETAI_SEED_ON_STARTUP=false
[ ] MARKETAI_CREATE_DEMO_USER=false
[ ] MARKETAI_START_SCHEDULER_IN_API=false
[ ] MARKETAI_CORS_ORIGINS (chỉ chứa production domain)

# Frontend env
[ ] VITE_API_BASE_URL=https://api.nongnghiepso.vn

# Database
[ ] PostgreSQL 16 với TimescaleDB extension đã enable
[ ] alembic upgrade head đã chạy thành công
[ ] Một admin user đã được set is_admin=true

# Infrastructure
[ ] Caddy auto-HTTPS hoạt động
[ ] Daily backup cronjob đang chạy
[ ] Health check endpoint trả 200
[ ] Logs đang được rotate
[ ] Worker process running và healthy

# Smoke tests
[ ] GET /health → 200
[ ] GET /api/v1/analytics/ticker-prices?crop=sau_rieng → 200, có data
[ ] POST /api/v1/auth/register với email mới → 200
[ ] POST /api/v1/auth/login → 200, nhận JWT
[ ] POST /api/v1/auth/login 11 lần liên tiếp → request thứ 11 nhận 429
[ ] POST /api/v1/platform/jobs/scrape không có token → 401
[ ] POST /api/v1/platform/jobs/scrape với non-admin token → 403
[ ] POST /api/v1/ingestion/scrape-prices không có token → 401
[ ] GET /api/v1/content/image-proxy?url=http://127.0.0.1:80 → 403
[ ] Frontend load < 2s trên 4G
[ ] No JS errors trong console
```

---

## 📋 SECTION 8 — METRICS ĐỂ THEO DÕI SAU DEPLOY

| Metric | Target | Cách đo |
|---|---|---|
| API p95 latency | < 500ms | Caddy logs (duration field) |
| Forecast endpoint p95 | < 200ms (cached) | Sau FIX-014 |
| 4xx error rate | < 1% | Caddy logs |
| 5xx error rate | < 0.1% | Caddy logs + Sentry |
| Failed scrape rate | < 20% | scrape_runs table query |
| Data freshness (oldest source) | < 7 ngày | source_health endpoint |
| Database size growth | < 100MB/tháng | pg_database_size |
| JWT token leak | 0 | Sentry alert nếu có pattern bất thường |

---

## ✅ TỔNG KẾT

**Tổng số issues:** 41 (12 critical, 14 high, 13 medium, 2 low — wait, đếm lại để tránh nhầm)

**Phân loại theo mức độ:**
- 🔴 CRITICAL (12 issues): FIX-001 → FIX-012
- 🟠 HIGH (8 issues): FIX-013 → FIX-020
- 🟡 MEDIUM (10 issues): FIX-021 → FIX-030
- 🟢 LOW (11 issues): FIX-031 → FIX-041

**Phân loại theo domain:**
- Backend security: 12 issues
- Backend performance: 8 issues
- Database/Schema: 6 issues
- Frontend architecture: 8 issues
- DevOps/Deployment: 5 issues
- Code quality: 2 issues

**Estimated total effort:** 3-4 tuần (1 developer full-time) cho toàn bộ Section 1-4. Section 5 có thể incremental.

**Note quan trọng:** File này được sinh để feed vào AI coding agent. Khi assign cho agent, dùng format:
```
"Implement FIX-001 through FIX-012 from AUDIT_REPORT.md. After each fix, 
run tests in backend/tests/ and report any breaking changes. 
Commit each FIX as a separate commit with message 'fix(audit): [FIX-NNN] short description'."
```

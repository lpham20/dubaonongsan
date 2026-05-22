from datetime import UTC, datetime
import html
import ipaddress
import re
import socket
import threading
from contextlib import contextmanager
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import cached, invalidate_cache
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import get_db
from app.models import AppUser, DurianVariety, GuidePost, NewsArticle, ProductionRegion, Subscriber, UserPriceReport
from app.schemas import GuidePostOut, NewsArticleOut, SubscriberIn, SubscriberOut, UserPriceReportIn, UserPriceReportOut
from app.services.auth import require_admin
from app.services.content_portal import ContentPortalService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["content"])

PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]
ALLOWED_IMAGE_HOSTS = {
    "hainong.vn",
    "panel.hainong.vn",
    "nongnghiepmoitruong.vn",
    "nongsanviet.nongnghiepmoitruong.vn",
}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
SITE_BASE = "https://dubaonongsan.com"
_DNS_PIN_LOCK = threading.Lock()


def _slug_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\-]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:120] or "bai-viet"


def _slug_from_url(url: str, fallback: str = "bai-viet") -> str:
    try:
        parsed = urlparse(url)
        tail = parsed.path.rstrip("/").split("/")[-1] or fallback
    except Exception:
        tail = fallback
    tail = re.sub(r"\.(html?|aspx?)$", "", tail.split("?", 1)[0], flags=re.IGNORECASE)
    return _slug_text(tail)


def _news_slug(article: NewsArticle) -> str:
    if article.public_slug:
        return article.public_slug
    return f"{article.article_id}-{_slug_from_url(article.source_url, article.title)}"


def _public_guide_slug(slug: str) -> str:
    return re.sub(r"^(hainong|hai-nong|hai_nong)-+", "", slug, flags=re.IGNORECASE)


def _guide_out(guide: GuidePost) -> dict:
    return {
        "post_id": guide.post_id,
        "slug": guide.public_slug or _public_guide_slug(guide.slug),
        "title": guide.title,
        "crop_type": guide.crop_type,
        "category": guide.category,
        "tags": guide.tags,
        "summary": guide.summary,
        "content": _public_guide_content(guide.content),
        "author": guide.author,
        "published_at": guide.published_at,
    }


def _public_guide_content(content: str) -> str:
    public_lines = []
    for line in content.splitlines():
        if line.strip().startswith("IMAGE::"):
            continue
        public_lines.append(line)
    return "\n".join(public_lines)


def _guide_image_urls(content: str) -> list[str]:
    urls = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("IMAGE::"):
            urls.append(line.removeprefix("IMAGE::").strip())
    return urls


@router.get("/content/news", response_model=list[NewsArticleOut])
@cached(prefix="news", ttl_seconds=300)
def news(
    category: str | None = Query(default=None),
    limit: int = Query(default=120, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list:
    return ContentPortalService(db).latest_news(limit=limit, category=category)


@router.get("/content/news/{slug}", response_model=NewsArticleOut)
@cached(prefix="news-detail", ttl_seconds=900)
def news_detail(slug: str, db: Session = Depends(get_db)) -> NewsArticle:
    article = db.scalar(select(NewsArticle).where(NewsArticle.public_slug == slug))
    if article:
        return article
    article_id_part = slug.split("-", 1)[0]
    if article_id_part.isdigit():
        article = db.scalar(select(NewsArticle).where(NewsArticle.article_id == int(article_id_part)))
        if article:
            return article

    articles = db.scalars(select(NewsArticle).order_by(NewsArticle.scraped_at.desc()).limit(2500)).all()
    for article in articles:
        if _news_slug(article) == slug or _slug_from_url(article.source_url, article.title) == slug:
            return article
    raise HTTPException(status_code=404, detail="Không tìm thấy bài tin")


@router.post("/content/news/scrape")
def scrape_news(
    _: AppUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    summary = ContentPortalService(db).scrape_news()
    invalidate_cache("news")
    invalidate_cache("news-detail")
    invalidate_cache("sitemap-xml")
    return summary


@router.get("/content/guides", response_model=list[GuidePostOut])
@cached(prefix="guides", ttl_seconds=900)
def guides(
    crop: str | None = Query(default=None),
    limit: int = Query(default=120, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list:
    return [_guide_out(guide) for guide in ContentPortalService(db).guides(crop=crop, limit=limit)]


@router.get("/content/guides/{slug}", response_model=GuidePostOut)
@cached(prefix="guide-detail", ttl_seconds=1800)
def guide_detail(slug: str, db: Session = Depends(get_db)) -> dict:
    public_slug = _public_guide_slug(slug)
    guide = db.scalar(select(GuidePost).where(GuidePost.public_slug == public_slug))
    if guide is not None:
        return _guide_out(guide)
    candidate_slugs = {slug, f"hainong-{slug}"}
    guide = db.scalar(select(GuidePost).where(GuidePost.slug.in_(candidate_slugs)))
    if guide is None:
        guide = db.scalar(select(GuidePost).where(GuidePost.slug.in_({public_slug, f"hainong-{public_slug}"})))
    if guide is None:
        id_match = re.match(r"^.*-(\d+)$", slug)
        if id_match:
            guide = db.scalar(select(GuidePost).where(GuidePost.post_id == int(id_match.group(1))))
    if guide is None:
        prefix = re.sub(r"-\d+$", "", _public_guide_slug(slug)).strip("-")
        if prefix:
            rows = db.scalars(select(GuidePost).limit(2500)).all()
            guide = next(
                (
                    row
                    for row in rows
                    if _public_guide_slug(row.slug) == slug
                    or _public_guide_slug(row.slug).startswith(f"{prefix}-")
                ),
                None,
            )
    if guide is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài hướng dẫn")
    return _guide_out(guide)


@router.get("/sitemap.xml", include_in_schema=False)
@router.head("/sitemap.xml", include_in_schema=False)
@cached(prefix="sitemap-xml", ttl_seconds=900)
def sitemap(db: Session = Depends(get_db)) -> Response:
    urls: list[tuple[str, str, str, str | None]] = [
        (f"{SITE_BASE}/", "1.0", "daily", None),
        (f"{SITE_BASE}/tin-tuc", "0.9", "hourly", None),
        (f"{SITE_BASE}/huong-dan", "0.9", "weekly", None),
        (f"{SITE_BASE}/du-bao-gia/sau_rieng", "0.9", "daily", None),
        (f"{SITE_BASE}/du-bao-gia/ca_phe", "0.9", "daily", None),
        (f"{SITE_BASE}/du-bao-gia/ho_tieu", "0.9", "daily", None),
        (f"{SITE_BASE}/du-bao-gia/lua", "0.9", "daily", None),
        (f"{SITE_BASE}/du-bao-gia/phan-bon", "0.8", "daily", None),
        (f"{SITE_BASE}/roi-uoc-tinh", "0.6", "weekly", None),
        (f"{SITE_BASE}/khuyen-nghi-bon-phan", "0.8", "weekly", None),
        (f"{SITE_BASE}/khuyen-nghi-bon-phan/logic", "0.7", "monthly", None),
        (f"{SITE_BASE}/bao-cao-nang-suat", "0.7", "monthly", None),
        (f"{SITE_BASE}/thuat-toan-du-bao", "0.7", "monthly", None),
    ]

    guides_rows = db.scalars(select(GuidePost).order_by(GuidePost.published_at.desc()).limit(1000)).all()
    for guide in guides_rows:
        lastmod = guide.published_at.date().isoformat() if guide.published_at else None
        urls.append((f"{SITE_BASE}/huong-dan/{guide.public_slug or _public_guide_slug(guide.slug)}", "0.7", "monthly", lastmod))

    articles = ContentPortalService(db).latest_news(limit=500)
    for article in articles:
        published = article.published_at or article.scraped_at
        lastmod = published.date().isoformat() if published else None
        urls.append((f"{SITE_BASE}/tin-tuc/{_news_slug(article)}", "0.6", "weekly", lastmod))

    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, priority, changefreq, lastmod in urls:
        body.append("  <url>")
        body.append(f"    <loc>{html.escape(loc)}</loc>")
        body.append(f"    <changefreq>{changefreq}</changefreq>")
        body.append(f"    <priority>{priority}</priority>")
        if lastmod:
            body.append(f"    <lastmod>{lastmod}</lastmod>")
        body.append("  </url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml; charset=utf-8")


@router.get("/rss/news.xml", include_in_schema=False)
def news_rss(db: Session = Depends(get_db)) -> Response:
    articles = ContentPortalService(db).latest_news(limit=50)
    items = []
    for article in articles:
        published = article.published_at or article.scraped_at
        pub_date = published.strftime("%a, %d %b %Y %H:%M:%S +0700") if published else ""
        link = f"{SITE_BASE}/tin-tuc/{_news_slug(article)}"
        items.append(
            f"""
    <item>
      <title><![CDATA[{article.title}]]></title>
      <link>{html.escape(link)}</link>
      <guid>{html.escape(link)}</guid>
      <description><![CDATA[{article.summary}]]></description>
      <pubDate>{pub_date}</pubDate>
      <category><![CDATA[{article.category}]]></category>
    </item>"""
        )

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Dự báo nông sản - Tin nông nghiệp</title>
    <link>{SITE_BASE}</link>
    <description>Tin tức thị trường nông sản, phân bón và chính sách nông nghiệp Việt Nam.</description>
    <language>vi</language>
    {"".join(items)}
  </channel>
</rss>"""
    return Response(rss, media_type="application/rss+xml; charset=utf-8")


@router.post("/content/subscribers", response_model=SubscriberOut, status_code=201)
@limiter.limit("3/minute")
def subscribe_to_newsletter(
    request: Request,
    payload: SubscriberIn,
    response: Response,
    db: Session = Depends(get_db),
) -> Subscriber:
    email = payload.email.strip().lower()
    now = datetime.now(UTC)
    existing = db.scalar(select(Subscriber).where(Subscriber.email == email))
    if existing:
        existing.source = payload.source or existing.source
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        response.status_code = 200
        return existing

    subscriber = Subscriber(
        email=email,
        source=payload.source or "footer",
        created_at=now,
        updated_at=now,
    )
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)
    return subscriber


@router.post("/content/price-reports", response_model=UserPriceReportOut, status_code=201)
@limiter.limit("6/minute")
def report_local_price(
    request: Request,
    payload: UserPriceReportIn,
    db: Session = Depends(get_db),
) -> dict:
    region = db.scalar(select(ProductionRegion).where(ProductionRegion.region_id == payload.region_id))
    variety = db.scalar(
        select(DurianVariety).where(
            DurianVariety.variety_id == payload.variety_id,
            DurianVariety.crop_type == payload.crop_type,
        )
    )
    if region is None or variety is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy vùng hoặc loại nông sản đã chọn.")

    now = datetime.now(UTC)
    grade = (payload.quality_grade or "Giá người dùng báo").strip()
    report = UserPriceReport(
        crop_type=payload.crop_type,
        region_id=payload.region_id,
        variety_id=payload.variety_id,
        quality_grade=grade,
        price_vnd=payload.price_vnd,
        reporter_name=(payload.reporter_name or None),
        note=(payload.note or None),
        approved_for_training=False,
        created_at=now,
    )
    db.add(report)
    db.commit()
    invalidate_cache("daily-price-board")
    db.refresh(report)
    return {
        "report_id": report.report_id,
        "crop_type": report.crop_type,
        "region_id": report.region_id,
        "variety_id": report.variety_id,
        "price_vnd": float(report.price_vnd),
        "quality_grade": report.quality_grade,
        "approved_for_training": report.approved_for_training,
        "created_at": report.created_at,
        "message": "Đã ghi nhận giá địa phương để tham khảo. Giá này chưa được đưa vào dữ liệu huấn luyện mô hình.",
    }


def _is_allowed_image_host(host: str) -> bool:
    if not host:
        return False
    clean_host = host.lower().strip().rstrip(".")
    return clean_host in ALLOWED_IMAGE_HOSTS or any(clean_host.endswith(f".{allowed}") for allowed in ALLOWED_IMAGE_HOSTS)


def _resolve_public_ip(host: str) -> str | None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return None
    if not infos:
        return None
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return None
        if any(ip in network for network in PRIVATE_NETWORKS):
            return None
    return infos[0][4][0]


@contextmanager
def _pinned_dns(host: str, public_ip: str):
    original_getaddrinfo = socket.getaddrinfo
    clean_host = host.lower().strip().rstrip(".")

    def pinned_getaddrinfo(name, port, *args, **kwargs):
        if str(name).lower().strip().rstrip(".") == clean_host:
            return original_getaddrinfo(public_ip, port, *args, **kwargs)
        return original_getaddrinfo(name, port, *args, **kwargs)

    with _DNS_PIN_LOCK:
        socket.getaddrinfo = pinned_getaddrinfo
        try:
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo


@router.get("/content/guide-images/{post_id}/{image_index}")
def guide_image_by_index(
    post_id: int,
    image_index: int,
    db: Session = Depends(get_db),
) -> Response:
    guide = db.scalar(select(GuidePost).where(GuidePost.post_id == post_id))
    if guide is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài hướng dẫn")
    image_urls = _guide_image_urls(guide.content)
    if image_index < 0 or image_index >= len(image_urls):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh hướng dẫn")
    return guide_image_proxy(url=image_urls[image_index], db=db)


@router.get("/content/image-proxy")
def guide_image_proxy(
    url: str = Query(..., min_length=10, max_length=800),
    db: Session = Depends(get_db),
) -> Response:
    image_url = url.strip()
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL ảnh không hợp lệ")

    host = parsed.hostname or ""
    if not _is_allowed_image_host(host):
        raise HTTPException(status_code=403, detail="Host ảnh không được phép")
    public_ip = _resolve_public_ip(host)
    if public_ip is None:
        raise HTTPException(status_code=403, detail="URL trỏ tới network nội bộ")

    known_image = db.scalar(
        select(GuidePost.post_id)
        .where(GuidePost.content.contains(f"IMAGE::{image_url}"))
        .limit(1)
    )
    if known_image is None:
        raise HTTPException(status_code=404, detail="Ảnh không nằm trong thư viện hướng dẫn")

    try:
        with _pinned_dns(host, public_ip):
            upstream = requests.get(
                image_url,
                timeout=12,
                stream=True,
                allow_redirects=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MarketAI/1.0)",
                    "Accept": "image/avif,image/webp,image/apng,image/*",
                },
            )
        upstream.raise_for_status()
        content_length = int(upstream.headers.get("content-length", 0))
        if content_length > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Ảnh quá lớn")
        content = b""
        for chunk in upstream.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > MAX_IMAGE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh quá lớn")
    except requests.RequestException as exc:
        raise HTTPException(status_code=404, detail="Không tải được ảnh hướng dẫn") from exc

    content_type = upstream.headers.get("content-type", "image/jpeg").split(";", 1)[0].strip()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=404, detail="Tệp không phải ảnh")
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )

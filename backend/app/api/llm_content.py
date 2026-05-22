"""LLM-friendly markdown endpoints.

Trả về plain text / markdown cho AI agents (ChatGPT, Claude, Perplexity, Gemini, Bingbot)
fetch trực tiếp thay vì phải parse HTML SPA. Content tối ưu cho ingestion bởi LLM:
- Plain markdown, no HTML.
- Heading rõ ràng (## level), bullet list cho data.
- Inline citation (link source) cho news.
- Cache TTL trung bình (5-10 phút) để giảm tải DB.

Endpoints:
- GET /api/v1/llm-content/forecast/{crop}    — markdown bảng giá + forecast 30 ngày
- GET /api/v1/llm-content/guides             — markdown index của 30 guides
- GET /api/v1/llm-content/guide/{slug}       — markdown content của 1 guide
- GET /api/v1/llm-content/news               — markdown index của 30 news
- GET /api/v1/llm-content/news/{slug}        — markdown content của 1 news article
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.cache import cached
from app.core.config import get_settings
from app.db import get_db
from app.models import GuidePost, NewsArticle
from app.services.data_loader import DataLoader
from app.services.input_prices import InputPriceService

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["llm-content"])


CROP_LABEL = {
    "sau_rieng": "sầu riêng",
    "ca_phe": "cà phê",
    "ho_tieu": "hồ tiêu",
    "lua": "lúa",
}

MD_HEADERS = {
    "Content-Type": "text/markdown; charset=utf-8",
    "Cache-Control": "public, max-age=300",
    "X-Robots-Tag": "index, follow",
}


def _md_response(body: str) -> Response:
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300", "X-Robots-Tag": "index, follow"},
    )


def _clean_md(value: str | None) -> str:
    """Loại bỏ ký tự kiểm soát + collapse whitespace."""
    if not value:
        return ""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()


def _format_int(value) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "—"


@router.get("/llm-content/forecast/{crop}")
@cached(prefix="llm-forecast", ttl_seconds=300)
def llm_forecast(crop: str, db: Session = Depends(get_db)) -> Response:
    """Markdown summary: bảng giá hiện tại + forecast 30 ngày."""
    if crop == "phan-bon":
        return _llm_input_prices_fertilizer(db)
    if crop not in CROP_LABEL:
        raise HTTPException(status_code=404, detail="Crop không hỗ trợ")
    label = CROP_LABEL[crop]

    loader = DataLoader(db)
    rows = loader.historical_prices(crop_type=crop, quality_grade=None, limit=200)
    latest_by_key: dict = {}
    for row in rows:
        key = (row.get("variety"), row.get("region"), row.get("province"), row.get("quality_grade"))
        if key not in latest_by_key:
            latest_by_key[key] = row
    latest_prices = list(latest_by_key.values())[:20]

    lines = [
        f"# Giá {label} Việt Nam — cập nhật {datetime.now(timezone.utc).date().isoformat()}",
        "",
        "Nguồn: dubaonongsan.com — dự báo giá nông sản Việt Nam.",
        f"URL gốc: https://dubaonongsan.com/du-bao-gia/{crop}",
        "",
        "## Bảng giá hiện tại theo vùng và giống",
        "",
        "| Tỉnh | Vùng | Giống | Loại | Giá min (VND/kg) | Giá max (VND/kg) | Ngày |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in latest_prices:
        timestamp = p.get("timestamp") or ""
        if hasattr(timestamp, "date"):
            timestamp = timestamp.date().isoformat()
        elif isinstance(timestamp, str):
            timestamp = timestamp[:10]
        lines.append(
            f"| {_clean_md(p.get('province') or '')} "
            f"| {_clean_md(p.get('region') or '')} "
            f"| {_clean_md(p.get('variety') or '')} "
            f"| {_clean_md(p.get('quality_grade') or '')} "
            f"| {_format_int(p.get('min_price_vnd'))} "
            f"| {_format_int(p.get('max_price_vnd'))} "
            f"| {timestamp} |"
        )

    try:
        from app.api.analytics import forecast_30_days

        forecast = forecast_30_days(crop=crop, region_id=1, variety_id=None, variety=1, db=db)
    except Exception:
        forecast = []

    if forecast:
        lines.extend(
            [
                "",
                f"## Dự báo giá {label} 30 ngày tới (vùng trọng điểm)",
                "",
                "| Ngày | Dự báo (VND/kg) | Khoảng tin cậy thấp | Khoảng tin cậy cao |",
                "|---|---|---|---|",
            ]
        )
        for i, p in enumerate(forecast):
            if i not in (0, 1, 2, 3, 4, 5, 6, 13, 20, 29):
                continue
            ts = p.get("timestamp") or ""
            if hasattr(ts, "date"):
                ts = ts.date().isoformat()
            elif isinstance(ts, str):
                ts = ts[:10]
            lines.append(
                f"| {ts} "
                f"| {_format_int(p.get('forecast_price_vnd'))} "
                f"| {_format_int(p.get('confidence_low_vnd'))} "
                f"| {_format_int(p.get('confidence_high_vnd'))} |"
            )

    lines.extend(
        [
            "",
            "## Phương pháp dự báo",
            "",
            f"Dự báo giá {label} sử dụng mô hình machine learning kết hợp moving average, "
            "rolling statistics, lag features và tín hiệu thời tiết (nhiệt độ, lượng mưa). "
            "Khi đủ dữ liệu sẽ chuyển sang LSTM deep learning. Hiện tại model_kind có thể "
            "là 'baseline-statistical' hoặc 'lightgbm-v1' tuỳ artifact có sẵn.",
            "",
            "Chi tiết tại https://dubaonongsan.com/thuat-toan-du-bao",
            "",
            "## License",
            "",
            'Dữ liệu cấp phép CC BY 4.0. Khi cite vui lòng ghi nguồn "dubaonongsan.com".',
        ]
    )
    return _md_response("\n".join(lines))


@router.get("/llm-content/input-prices/phan-bon")
@cached(prefix="llm-input-prices-fertilizer", ttl_seconds=300)
def llm_input_prices_fertilizer(db: Session = Depends(get_db)) -> Response:
    return _llm_input_prices_fertilizer(db)


def _llm_input_prices_fertilizer(db: Session) -> Response:
    service = InputPriceService(db)
    products = service.products(category="fertilizer")
    latest_prices = service.latest_prices(category="fertilizer", limit=80)
    primary_slug = products[0].slug if products else "ure"
    forecast_scenario = service.forecast(product_slug=primary_slug, province=None, days=30)
    forecast = forecast_scenario.get("base", []) if isinstance(forecast_scenario, dict) else []

    lines = [
        f"# Giá phân bón đầu vào Việt Nam — cập nhật {datetime.now(timezone.utc).date().isoformat()}",
        "",
        "Nguồn: dubaonongsan.com — module giá vật tư đầu vào nông nghiệp.",
        "URL gốc: https://dubaonongsan.com/du-bao-gia/phan-bon",
        "",
        "## Sản phẩm đang theo dõi",
        "",
    ]
    for product in products:
        nutrient = f" ({_clean_md(product.nutrient_profile)})" if product.nutrient_profile else ""
        lines.append(f"- {_clean_md(product.name)}{nutrient}: {_clean_md(product.package_label or product.standard_unit)}")

    lines.extend(
        [
            "",
            "## Bảng giá mới nhất",
            "",
            "| Tỉnh | Sản phẩm | Thương hiệu | Giá bao | Giá quy đổi (VND/kg) | Nguồn | Ngày |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in latest_prices[:40]:
        observed_at = row["observed_at"]
        timestamp = observed_at.date().isoformat() if hasattr(observed_at, "date") else str(observed_at)[:10]
        lines.append(
            f"| {_clean_md(row.get('province'))} "
            f"| {_clean_md(row.get('product_name'))} "
            f"| {_clean_md(row.get('brand'))} "
            f"| {_format_int(row.get('package_price_vnd'))} "
            f"| {_format_int(row.get('normalized_price_vnd'))} "
            f"| {_clean_md(row.get('source_name'))} "
            f"| {timestamp} |"
        )

    if forecast:
        forecast_product = products[0].name if products else "phân bón"
        lines.extend(
            [
                "",
                f"## Dự báo ngắn hạn cho {forecast_product}",
                "",
                "| Ngày | Giá dự báo/bao | Khoảng thấp | Khoảng cao | Giá quy đổi (VND/kg) |",
                "|---|---|---|---|---|",
            ]
        )
        for i, row in enumerate(forecast):
            if i not in (0, 1, 2, 6, 13, 20, 29):
                continue
            ts = row["timestamp"]
            timestamp = ts.date().isoformat() if hasattr(ts, "date") else str(ts)[:10]
            lines.append(
                f"| {timestamp} "
                f"| {_format_int(row.get('forecast_price_vnd'))} "
                f"| {_format_int(row.get('confidence_low_vnd'))} "
                f"| {_format_int(row.get('confidence_high_vnd'))} "
                f"| {_format_int(row.get('normalized_price_vnd'))} |"
            )

    lines.extend(
        [
            "",
            "## Ghi chú dữ liệu",
            "",
            "Dữ liệu phân bón được tách khỏi dữ liệu giá nông sản đầu ra. Các dòng có nguồn công khai như vietnga.vn là dữ liệu crawler thu được; dữ liệu tham chiếu nền chỉ dùng khi nguồn thật chưa đủ lịch sử cho sản phẩm hoặc vùng giá.",
            "",
            "Dự báo dùng engine 3 kịch bản theo trend, mùa vụ tháng 5/tháng 11 và biến động xác định; không dùng model LSTM giá nông sản.",
            "",
            "License: CC BY 4.0. Khi cite vui lòng ghi nguồn dubaonongsan.com.",
        ]
    )
    return _md_response("\n".join(lines))


@router.get("/llm-content/guides")
@cached(prefix="llm-guides-index", ttl_seconds=600)
def llm_guides_index(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Response:
    """Markdown index of recent guides."""
    rows = db.scalars(select(GuidePost).order_by(desc(GuidePost.published_at)).limit(limit)).all()
    lines = [
        "# Thư viện hướng dẫn kỹ thuật canh tác — dubaonongsan.com",
        "",
        f"Tổng cộng {len(rows)} hướng dẫn gần nhất. URL gốc: https://dubaonongsan.com/huong-dan",
        "",
    ]
    by_cat: dict[str, list] = {}
    for r in rows:
        by_cat.setdefault(r.category or "Hướng dẫn khác", []).append(r)
    for cat, items in by_cat.items():
        lines.append(f"## {_clean_md(cat)}")
        lines.append("")
        for r in items:
            slug = re.sub(r"^(hainong|hai-nong|hai_nong)-+", "", r.slug or "", flags=re.IGNORECASE)
            lines.append(
                f"- [{_clean_md(r.title)}](https://dubaonongsan.com/huong-dan/{slug}): "
                f"{_clean_md(r.summary or '')[:250]}"
            )
        lines.append("")
    return _md_response("\n".join(lines))


@router.get("/llm-content/guide/{slug}")
@cached(prefix="llm-guide-detail", ttl_seconds=1800)
def llm_guide_detail(slug: str, db: Session = Depends(get_db)) -> Response:
    """Markdown content of 1 guide."""
    public_slug = re.sub(r"^(hainong|hai-nong|hai_nong)-+", "", slug, flags=re.IGNORECASE)
    candidates = [slug, f"hainong-{slug}", public_slug, f"hainong-{public_slug}"]
    guide = db.scalar(select(GuidePost).where(GuidePost.slug.in_(candidates)))
    if guide is None:
        raise HTTPException(status_code=404, detail="Guide not found")

    content_lines = [
        line for line in (guide.content or "").splitlines() if not line.strip().startswith("IMAGE::")
    ]
    content = "\n".join(content_lines).strip()

    lines = [
        f"# {_clean_md(guide.title)}",
        "",
        f"**Danh mục**: {_clean_md(guide.category)}  ",
        f"**Tác giả**: {_clean_md(guide.author)}  ",
        f"**Xuất bản**: {guide.published_at.date().isoformat() if guide.published_at else 'N/A'}  ",
        f"**URL gốc**: https://dubaonongsan.com/huong-dan/{public_slug}",
        "",
        f"> {_clean_md(guide.summary)}",
        "",
        "## Nội dung chi tiết",
        "",
        content,
        "",
        "---",
        "",
        "Nguồn: dubaonongsan.com. License CC BY 4.0.",
    ]
    return _md_response("\n".join(lines))


@router.get("/llm-content/news")
@cached(prefix="llm-news-index", ttl_seconds=600)
def llm_news_index(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Response:
    """Markdown index of recent news."""
    rows = db.scalars(
        select(NewsArticle).order_by(desc(NewsArticle.published_at), desc(NewsArticle.scraped_at)).limit(limit)
    ).all()
    lines = [
        "# Tin tức nông sản — dubaonongsan.com",
        "",
        f"Tổng cộng {len(rows)} bản tin gần nhất. URL gốc: https://dubaonongsan.com/tin-tuc",
        "",
    ]
    by_cat: dict[str, list] = {}
    for r in rows:
        by_cat.setdefault(r.category or "Tin nông nghiệp", []).append(r)
    for cat, items in by_cat.items():
        lines.append(f"## {_clean_md(cat)}")
        lines.append("")
        for r in items:
            slug = f"{r.article_id}"
            lines.append(
                f"- [{_clean_md(r.title)}](https://dubaonongsan.com/tin-tuc/{slug}) "
                f"({_clean_md(r.source_name)}): "
                f"{_clean_md(r.summary or r.excerpt or '')[:300]}"
            )
        lines.append("")
    return _md_response("\n".join(lines))


@router.get("/llm-content/news/{slug}")
@cached(prefix="llm-news-detail", ttl_seconds=1800)
def llm_news_detail(slug: str, db: Session = Depends(get_db)) -> Response:
    """Markdown content of 1 news article."""
    article_id_part = slug.split("-", 1)[0]
    article = None
    if article_id_part.isdigit():
        article = db.scalar(select(NewsArticle).where(NewsArticle.article_id == int(article_id_part)))
    if article is None:
        raise HTTPException(status_code=404, detail="News not found")

    lines = [
        f"# {_clean_md(article.title)}",
        "",
        f"**Nguồn**: [{_clean_md(article.source_name)}]({article.source_url})  ",
        f"**Danh mục**: {_clean_md(article.category)}  ",
        f"**Xuất bản**: {article.published_at.date().isoformat() if article.published_at else article.scraped_at.date().isoformat()}  ",
        f"**URL trên dubaonongsan.com**: https://dubaonongsan.com/tin-tuc/{article.article_id}",
        "",
        "## Tóm tắt",
        "",
        _clean_md(article.summary or ""),
        "",
        "## Trích đoạn",
        "",
        _clean_md(article.excerpt or article.summary or ""),
        "",
        "---",
        "",
        f"Đọc bài gốc: [{_clean_md(article.source_name)}]({article.source_url})",
        "",
        "Nguồn aggregation: dubaonongsan.com. Tin được scrape từ nguồn công khai, link về bài gốc bắt buộc.",
    ]
    return _md_response("\n".join(lines))

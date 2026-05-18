from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


API_BASE = (
    os.environ.get("SEO_API_BASE_URL")
    or os.environ.get("API_BASE")
    or os.environ.get("VITE_API_BASE_URL")
    or "https://api.dubaonongsan.com"
).rstrip("/")
SITE_BASE = os.environ.get("SITE_BASE", "https://dubaonongsan.com").rstrip("/")
SITE_NAME = "Dự báo nông sản"
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "")
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"
OUTPUT = DIST / "seo"


def _slug_text(value: str) -> str:
    value = value.strip().lower()
    value = (
        value.replace("đ", "d")
        .replace("Đ", "D")
        .replace("ă", "a")
        .replace("â", "a")
        .replace("ê", "e")
        .replace("ô", "o")
        .replace("ơ", "o")
        .replace("ư", "u")
    )
    value = re.sub(r"[^a-zA-Z0-9\-_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:120] or "bai-viet"


def _slug_from_url(url: str, fallback: str = "article") -> str:
    try:
        parsed = urlparse(url)
        tail = parsed.path.rstrip("/").split("/")[-1] or fallback
    except Exception:
        tail = fallback
    tail = tail.split("?", 1)[0].replace(".html", "").replace(".htm", "")
    return _slug_text(tail)


def _news_slug(article: dict) -> str:
    return f"{article.get('article_id', 'tin')}-{_slug_from_url(article.get('source_url', ''), article.get('title', 'article'))}"


def _public_guide_slug(slug: str) -> str:
    return re.sub(r"^(hainong|hai-nong|hai_nong)-+", "", slug, flags=re.IGNORECASE)


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _json(path: str, limit: int) -> list[dict]:
    try:
        url = f"{API_BASE}{path}?{urlencode({'limit': limit})}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "DubaonongsanSEOPrerender/1.0 (+https://dubaonongsan.com)",
            },
        )
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception as exc:
        print(f"SEO prerender warning: cannot fetch {path} from {API_BASE}: {exc}")
        return []


def _fetch_guides_for_index(limit: int = 30) -> list[dict]:
    """Fetch top guides for index page. Returns compact dict list."""
    try:
        data = _json("/api/v1/content/guides", limit)
        return data[:limit]
    except Exception as exc:
        print(f"SEO warning: fetch guides failed: {exc}")
        return []


def _fetch_news_for_index(limit: int = 30) -> list[dict]:
    """Fetch top news for index page."""
    try:
        data = _json("/api/v1/content/news", limit)
        return data[:limit]
    except Exception as exc:
        print(f"SEO warning: fetch news failed: {exc}")
        return []


def _fetch_prices_for_crop(crop: str, limit: int = 20) -> list[dict]:
    """Fetch current price board for crop. Endpoint /analytics/daily-price-board is public."""
    try:
        url = f"{API_BASE}/api/v1/analytics/daily-price-board?crop={crop}&limit={limit}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "DubaonongsanSEOPrerender/1.0",
            },
        )
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception as exc:
        print(f"SEO warning: fetch prices for {crop} failed: {exc}")
        return []


def _fetch_top_movers(crop: str) -> dict:
    """Fetch top gainers/losers for homepage."""
    try:
        url = f"{API_BASE}/api/v1/analytics/top-movers?crop={crop}&limit=5"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "DubaonongsanSEOPrerender/1.0",
            },
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"SEO warning: fetch top-movers for {crop} failed: {exc}")
        return {"gainers": [], "losers": []}


def _asset_tags() -> str:
    index_html_path = DIST / "index.html"
    if not index_html_path.exists():
        return ""
    index_html = index_html_path.read_text(encoding="utf-8")
    tags = [
        line.strip()
        for line in index_html.splitlines()
        if (
            ("<script" in line or "<link" in line)
            and ("/assets/" in line or 'rel="modulepreload"' in line)
        )
    ]
    return "\n  ".join(dict.fromkeys(tags))


def _breadcrumb(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index + 1, "name": name, "item": url}
            for index, (name, url) in enumerate(items)
        ],
    }


def _schema_block(schema: dict | list[dict] | None) -> str:
    if not schema:
        return ""
    schemas = schema if isinstance(schema, list) else [schema]
    return "\n  ".join(
        f'<script type="application/ld+json">{_json_ld(item)}</script>'
        for item in schemas
    )


def _json_ld(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _page(
    title: str,
    description: str,
    canonical: str,
    body: str,
    schema: dict | list[dict] | None = None,
    published_at: str | None = None,
    news_keywords: str | None = None,
    og_type: str = "article",
) -> str:
    escaped_title = html.escape(title)
    escaped_description = html.escape(description[:180])
    schema_markup = _schema_block(schema)
    article_meta = ""
    if published_at:
        article_meta = f'<meta property="article:published_time" content="{html.escape(published_at)}" />'
    keyword_meta = ""
    if news_keywords:
        keyword_meta = f'<meta name="news_keywords" content="{html.escape(news_keywords[:240])}" />'
    asset_tags = _asset_tags()
    fallback_script = (
        "<script>(function(){"
        "function ready(){var r=document.getElementById('root');return !!(r&&r.children.length);}"
        "function removeSeo(){var s=document.getElementById('seo-prerender');if(s){s.remove();}}"
        "var guard=setInterval(function(){if(ready()){clearInterval(guard);removeSeo();}},250);"
        "setTimeout(function(){if(ready()){clearInterval(guard);removeSeo();return;}"
        "var s=document.getElementById('seo-prerender');"
        "if(s){s.removeAttribute('hidden');"
        "s.style.cssText='max-width:760px;margin:24px auto;padding:0 16px;"
        "font-family:system-ui,sans-serif;line-height:1.6;color:#1a1a1a';}"
        "},5000);})();</script>"
    )

    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="theme-color" content="#0d4b38" />
  <title>{escaped_title} | {SITE_NAME}</title>
  <meta name="description" content="{escaped_description}" />
  <meta name="robots" content="index, follow, max-image-preview:large" />
  {keyword_meta}
  <link rel="canonical" href="{canonical}" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <link rel="manifest" href="/manifest.webmanifest" />
  <meta property="og:type" content="{html.escape(og_type)}" />
  <meta property="og:locale" content="vi_VN" />
  <meta property="og:site_name" content="{SITE_NAME}" />
  <meta property="og:title" content="{escaped_title}" />
  <meta property="og:description" content="{escaped_description}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="{SITE_BASE}/og-cover.jpg" />
  <meta property="og:image:type" content="image/jpeg" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image" content="{SITE_BASE}/og-cover.webp" />
  <meta property="og:image:type" content="image/webp" />
  <meta name="twitter:card" content="summary_large_image" />
  {article_meta}
  {schema_markup}
  {fallback_script}
  {asset_tags}
</head>
<body>
  <div id="seo-prerender" hidden>{body}</div>
  <div id="root"></div>
</body>
</html>"""


def _lastmod(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[:10]


def render_news() -> list[tuple[str, str | None]]:
    articles = _json("/api/v1/content/news", 500)
    urls: list[tuple[str, str | None]] = []
    for article in articles:
        slug = _news_slug(article)
        canonical = f"{SITE_BASE}/tin-tuc/{slug}"
        title = article.get("title") or "Tin nông nghiệp"
        summary = article.get("summary") or article.get("excerpt") or title
        source_name = article.get("source_name") or "Nguồn tin"
        source_url = article.get("source_url") or "#"
        published_at = article.get("published_at") or article.get("scraped_at")
        body = f"""
<article>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(summary)}</p>
  <p>{html.escape(article.get("excerpt") or summary)}</p>
  <p>Đọc thêm tại nguồn: <a href="{html.escape(source_url)}">{html.escape(source_name)}</a></p>
</article>"""
        article_schema = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": title[:110],
            "description": summary[:180],
            "url": canonical,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
            "datePublished": published_at,
            "dateModified": published_at,
            "author": {"@type": "Organization", "name": SITE_NAME},
            "publisher": {
                "@type": "Organization",
                "name": SITE_NAME,
                "url": SITE_BASE,
                "logo": {"@type": "ImageObject", "url": f"{SITE_BASE}/og-cover.jpg", "width": 1200, "height": 630},
            },
            "image": {"@type": "ImageObject", "url": f"{SITE_BASE}/og-cover.jpg", "width": 1200, "height": 630},
            "articleSection": article.get("category", "Nông sản"),
            "inLanguage": "vi",
        }
        breadcrumb_schema = _breadcrumb(
            [
                ("Trang chủ", f"{SITE_BASE}/"),
                ("Tin tức", f"{SITE_BASE}/tin-tuc"),
                (title[:60], canonical),
            ]
        )
        raw_keywords = article.get("keywords") or []
        if isinstance(raw_keywords, str):
            keyword_items = [item.strip() for item in raw_keywords.split(",") if item.strip()]
        elif isinstance(raw_keywords, list):
            keyword_items = [str(item).strip() for item in raw_keywords if str(item).strip()]
        else:
            keyword_items = []
        keyword_items = keyword_items[:10] or [
            "nông sản",
            "giá nông sản",
            str(article.get("category") or "").strip(),
        ]
        news_keywords = ", ".join(item for item in keyword_items if item)
        _write(
            OUTPUT / "news" / f"{slug}.html",
            _page(title, summary, canonical, body, [article_schema, breadcrumb_schema], published_at, news_keywords),
        )
        urls.append((canonical, _lastmod(published_at)))
    return urls


def render_guides() -> list[tuple[str, str | None]]:
    guides = _json("/api/v1/content/guides", 500)
    urls: list[tuple[str, str | None]] = []
    for guide in guides:
        slug = _public_guide_slug(guide.get("slug") or _slug_text(guide.get("title", "huong-dan")))
        canonical = f"{SITE_BASE}/huong-dan/{slug}"
        title = guide.get("title") or "Hướng dẫn kỹ thuật"
        summary = guide.get("summary") or title
        clean_lines = [
            line
            for line in (guide.get("content") or "").splitlines()
            if not line.strip().startswith("IMAGE::")
        ]
        content = html.escape("\n".join(clean_lines)).replace("\n", "<br />")
        published_at = guide.get("published_at") or guide.get("updated_at")
        body = f"<article><h1>{html.escape(title)}</h1><p>{html.escape(summary)}</p><div>{content}</div></article>"
        guide_schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": summary,
            "url": canonical,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
            "datePublished": published_at,
            "dateModified": published_at,
            "image": {"@type": "ImageObject", "url": f"{SITE_BASE}/og-cover.jpg", "width": 1200, "height": 630},
            "publisher": {
                "@type": "Organization",
                "name": SITE_NAME,
                "url": SITE_BASE,
                "logo": {"@type": "ImageObject", "url": f"{SITE_BASE}/og-cover.jpg", "width": 1200, "height": 630},
            },
            "inLanguage": "vi",
        }
        breadcrumb_schema = _breadcrumb(
            [
                ("Trang chủ", f"{SITE_BASE}/"),
                ("Hướng dẫn", f"{SITE_BASE}/huong-dan"),
                (title[:60], canonical),
            ]
        )
        _write(
            OUTPUT / "guides" / f"{slug}.html",
            _page(title, summary, canonical, body, [guide_schema, breadcrumb_schema], published_at),
        )
        urls.append((canonical, _lastmod(published_at)))
    return urls


def _build_home_body(heading: str, desc: str) -> str:
    """Build body for homepage with top movers and latest news."""
    crops = [
        ("sau_rieng", "sầu riêng"),
        ("ca_phe", "cà phê"),
        ("ho_tieu", "hồ tiêu"),
        ("lua", "lúa"),
    ]

    sections = [
        f"<main><h1>{html.escape(heading)}</h1>",
        f"<p>{html.escape(desc)}</p>",
        "<h2>Dự báo giá theo nông sản</h2>",
        "<ul>",
    ]
    for crop_key, crop_name in crops:
        sections.append(
            f'<li><a href="{SITE_BASE}/du-bao-gia/{crop_key}">'
            f"Giá {html.escape(crop_name)} hôm nay và dự báo 30 ngày</a></li>"
        )
    sections.append("</ul>")

    movers = _fetch_top_movers("sau_rieng")
    gainers = movers.get("gainers", [])[:5]
    losers = movers.get("losers", [])[:5]
    if gainers:
        sections.append("<h2>Vùng tăng giá mạnh nhất (sầu riêng)</h2><ul>")
        for mover in gainers:
            price = int(mover.get("latest_price_vnd") or mover.get("price_vnd") or 0)
            change = float(mover.get("change_pct") or 0)
            sections.append(
                f"<li>{html.escape(str(mover.get('variety') or mover.get('crop_name') or ''))} tại "
                f"{html.escape(str(mover.get('province') or mover.get('region') or ''))}: "
                f"{price:,} VND/kg (+{change:.1f}%)</li>"
            )
        sections.append("</ul>")
    if losers:
        sections.append("<h2>Vùng giảm giá mạnh nhất (sầu riêng)</h2><ul>")
        for mover in losers:
            price = int(mover.get("latest_price_vnd") or mover.get("price_vnd") or 0)
            change = float(mover.get("change_pct") or 0)
            sections.append(
                f"<li>{html.escape(str(mover.get('variety') or mover.get('crop_name') or ''))} tại "
                f"{html.escape(str(mover.get('province') or mover.get('region') or ''))}: "
                f"{price:,} VND/kg ({change:.1f}%)</li>"
            )
        sections.append("</ul>")

    news = _fetch_news_for_index(limit=10)
    if news:
        sections.append("<h2>Tin nông nghiệp mới nhất</h2><ul>")
        for item in news:
            slug = _news_slug(item)
            title = item.get("title") or "Tin"
            summary = (item.get("summary") or item.get("excerpt") or "")[:200]
            sections.append(
                f'<li><a href="{SITE_BASE}/tin-tuc/{slug}">'
                f"{html.escape(title)}</a>: {html.escape(summary)}</li>"
            )
        sections.append("</ul>")

    sections.append(
        "<h2>Về dubaonongsan.com</h2>"
        "<p>dubaonongsan.com là nền tảng dự báo giá nông sản Việt Nam, "
        "cập nhật giá theo vùng trồng và giống, kèm dự báo 30 ngày dùng mô hình "
        "machine learning. Dữ liệu được scrape hằng ngày từ các nguồn công khai "
        "như banggianongsan.com, baonghean.vn, congthuong.vn, và cập nhật trong "
        "khung 6h-22h GMT+7.</p>"
    )
    sections.append("</main>")
    return "\n".join(sections)


def _build_guides_index_body(heading: str, desc: str) -> str:
    """Build body for /huong-dan index with the latest 30 guides."""
    sections = [
        f"<main><h1>{html.escape(heading)}</h1>",
        f"<p>{html.escape(desc)}</p>",
    ]

    guides = _fetch_guides_for_index(limit=30)
    if guides:
        by_category: dict[str, list[dict]] = {}
        for guide in guides:
            category = guide.get("category") or "Hướng dẫn khác"
            by_category.setdefault(category, []).append(guide)

        for category, items in by_category.items():
            sections.append(f"<h2>{html.escape(category)}</h2><ul>")
            for guide in items:
                slug = _public_guide_slug(guide.get("slug") or "")
                if not slug:
                    continue
                title = guide.get("title") or "Hướng dẫn"
                summary = (guide.get("summary") or "")[:250]
                sections.append(
                    f'<li><a href="{SITE_BASE}/huong-dan/{slug}">'
                    f"<strong>{html.escape(title)}</strong></a>: "
                    f"{html.escape(summary)}</li>"
                )
            sections.append("</ul>")
    else:
        sections.append("<p>Thư viện hướng dẫn đang được xây dựng.</p>")

    sections.append(
        "<h2>Mô tả thư viện</h2>"
        "<p>Thư viện hướng dẫn dubaonongsan.com bao gồm các bài viết kỹ thuật "
        "canh tác, quản lý vườn, xử lý sâu bệnh, kế hoạch bón phân, thu hoạch "
        "và bảo quản nông sản tại Việt Nam. Mỗi bài cung cấp mục tiêu, thời điểm "
        "áp dụng, cách làm tại vườn, theo dõi sau khi làm và các lỗi cần tránh.</p>"
        "<p>Nội dung được tổ chức theo nhóm cây trồng và nhóm thao tác để người đọc "
        "có thể nhanh chóng tìm quy trình phù hợp với vườn, ruộng hoặc lô sản xuất "
        "đang quản lý. Các bài hướng dẫn ưu tiên ngôn ngữ thực hành, có checklist "
        "kiểm tra, dấu hiệu cần quan sát và khuyến nghị ghi chép sau khi áp dụng.</p>"
    )
    sections.append("</main>")
    return "\n".join(sections)


def render_static_pages() -> list[tuple[str, str | None]]:
    crops = {
        "sau_rieng": "sầu riêng",
        "ca_phe": "cà phê",
        "ho_tieu": "hồ tiêu",
        "lua": "lúa",
    }
    urls: list[tuple[str, str | None]] = []
    today = datetime.utcnow().date().isoformat()
    landing_pages = [
        (
            "home.html",
            f"{SITE_BASE}/",
            "Dự báo nông sản - Dự báo giá nông sản Việt Nam",
            "Theo dõi giá sầu riêng, cà phê, hồ tiêu, lúa và dự báo 30 ngày theo vùng trồng tại Việt Nam.",
            "Dự báo giá nông sản Việt Nam",
        ),
        (
            "news.html",
            f"{SITE_BASE}/tin-tuc",
            "Tin tức thị trường nông sản, phân bón và chính sách mới nhất",
            "Bản tin nông nghiệp mới nhất về giá nông sản, phân bón, vật tư, xuất khẩu và chính sách thị trường.",
            "Tin tức thị trường nông sản",
        ),
        (
            "guides.html",
            f"{SITE_BASE}/huong-dan",
            "Cẩm nang kỹ thuật canh tác nông sản",
            "Thư viện hướng dẫn kỹ thuật trồng, chăm sóc, xử lý sâu bệnh và quản lý vườn cho nông dân Việt Nam.",
            "Cẩm nang kỹ thuật canh tác",
        ),
        (
            "fertilizer.html",
            f"{SITE_BASE}/khuyen-nghi-bon-phan",
            "Khuyến nghị bón phân N-P-K theo cây trồng",
            "Công cụ tham khảo nhu cầu N-P-K, chia lịch bón phân và cảnh báo an toàn theo cây trồng, tuổi cây và năng suất mục tiêu.",
            "Khuyến nghị bón phân",
        ),
    ]
    for filename, canonical, title, desc, heading in landing_pages:
        schema: dict | list[dict] = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": desc,
            "url": canonical,
            "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_BASE},
            "inLanguage": "vi",
        }
        if canonical == f"{SITE_BASE}/":
            schema = [
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": SITE_NAME,
                    "url": SITE_BASE,
                    "logo": f"{SITE_BASE}/og-cover.jpg",
                },
                {
                    "@context": "https://schema.org",
                    "@type": "WebSite",
                    "name": SITE_NAME,
                    "url": SITE_BASE,
                    "potentialAction": {
                        "@type": "SearchAction",
                        "target": f"{SITE_BASE}/tin-tuc?q={{search_term_string}}",
                        "query-input": "required name=search_term_string",
                    },
                },
            ]

        if filename == "home.html":
            body = _build_home_body(heading, desc)
        elif filename == "news.html":
            body = _build_news_index_body(heading, desc)
        elif filename == "guides.html":
            body = _build_guides_index_body(heading, desc)
        elif filename == "fertilizer.html":
            body = _build_fertilizer_index_body(heading, desc)
        else:
            body = f"<main><h1>{html.escape(heading)}</h1><p>{html.escape(desc)}</p></main>"
        _write(OUTPUT / filename, _page(title, desc, canonical, body, schema, og_type="website"))
        urls.append((canonical, today))

    for crop, label in crops.items():
        canonical = f"{SITE_BASE}/du-bao-gia/{crop}"
        title = f"Giá {label} hôm nay & dự báo 30 ngày"
        desc = f"Cập nhật giá {label} theo vùng trồng, giống, biểu đồ lịch sử và dự báo 30 ngày."
        dataset_schema = {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": f"Giá {label} Việt Nam - chuỗi thời gian theo vùng trồng",
            "description": desc,
            "url": canonical,
            "keywords": [f"giá {label}", "nông sản", "Việt Nam", "dự báo giá", label],
            "creator": {"@type": "Organization", "name": SITE_NAME, "url": SITE_BASE},
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "isAccessibleForFree": True,
            "spatialCoverage": {"@type": "Place", "name": "Việt Nam"},
            "temporalCoverage": "2024-01-01/" + today,
            "variableMeasured": [{"@type": "PropertyValue", "name": f"Giá {label}", "unitText": "VND/kg"}],
            "distribution": [
                {
                    "@type": "DataDownload",
                    "encodingFormat": "text/csv",
                    "contentUrl": f"{API_BASE}/api/v1/analytics/export.csv?crop={crop}",
                },
                {
                    "@type": "DataDownload",
                    "encodingFormat": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "contentUrl": f"{API_BASE}/api/v1/analytics/export.xlsx?crop={crop}",
                },
            ],
        }
        web_page_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": desc,
            "url": canonical,
            "mainEntity": {"@id": canonical + "#dataset"},
        }
        dataset_schema["@id"] = canonical + "#dataset"
        breadcrumb_schema = _breadcrumb(
            [
                ("Trang chủ", f"{SITE_BASE}/"),
                ("Dự báo giá nông sản", f"{SITE_BASE}/du-bao-gia/{crop}"),
            ]
        )
        _write(
            OUTPUT / "forecast" / f"{crop}.html",
            _page(title, desc, canonical, f"<main><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></main>", [dataset_schema, web_page_schema, breadcrumb_schema]),
        )
        urls.append((canonical, today))

    static_pages = [
        (
            "methodology.html",
            f"{SITE_BASE}/thuat-toan-du-bao",
            "Thuật toán dự báo giá nông sản",
            "Giải thích dữ liệu đầu vào, công thức dự báo, MAE, RMSE và cách đọc khoảng tin cậy.",
            "Thuật toán dự báo",
        ),
        (
            "fertilizer-methodology.html",
            f"{SITE_BASE}/khuyen-nghi-bon-phan/logic",
            "Giải thích logic khuyến nghị bón phân",
            "Cách hệ thống tính nhu cầu N-P-K, quy đổi ra phân thương mại, chia lịch bón và cảnh báo an toàn.",
            "Thuật toán bón phân",
        ),
    ]
    for filename, canonical, title, desc, crumb in static_pages:
        web_page_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": desc,
            "url": canonical,
        }
        breadcrumb_schema = _breadcrumb(
            [
                ("Trang chủ", f"{SITE_BASE}/"),
                (crumb, canonical),
            ]
        )
        _write(
            OUTPUT / filename,
            _page(title, desc, canonical, f"<main><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></main>", [web_page_schema, breadcrumb_schema]),
        )
        urls.append((canonical, today))

    news_views = [
        (
            "gia-sau-rieng",
            "Tin giá sầu riêng - cập nhật giá hôm nay",
            "Tin giá sầu riêng theo vùng trồng, giá Ri6, Monthong và bản tin xuất khẩu sầu riêng mới nhất.",
        ),
        (
            "gia-ca-phe",
            "Tin giá cà phê - cập nhật giá hôm nay",
            "Tin giá cà phê Robusta và Arabica tại Tây Nguyên, Đắk Lắk, Lâm Đồng.",
        ),
        (
            "gia-ho-tieu",
            "Tin giá hồ tiêu - cập nhật giá hôm nay",
            "Tin giá hồ tiêu Đắk Lắk, Đắk Nông, Bà Rịa - Vũng Tàu.",
        ),
    ]
    for slug, title, desc in news_views:
        canonical = f"{SITE_BASE}/tin-tuc/{slug}"
        breadcrumb_schema = _breadcrumb(
            [
                ("Trang chủ", f"{SITE_BASE}/"),
                ("Tin tức", f"{SITE_BASE}/tin-tuc"),
                (title.split("-")[0].strip(), canonical),
            ]
        )
        web_page_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": desc,
            "url": canonical,
        }
        _write(
            OUTPUT / "news-views" / f"{slug}.html",
            _page(title, desc, canonical, f"<main><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></main>", [web_page_schema, breadcrumb_schema]),
        )
        urls.append((canonical, today))
    return urls


def write_sitemap(urls: list[tuple[str, str | None]]) -> None:
    today = datetime.utcnow().date().isoformat()
    static_urls = [
        (f"{SITE_BASE}/", today),
        (f"{SITE_BASE}/tin-tuc", today),
        (f"{SITE_BASE}/huong-dan", today),
        (f"{SITE_BASE}/khuyen-nghi-bon-phan", today),
        (f"{SITE_BASE}/khuyen-nghi-bon-phan/logic", today),
    ]
    all_urls = []
    seen: set[str] = set()
    for loc, lastmod in static_urls + urls:
        if loc in seen:
            continue
        seen.add(loc)
        all_urls.append((loc, lastmod))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in all_urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(loc)}</loc>")
        lines.append(f"    <lastmod>{html.escape(lastmod or today)}</lastmod>")
        if loc == f"{SITE_BASE}/":
            lines.append("    <priority>1.0</priority>")
            lines.append("    <changefreq>daily</changefreq>")
        elif "/du-bao-gia/" in loc:
            lines.append("    <priority>0.9</priority>")
            lines.append("    <changefreq>daily</changefreq>")
        elif "/tin-tuc/" in loc and "category" not in loc and loc != f"{SITE_BASE}/tin-tuc":
            lines.append("    <priority>0.7</priority>")
            lines.append("    <changefreq>weekly</changefreq>")
        elif "/huong-dan/" in loc and loc != f"{SITE_BASE}/huong-dan":
            lines.append("    <priority>0.7</priority>")
            lines.append("    <changefreq>monthly</changefreq>")
        else:
            lines.append("    <priority>0.6</priority>")
            lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    _write(DIST / "sitemap.xml", "\n".join(lines))


def ping_indexnow(urls: list[tuple[str, str | None]]) -> None:
    if not INDEXNOW_KEY or not urls:
        return
    payload = json.dumps(
        {
            "host": "dubaonongsan.com",
            "key": INDEXNOW_KEY,
            "keyLocation": f"{SITE_BASE}/{INDEXNOW_KEY}.txt",
            "urlList": [url for url, _ in urls[:1000]],
        }
    ).encode("utf-8")
    try:
        request = Request(
            "https://api.indexnow.org/indexnow",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=20) as response:
            print(f"IndexNow: HTTP {response.status}")
    except Exception as exc:
        print(f"IndexNow ping skipped: {exc}")


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    urls: list[tuple[str, str | None]] = []
    urls.extend(render_static_pages())
    urls.extend(render_news())
    urls.extend(render_guides())
    write_sitemap(urls)
    ping_indexnow(urls)
    print(f"SEO HTML generated in {OUTPUT}")

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
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
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"
PUBLIC = ROOT / "frontend" / "public"
OUTPUT = DIST / "seo"


def _detect_indexnow_key() -> str:
    configured = os.environ.get("INDEXNOW_KEY", "").strip()
    if configured:
        return configured
    for key_file in sorted(PUBLIC.glob("*.txt")):
        key = key_file.stem.strip()
        try:
            value = key_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value == key and re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key):
            return key
    return ""


INDEXNOW_KEY = _detect_indexnow_key()


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


def _analytics_tags() -> str:
    index_html_path = DIST / "index.html"
    if not index_html_path.exists():
        return ""
    index_html = index_html_path.read_text(encoding="utf-8")
    tags = re.findall(r"<script\b[^>]*>.*?</script>", index_html, flags=re.DOTALL)
    selected = [
        tag.strip()
        for tag in tags
        if "DUBAONONGSAN_GA_ID" in tag or 'src="/inline-ga.js"' in tag
    ]
    return "\n  ".join(dict.fromkeys(selected))


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
        f'<script type="application/ld+json" nonce="dubaonongsan-jsonld">{_json_ld(item)}</script>'
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


def _inline_markdown(value: str) -> str:
    parts = re.split(r"(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))", value)
    rendered: list[str] = []
    for part in parts:
        if not part:
            continue
        link = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", part)
        if link:
            label, href = link.groups()
            rendered.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
            continue
        if part.startswith("**") and part.endswith("**"):
            rendered.append(f"<strong>{html.escape(part[2:-2])}</strong>")
            continue
        rendered.append(html.escape(part))
    return "".join(rendered)


def _table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|") if cell.strip()]


def _table_html(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    head, *body = rows
    head_html = "".join(f"<th>{_inline_markdown(cell)}</th>" for cell in head)
    body_html = "\n".join(
        "<tr>" + "".join(f"<td>{_inline_markdown(row[index] if index < len(row) else '')}</td>" for index in range(len(head))) + "</tr>"
        for row in body
    )
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table>"


def _guide_markdown_to_html(content: str) -> str:
    output: list[str] = []
    active_list: str | None = None
    active_quote: list[str] = []
    active_table: list[list[str]] = []

    def close_list() -> None:
        nonlocal active_list
        if active_list:
            output.append(f"</{active_list}>")
            active_list = None

    def close_quote() -> None:
        nonlocal active_quote
        if active_quote:
            output.append("<blockquote>" + "".join(f"<p>{_inline_markdown(line)}</p>" for line in active_quote) + "</blockquote>")
            active_quote = []

    def close_table() -> None:
        nonlocal active_table
        if active_table:
            output.append(_table_html(active_table))
            active_table = []

    def close_all() -> None:
        close_table()
        close_quote()
        close_list()

    for raw_line in content.replace("\r\n", "\n").splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("nguồn"):
            close_all()
            continue
        if line.startswith("IMAGE::"):
            close_all()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            close_all()
            level = min(max(len(heading.group(1)), 2), 4)
            text = re.sub(r"^\d+(?:\.\d+)?\.\s*", "", heading.group(2)).strip()
            output.append(f"<h{level}>{_inline_markdown(text)}</h{level}>")
            continue
        if line.startswith("|"):
            cells = _table_row(line)
            if cells and not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                close_quote()
                close_list()
                active_table.append(cells)
            continue
        close_table()
        if line.startswith(">"):
            close_list()
            quote = line.replace(">", "", 1).strip()
            if quote:
                active_quote.append(quote)
            continue
        close_quote()
        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if ordered:
            if active_list != "ol":
                close_list()
                output.append("<ol>")
                active_list = "ol"
            output.append(f"<li>{_inline_markdown(ordered.group(1).strip())}</li>")
            continue
        if bullet:
            if active_list != "ul":
                close_list()
                output.append("<ul>")
                active_list = "ul"
            output.append(f"<li>{_inline_markdown(bullet.group(1).strip())}</li>")
            continue
        close_list()
        output.append(f"<p>{_inline_markdown(line)}</p>")
    close_all()
    return "\n".join(output)


def _english_alternate_url(canonical: str) -> str:
    parsed = urlparse(canonical)
    path = parsed.path or "/"
    return f"{SITE_BASE}/en" if path == "/" else f"{SITE_BASE}/en{path}"


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
    analytics_tags = _analytics_tags()
    fallback_script = '<script src="/inline-seo-fallback.js" defer></script>'
    alternate_en = _english_alternate_url(canonical)

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
  <link rel="alternate" hreflang="vi" href="{canonical}" />
  <link rel="alternate" hreflang="en" href="{alternate_en}" />
  <link rel="alternate" hreflang="x-default" href="{canonical}" />
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
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  {article_meta}
  {schema_markup}
  {analytics_tags}
  {fallback_script}
  {asset_tags}
</head>
<body>
  <div id="seo-prerender" class="visually-hidden" aria-hidden="true">{body}</div>
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
        content = _guide_markdown_to_html(guide.get("content") or "")
        published_at = guide.get("published_at") or guide.get("updated_at")
        keywords = guide.get("tags") or ""
        body = f"<article><h1>{html.escape(title)}</h1><p>{html.escape(summary)}</p>{content}</article>"
        guide_schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": summary,
            "url": canonical,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
            "datePublished": published_at,
            "dateModified": published_at,
            "keywords": keywords,
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


def _build_news_index_body(heading: str, desc: str) -> str:
    """Build body for /tin-tuc index with the latest 30 news articles."""
    sections = [
        f"<main><h1>{html.escape(heading)}</h1>",
        f"<p>{html.escape(desc)}</p>",
    ]

    news = _fetch_news_for_index(limit=30)
    if news:
        by_category: dict[str, list[dict]] = {}
        for item in news:
            category = item.get("category") or "Tin nông nghiệp"
            by_category.setdefault(category, []).append(item)

        for category, items in by_category.items():
            sections.append(f"<h2>{html.escape(category)}</h2><ul>")
            for item in items:
                slug = _news_slug(item)
                title = item.get("title") or "Tin"
                summary = (item.get("summary") or item.get("excerpt") or "")[:300]
                source = item.get("source_name") or ""
                sections.append(
                    f'<li><a href="{SITE_BASE}/tin-tuc/{slug}">'
                    f"<strong>{html.escape(title)}</strong></a> "
                    f"({html.escape(source)}): {html.escape(summary)}</li>"
                )
            sections.append("</ul>")
    else:
        sections.append(
            "<h2>Nhóm tin theo dõi thường xuyên</h2>"
            "<ul>"
            "<li>Giá nông sản: sầu riêng, cà phê, hồ tiêu, lúa và các mặt hàng chủ lực theo vùng.</li>"
            "<li>Xuất khẩu: đơn hàng, kiểm dịch, tiêu chuẩn vùng trồng, logistics và biến động thị trường nhập khẩu.</li>"
            "<li>Vật tư đầu vào: phân bón, thuốc bảo vệ thực vật, giống, chi phí tưới và nhân công.</li>"
            "<li>Chính sách: quy định địa phương, truy xuất nguồn gốc, mã số vùng trồng và tiêu chuẩn chất lượng.</li>"
            "</ul>"
            "<p>Khi API tin tức tạm thời chưa phản hồi trong lúc prerender, trang vẫn mô tả rõ phạm vi bản tin để crawler "
            "hiểu đây là trung tâm cập nhật tin thị trường nông nghiệp, không phải trang rỗng. Bản SPA phía client sẽ tải "
            "danh sách tin mới nhất khi người dùng mở trang bằng trình duyệt.</p>"
            "<p>Độc giả có thể dùng trang này để theo dõi các tín hiệu ảnh hưởng trực tiếp tới quyết định bán hàng, giữ hàng, "
            "lên lịch thu hoạch hoặc chuẩn bị vật tư. Mỗi bản tin trên dubaonongsan.com luôn giữ liên kết về nguồn gốc để "
            "người đọc kiểm tra bối cảnh đầy đủ trước khi hành động.</p>"
        )

    sections.append(
        "<h2>Mô tả bản tin thị trường</h2>"
        "<p>Tin tức dubaonongsan.com tổng hợp từ các nguồn báo nông nghiệp Việt Nam "
        "như Báo Nông nghiệp và Môi trường, Vinanet, Báo Công Thương, Báo Nghệ An, "
        "Báo Hà Tĩnh, Sở Công Thương Đắk Lắk. Mỗi bài có liên kết về nguồn gốc, "
        "cập nhật 3 giờ một lần để theo kịp biến động giá và chính sách thị trường.</p>"
        "<p>Trang tin tức ưu tiên các chủ đề có tác động đến giá nông sản, xuất khẩu, "
        "vật tư đầu vào, thời tiết, vùng trồng và chính sách quản lý. Nội dung index "
        "giúp crawler không chạy JavaScript vẫn đọc được nhóm tin, nguồn tin và tóm tắt "
        "trước khi đi vào từng bài chi tiết.</p>"
    )
    sections.append("</main>")
    return "\n".join(sections)


def _build_fertilizer_index_body(heading: str, desc: str) -> str:
    """Build body for /khuyen-nghi-bon-phan. Static content explains the tool."""
    return f"""<main>
<h1>{html.escape(heading)}</h1>
<p>{html.escape(desc)}</p>

<h2>Cây trồng được hỗ trợ</h2>
<ul>
<li><strong>Cà phê vối Robusta</strong>: phù hợp đất bazan đỏ Tây Nguyên, granite xám, gneiss. Tham chiếu WASI 2016, IPI 2015.</li>
<li><strong>Hồ tiêu</strong>: bazan đỏ, acrisol. Tham chiếu IPI 2018.</li>
<li><strong>Sầu riêng</strong>: bazan đỏ, đất phù sa. Tham chiếu Poovarodom & Tawinteung, DRIS 2024 và tài liệu Thai DOA/ĐBSCL.</li>
</ul>

<h2>Dữ liệu đầu vào</h2>
<ul>
<li>Mẫu đất: texture, pH KCl, pH H2O, OC%, N%, P dễ tiêu (Bray II / Mehlich-3), K trao đổi (NH4OAc), Ca/Mg trao đổi, CEC.</li>
<li>Năng suất mục tiêu (tấn/ha/năm) và mật độ cây/ha.</li>
<li>Bối cảnh: vị trí (tỉnh, độ cao), khí hậu (lượng mưa, tưới tiêu), độ dốc, số năm canh tác.</li>
<li>Tuỳ chọn: lượng phân hữu cơ sẵn có, thương hiệu phân ưu tiên.</li>
</ul>

<h2>Đầu ra của công cụ</h2>
<ul>
<li>Tổng nhu cầu N-P2O5-K2O kg/ha/năm + lượng vôi bón.</li>
<li>Chia lịch bón theo giai đoạn sinh trưởng (đầu mùa, giữa mùa, cuối mùa, nuôi trái).</li>
<li>Quy đổi sang phân thương mại (NPK 16-16-8, urea, kali clorua, MOP, DAP) kèm số bao 50kg/ha.</li>
<li>Cảnh báo an toàn: dư đạm, thiếu kali, đất chua, đất kiềm, rủi ro rửa trôi mùa mưa.</li>
<li>Giải thích logic tính toán và nguồn tham chiếu khoa học.</li>
</ul>

<h2>Phương pháp luận</h2>
<p>Khuyến nghị bón phân dựa trên balance NPK: nhu cầu cây - cung từ đất - hiệu suất sử dụng. Hệ số điều chỉnh tính theo texture đất, OC%, pH, năng suất mục tiêu, lượng mưa và độ dốc. Chi tiết thuật toán tại
<a href="{SITE_BASE}/khuyen-nghi-bon-phan/logic">trang giải thích thuật toán bón phân</a>.</p>

<h2>Dữ liệu hiệu chỉnh sau vụ</h2>
<p>Sau khi tính khuyến nghị, hệ thống tạo mã phiên 8 ký tự để người trồng gửi báo cáo năng suất tại
<a href="{SITE_BASE}/bao-cao-nang-suat">trang báo cáo năng suất</a>. Dữ liệu này dùng cho bước chuẩn bị Tier 2.</p>

<h2>Lưu ý quan trọng</h2>
<p>Công cụ chỉ mang tính tham khảo. Quyết định cuối cùng cần dựa trên kết quả phân tích đất gần nhất tại vườn, kinh nghiệm thực tế, và tư vấn của kỹ sư nông nghiệp địa phương. Không thay thế cho khuyến cáo của Viện Khoa học Nông nghiệp.</p>
</main>"""


def _build_yield_feedback_body(heading: str, desc: str) -> str:
    """Build static body for /bao-cao-nang-suat."""
    return f"""<main>
<h1>{html.escape(heading)}</h1>
<p>{html.escape(desc)}</p>

<h2>Dữ liệu cần gửi</h2>
<ul>
<li>Mã khuyến nghị 8 ký tự được hiển thị sau khi tính khuyến nghị bón phân.</li>
<li>Năng suất thực tế sau thu hoạch theo tấn/ha.</li>
<li>Ngày thu hoạch, mức làm theo khuyến nghị, đánh giá và ghi chú hiện trường nếu có.</li>
</ul>

<h2>Mục đích sử dụng</h2>
<p>Dữ liệu báo cáo năng suất được nối với phiên khuyến nghị trước đó để tạo bộ dữ liệu huấn luyện Tier 2. Hệ thống dùng dữ liệu này để so sánh lượng N-P-K đã khuyến nghị với kết quả thực tế theo cây trồng, giống, vùng và điều kiện đất.</p>

<h2>Lưu ý riêng tư</h2>
<p>Thông tin liên hệ là tuỳ chọn, chỉ dùng khi cần hỏi thêm bối cảnh vườn. Người dùng có thể gửi lại cùng một mã phiên để cập nhật báo cáo mới nhất.</p>
</main>"""


def _build_forecast_body(crop: str, crop_label: str, title: str, desc: str) -> str:
    """Build body for /du-bao-gia/{crop} with current price table and forecast preview."""
    sections = [
        f"<main><h1>{html.escape(title)}</h1>",
        f"<p>{html.escape(desc)}</p>",
    ]

    prices = _fetch_prices_for_crop(crop, limit=20)
    if prices:
        sections.append(f"<h2>Giá {html.escape(crop_label)} hiện tại theo vùng và giống</h2>")
        sections.append("<table>")
        sections.append(
            "<thead><tr><th>Tỉnh</th><th>Vùng</th><th>Giống</th>"
            "<th>Loại</th><th>Giá min (VND/kg)</th><th>Giá max (VND/kg)</th>"
            "<th>Ngày cập nhật</th></tr></thead>"
        )
        sections.append("<tbody>")
        for price in prices:
            timestamp = (price.get("timestamp") or "")[:10]
            sections.append(
                "<tr>"
                f"<td>{html.escape(str(price.get('province') or ''))}</td>"
                f"<td>{html.escape(str(price.get('region') or ''))}</td>"
                f"<td>{html.escape(str(price.get('variety') or ''))}</td>"
                f"<td>{html.escape(str(price.get('quality_grade') or ''))}</td>"
                f"<td>{int(price.get('min_price_vnd') or 0):,}</td>"
                f"<td>{int(price.get('max_price_vnd') or 0):,}</td>"
                f"<td>{html.escape(timestamp)}</td>"
                "</tr>"
            )
        sections.append("</tbody></table>")
    else:
        sections.append(f"<p>Dữ liệu giá {html.escape(crop_label)} đang được cập nhật.</p>")

    try:
        url = f"{API_BASE}/api/v1/analytics/forecast-30-days?crop={crop}&region_id=1&variety=1"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "DubaonongsanSEOPrerender/1.0",
            },
        )
        with urlopen(request, timeout=20) as response:
            forecast = json.loads(response.read().decode("utf-8"))
        if isinstance(forecast, list) and forecast:
            sections.append(f"<h2>Dự báo giá {html.escape(crop_label)} 30 ngày tới (vùng trọng điểm)</h2>")
            sections.append("<ul>")
            indices = [0, 1, 2, 3, 4, 5, 6, 13, 20, 29]
            for index in indices:
                if index >= len(forecast):
                    break
                point = forecast[index]
                ts = (point.get("timestamp") or "")[:10]
                fp = int(point.get("forecast_price_vnd") or 0)
                lo = int(point.get("confidence_low_vnd") or 0)
                hi = int(point.get("confidence_high_vnd") or 0)
                sections.append(
                    f"<li>Ngày {ts}: dự báo {fp:,} VND/kg "
                    f"(khoảng tin cậy {lo:,} - {hi:,})</li>"
                )
            sections.append("</ul>")
    except Exception as exc:
        print(f"SEO warning: fetch forecast for {crop} failed: {exc}")

    sections.append(
        f"<h2>Về dữ liệu giá {html.escape(crop_label)}</h2>"
        f"<p>Giá {html.escape(crop_label)} được dubaonongsan.com cập nhật hàng ngày "
        "từ các nguồn công khai bao gồm bảng giá nông sản, báo nông nghiệp địa phương, "
        "sở công thương các tỉnh trọng điểm. Dữ liệu được phân loại theo giống, vùng, "
        "loại (A/B/C) và mức chợ đầu mối. Mô hình dự báo 30 ngày sử dụng kết hợp "
        "machine learning gradient boosting và phân tích chuỗi thời gian để ước lượng "
        "biến động giá kỳ vọng kèm khoảng tin cậy.</p>"
        f"<p>Khi bảng giá hoặc forecast của {html.escape(crop_label)} chưa tải được trong lúc prerender, "
        "trang vẫn cung cấp mô tả dữ liệu, phạm vi vùng trồng, cách đọc giá thấp nhất/cao nhất, "
        "và cảnh báo rằng giá thực tế cần được đối chiếu với nguồn thu mua tại địa phương trước khi ra quyết định.</p>"
        f'<p>Để xem chi tiết thuật toán, truy cập '
        f'<a href="{SITE_BASE}/thuat-toan-du-bao">trang giải thích thuật toán dự báo</a>.</p>'
    )
    sections.append("</main>")
    return "\n".join(sections)


def _build_methodology_body(title: str, desc: str) -> str:
    """Static content explaining the forecast algorithm."""
    return f"""<main>
<h1>{html.escape(title)}</h1>
<p>{html.escape(desc)}</p>

<h2>Nguồn dữ liệu đầu vào</h2>
<ul>
<li><strong>Giá lịch sử</strong>: scrape hàng ngày từ banggianongsan.com, baonghean.vn, congthuong.vn, baohatinh.vn, sở công thương Đắk Lắk, vietnamvn.com, coffee market.</li>
<li><strong>Thời tiết</strong>: Open-Meteo API cho từng tỉnh trọng điểm (nhiệt độ tối đa, lượng mưa, độ ẩm).</li>
<li><strong>Khối lượng giao dịch</strong>: trích xuất từ các bài viết có khối lượng được công bố.</li>
<li><strong>Chỉ số chín</strong>: dữ liệu cảm biến IoT từ một số vùng pilot, cập nhật qua endpoint maturity-telemetry.</li>
<li><strong>Báo cáo của nông dân</strong>: giá địa phương được người dùng báo qua form, dùng để cross-check, không đưa vào training trực tiếp.</li>
</ul>

<h2>Cách dự báo</h2>
<p>Hiện tại mô hình dự báo dùng baseline statistical kết hợp với gradient boosting (LightGBM khi có đủ artifact). Khi tích lũy đủ ≥ 1000 điểm/series, sẽ chuyển sang LSTM deep learning. Quy trình:</p>
<ol>
<li>Lấy cửa sổ 60 ngày gần nhất cho cặp (vùng, giống) đang xem.</li>
<li>Tính lag features (giá 1, 2, 3, 7, 14, 30 ngày trước), rolling mean và std (7, 14, 30 ngày), slope tuyến tính 14 ngày.</li>
<li>Bổ sung tín hiệu mùa vụ (tháng, ngày trong tuần, giai đoạn Tết) và tín hiệu thời tiết lag.</li>
<li>Mô hình trả 30 giá trị giá kỳ vọng cho 30 ngày kế tiếp.</li>
<li>Áp dụng giới hạn dưới (price floor) để tránh dự báo phi lý sau biến động lớn.</li>
</ol>

<h2>Khoảng tin cậy</h2>
<p>Khoảng tin cậy (confidence interval) được ước tính từ độ biến động (volatility) cửa sổ 30 ngày gần nhất, scale theo giá hiện tại. Mặc định khoảng ±8% cho sầu riêng, cà phê, hồ tiêu; ±5.5% cho lúa do biến động thấp hơn.</p>

<h2>Đo độ chính xác</h2>
<ul>
<li><strong>RMSE (Root Mean Squared Error)</strong>: căn bậc hai của trung bình bình phương sai số. Nhạy với outlier lớn. Đo bằng VND/kg.</li>
<li><strong>MAE (Mean Absolute Error)</strong>: trung bình độ lớn sai số tuyệt đối. Robust hơn RMSE.</li>
<li>Backtest trượt: mỗi đợt retrain (mặc định 24h/lần) chạy backtest với cửa sổ 60-ngày-train, 30-ngày-test trên dữ liệu lịch sử.</li>
<li>Số mẫu backtest và số series được đánh giá hiển thị tại endpoint <code>/api/v1/analytics/model-metrics</code>.</li>
</ul>

<h2>Hạn chế</h2>
<ul>
<li>Mô hình không nắm bắt được sự kiện bất thường (kiểm dịch, lệnh cấm xuất khẩu đột ngột, thiên tai lớn).</li>
<li>Dữ liệu phụ thuộc nguồn scrape — nếu nguồn thay đổi HTML hoặc dừng cập nhật, dự báo lệch.</li>
<li>Forecast càng xa, sai số càng tăng. Ngày 1-7 đáng tin cậy hơn ngày 21-30.</li>
<li>Không áp dụng cho mục đích giao dịch tài chính — chỉ tham khảo định hướng cho nông dân và thương lái.</li>
</ul>

<h2>Cập nhật mô hình</h2>
<p>Mô hình được retrain định kỳ 24 giờ một lần qua scheduler nội bộ. Khi có model mới, artifact được atomic-swap để tránh API đọc file dở. Phiên bản model hiện tại có thể xem qua endpoint <code>/api/v1/analytics/model-metrics</code> field <code>model_kind</code>.</p>
</main>"""


def _build_fertilizer_methodology_body(title: str, desc: str) -> str:
    """Static content explaining fertilizer recommendation logic."""
    return f"""<main>
<h1>{html.escape(title)}</h1>
<p>{html.escape(desc)}</p>

<h2>Nguyên lý tính nhu cầu N-P-K</h2>
<p>Lượng phân khuyến nghị dựa trên cân bằng nutrient: nhu cầu cây trồng = năng suất mục tiêu × hệ số hấp thu - lượng có sẵn trong đất × hệ số hiệu suất.</p>
<ul>
<li><strong>Đạm (N)</strong>: tính theo năng suất mục tiêu, có hiệu chỉnh theo OC% (đất giàu hữu cơ giảm N) và lượng mưa (mưa nhiều tăng N do rửa trôi).</li>
<li><strong>Lân (P2O5)</strong>: tính theo P dễ tiêu trong đất, hiệu chỉnh theo pH (đất chua giảm hiệu suất P).</li>
<li><strong>Kali (K2O)</strong>: tính theo K trao đổi và CEC, hiệu chỉnh theo loại đất (đất cát giảm CEC).</li>
</ul>

<h2>Bảng tham chiếu khoa học</h2>
<ul>
<li>Cà phê vối: WASI 2016, IPI 2015 — dose 220-330 kg N/ha/năm tuỳ texture.</li>
<li>Hồ tiêu: IPI 2018 — dose 200-300 kg N/ha/năm.</li>
<li>Sầu riêng: Poovarodom & Tawinteung, DRIS 2024, Thai DOA/ĐBSCL — 1,0-1,8 kg N/cây/năm, tương đương khoảng 150-270 kg N/ha tại mật độ 150 cây/ha.</li>
</ul>

<h2>Phân tích đất cần thiết</h2>
<p>Để khuyến nghị chính xác, cần mẫu đất phân tích:</p>
<ol>
<li>pH KCl và pH H2O (đo bằng máy pH meter).</li>
<li>OC% (carbon hữu cơ) bằng phương pháp Walkley-Black.</li>
<li>N tổng (Kjeldahl).</li>
<li>P dễ tiêu (Bray II cho đất chua Tây Nguyên hoặc Mehlich-3).</li>
<li>K trao đổi (NH4OAc 1M).</li>
<li>Ca, Mg trao đổi và CEC.</li>
</ol>

<h2>Chia lịch bón</h2>
<p>Lượng tổng được chia thành 3-5 đợt bón tuỳ giai đoạn:</p>
<ol>
<li>Cà phê sau thu hoạch (tháng 1-2): 15% N + 50% P2O5 + 15% K2O.</li>
<li>Cà phê đầu mùa mưa (tháng 5-6): 30% N + 25% P2O5 + 25% K2O.</li>
<li>Cà phê giữa mùa mưa (tháng 7-8): 30% N + 15% P2O5 + 30% K2O.</li>
<li>Cà phê cuối mùa mưa (tháng 9-10): 25% N + 10% P2O5 + 30% K2O.</li>
</ol>

<h2>Quy đổi sang phân thương mại</h2>
<p>Hệ thống tự quy đổi lượng nguyên chất N-P-K sang:</p>
<ul>
<li>Urea 46% N</li>
<li>SA (sulfate ammonium) 21% N + 24% S</li>
<li>DAP 18-46-0</li>
<li>NPK 16-16-8, 20-20-15, 15-15-15</li>
<li>Kali clorua (MOP) 60% K2O cho giai đoạn phù hợp.</li>
<li>Sulfate kali (SOP) 50% K2O cho sầu riêng giai đoạn nuôi trái hoặc cây nhạy với Cl.</li>
</ul>
<p>Kết quả hiển thị số bao 50kg/ha kèm thương hiệu nếu user chỉ định.</p>

<h2>Cảnh báo và lưu ý</h2>
<ul>
<li>Nếu pH KCl &lt; 4.5: khuyến cáo bón vôi (1-2 tấn CaCO3/ha) trước khi bón phân.</li>
<li>Nếu OC &lt; 1%: cần bón hữu cơ (phân chuồng hoai, vermicompost) 5-10 tấn/ha.</li>
<li>Đất dốc &gt; 15%: chia nhiều lần bón nhỏ để giảm rửa trôi.</li>
<li>Tránh bón phân vào thời điểm mưa to dự báo trong 24h.</li>
<li>Hồ tiêu nếu P đất vượt 96 mg P/kg: tạm ngưng P2O5.</li>
<li>Sầu riêng giai đoạn nuôi trái: không dùng KCl; hệ thống tự đổi sang K2SO4 nếu người dùng chọn KCl.</li>
</ul>

<h2>Cách đọc kết quả</h2>
<p>Kết quả khuyến nghị cần được đọc theo ba lớp: lượng dinh dưỡng nguyên chất, lịch chia đợt bón và cảnh báo an toàn. Nếu đất quá chua, thiếu hữu cơ hoặc có nguy cơ rửa trôi cao, người dùng nên xử lý nền đất trước khi tăng lượng N-P-K. Nếu năng suất mục tiêu quá cao so với tuổi cây hoặc mật độ thực tế, hệ thống ưu tiên cảnh báo để tránh bón dư gây sốc rễ, cháy lá hoặc tăng sâu bệnh.</p>

<h2>Hạn chế</h2>
<p>Công cụ là khung tham chiếu. Quyết định cuối cùng cần kết hợp với phân tích đất cập nhật trong năm, kinh nghiệm thực tế của vườn và tư vấn của kỹ sư nông học địa phương.</p>
</main>"""


def render_static_pages() -> list[tuple[str, str | None]]:
    crops = {
        "sau_rieng": "sầu riêng",
        "ca_phe": "cà phê",
        "ho_tieu": "hồ tiêu",
        "lua": "lúa",
    }
    urls: list[tuple[str, str | None]] = []
    today = datetime.now(timezone.utc).date().isoformat()
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
        (
            "selling-time.html",
            f"{SITE_BASE}/thoi-diem-ban",
            "Thời điểm bán nông sản theo dự báo giá",
            "Xếp hạng ngày bán tốt nhất trong 30 ngày tới theo dự báo giá nông sản và chi phí lưu kho.",
            "Thời điểm bán",
        ),
        (
            "regional-arbitrage.html",
            f"{SITE_BASE}/chenh-lech-vung",
            "Chênh lệch giá nông sản theo tỉnh",
            "Quét các cặp tỉnh có chênh lệch giá sau chi phí vận chuyển ước tính để tham khảo cơ hội bán hàng.",
            "Chênh lệch vùng",
        ),
        (
            "cross-crop.html",
            f"{SITE_BASE}/so-sanh-cay-trong",
            "So sánh cây trồng theo tỉnh",
            "So sánh lợi nhuận tham khảo giữa sầu riêng, cà phê, hồ tiêu và lúa theo giá, năng suất và độ phù hợp của tỉnh.",
            "So sánh cây trồng",
        ),
        (
            "yield-feedback.html",
            f"{SITE_BASE}/bao-cao-nang-suat",
            "Báo cáo năng suất sau khuyến nghị bón phân",
            "Gửi năng suất thực tế sau khi dùng khuyến nghị bón phân để chuẩn bị dữ liệu hiệu chỉnh Tier 2.",
            "Báo cáo năng suất",
        ),
        (
            "roi.html",
            f"{SITE_BASE}/roi-uoc-tinh",
            "Ước tính lợi nhuận nông vụ",
            "Tính nhanh doanh thu, chi phí phân bón và lợi nhuận dự kiến theo giá vật tư đầu vào mới nhất.",
            "Ước tính lợi nhuận nông vụ",
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
        elif filename == "yield-feedback.html":
            body = _build_yield_feedback_body(heading, desc)
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
            _page(
                title,
                desc,
                canonical,
                _build_forecast_body(crop, label, title, desc),
                [dataset_schema, web_page_schema, breadcrumb_schema],
            ),
        )
        urls.append((canonical, today))

    input_canonical = f"{SITE_BASE}/du-bao-gia/phan-bon"
    input_title = "Dự báo giá phân bón thế giới"
    input_desc = "Theo dõi giá Urê, DAP và Kali MOP thế giới theo USD/tấn, kèm dự báo 30 ngày và mức tăng giảm mỗi ngày để tham chiếu giá phân bón địa phương."
    input_body = f"""<main>
<h1>{html.escape(input_title)}</h1>
<p>{html.escape(input_desc)}</p>
<h2>Nhóm hàng hóa theo dõi</h2>
<ul>
<li>Urê thế giới theo USD/tấn.</li>
<li>DAP thế giới theo USD/tấn.</li>
<li>Kali MOP thế giới theo USD/tấn.</li>
</ul>
<h2>Cách đọc dự báo</h2>
<p>Mỗi ngày có giá dự báo, mức đổi theo ngày và mức đổi cộng dồn so với giá tham chiếu hiện tại. Người dùng có thể lấy tỷ lệ phần trăm này làm tín hiệu đầu vào khi so với báo giá đại lý địa phương.</p>
<h2>Không phải giá đại lý địa phương</h2>
<p>Trang này không trộn bảng giá phân bón địa phương vào biểu đồ. Mục tiêu là theo dõi giá hàng hóa thế giới và xu hướng tăng giảm để tham chiếu cho quyết định mua vật tư.</p>
</main>"""
    input_dataset_schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Dự báo giá phân bón thế giới",
        "description": input_desc,
        "url": input_canonical,
        "keywords": ["giá phân bón thế giới", "dự báo phân bón", "ure", "dap", "kali", "mop"],
        "creator": {"@type": "Organization", "name": SITE_NAME, "url": SITE_BASE},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "isAccessibleForFree": True,
        "spatialCoverage": {"@type": "Place", "name": "Thị trường thế giới"},
        "temporalCoverage": "2025-06-01/" + today,
        "variableMeasured": [
            {"@type": "PropertyValue", "name": "Giá phân bón thế giới", "unitText": "USD/tấn"},
            {"@type": "PropertyValue", "name": "Mức tăng giảm dự báo", "unitText": "%/ngày"},
        ],
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": "application/json",
                "contentUrl": f"{API_BASE}/api/v1/advisory/world-fertilizer/forecast?commodity=urea",
            }
        ],
    }
    input_page_schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": input_title,
        "description": input_desc,
        "url": input_canonical,
        "mainEntity": {"@id": input_canonical + "#dataset"},
    }
    input_dataset_schema["@id"] = input_canonical + "#dataset"
    _write(
        OUTPUT / "forecast" / "phan-bon.html",
        _page(
            input_title,
            input_desc,
            input_canonical,
            input_body,
            [
                input_dataset_schema,
                input_page_schema,
                _breadcrumb(
                    [
                        ("Trang chủ", f"{SITE_BASE}/"),
                        ("Giá phân bón thế giới", input_canonical),
                    ]
                ),
            ],
        ),
    )
    urls.append((input_canonical, today))

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
        if filename == "methodology.html":
            body = _build_methodology_body(title, desc)
        elif filename == "fertilizer-methodology.html":
            body = _build_fertilizer_methodology_body(title, desc)
        else:
            body = f"<main><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></main>"
        _write(
            OUTPUT / filename,
            _page(title, desc, canonical, body, [web_page_schema, breadcrumb_schema]),
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
    today = datetime.now(timezone.utc).date().isoformat()
    static_urls = [
        (f"{SITE_BASE}/", today),
        (f"{SITE_BASE}/tin-tuc", today),
        (f"{SITE_BASE}/huong-dan", today),
        (f"{SITE_BASE}/khuyen-nghi-bon-phan", today),
        (f"{SITE_BASE}/thoi-diem-ban", today),
        (f"{SITE_BASE}/chenh-lech-vung", today),
        (f"{SITE_BASE}/so-sanh-cay-trong", today),
        (f"{SITE_BASE}/khuyen-nghi-bon-phan/logic", today),
        (f"{SITE_BASE}/bao-cao-nang-suat", today),
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

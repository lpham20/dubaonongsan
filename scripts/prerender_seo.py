from __future__ import annotations

import html
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
import json


API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8010").rstrip("/")
SITE_BASE = os.environ.get("SITE_BASE", "https://dubaonongsan.com").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"
OUTPUT = DIST / "seo"


def _slug_text(value: str) -> str:
    value = value.strip().lower()
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
        with urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception as exc:
        print(f"SEO prerender warning: cannot fetch {path} from {API_BASE}: {exc}")
        return []


def _page(title: str, description: str, canonical: str, body: str, schema: dict | None = None) -> str:
    escaped_title = html.escape(title)
    escaped_description = html.escape(description[:180])
    schema_block = ""
    if schema:
        schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title} | Dự báo nông sản</title>
  <meta name="description" content="{escaped_description}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{escaped_title}" />
  <meta property="og:description" content="{escaped_description}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:image" content="{SITE_BASE}/og-cover.jpg" />
  <meta name="twitter:card" content="summary_large_image" />
  {schema_block}
</head>
<body>{body}</body>
</html>"""


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
        schema = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": title,
            "description": summary[:180],
            "url": canonical,
            "datePublished": published_at,
            "publisher": {"@type": "Organization", "name": "Dự báo nông sản"},
        }
        _write(OUTPUT / "news" / f"{slug}.html", _page(title, summary, canonical, body, schema))
        urls.append((canonical, published_at[:10] if isinstance(published_at, str) else None))
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
        published_at = guide.get("published_at")
        body = f"<article><h1>{html.escape(title)}</h1><p>{html.escape(summary)}</p><div>{content}</div></article>"
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": summary,
            "datePublished": published_at,
            "publisher": {"@type": "Organization", "name": "Dự báo nông sản"},
        }
        _write(OUTPUT / "guides" / f"{slug}.html", _page(title, summary, canonical, body, schema))
        urls.append((canonical, published_at[:10] if isinstance(published_at, str) else None))
    return urls


def render_static_pages() -> list[tuple[str, str | None]]:
    crops = {
        "sau_rieng": "sầu riêng",
        "ca_phe": "cà phê",
        "ho_tieu": "hồ tiêu",
        "lua": "lúa",
    }
    urls: list[tuple[str, str | None]] = []
    for crop, label in crops.items():
        canonical = f"{SITE_BASE}/du-bao-gia/{crop}"
        title = f"Giá {label} hôm nay & dự báo 30 ngày"
        desc = f"Cập nhật giá {label} theo vùng trồng, giống, biểu đồ lịch sử và dự báo 30 ngày."
        schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": f"Giá {label}",
            "description": desc,
            "category": f"Nông sản / {label}",
            "offers": {"@type": "AggregateOffer", "priceCurrency": "VND", "offerCount": 1},
        }
        _write(OUTPUT / "forecast" / f"{crop}.html", _page(title, desc, canonical, f"<main><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p></main>", schema))
        urls.append((canonical, datetime.utcnow().date().isoformat()))

    canonical = f"{SITE_BASE}/thuat-toan-du-bao"
    title = "Thuật toán dự báo giá nông sản"
    desc = "Giải thích dữ liệu đầu vào, công thức dự báo, MAE, RMSE và cách đọc khoảng tin cậy."
    _write(OUTPUT / "methodology.html", _page(title, desc, canonical, f"<main><h1>{title}</h1><p>{desc}</p></main>"))
    urls.append((canonical, None))
    return urls


def write_sitemap(urls: list[tuple[str, str | None]]) -> None:
    static_urls = [
        (f"{SITE_BASE}/", None),
        (f"{SITE_BASE}/tin-tuc", None),
        (f"{SITE_BASE}/huong-dan", None),
        (f"{SITE_BASE}/tin-tuc/category/ca-phe", None),
        (f"{SITE_BASE}/tin-tuc/category/sau-rieng", None),
        (f"{SITE_BASE}/tin-tuc/category/ho-tieu", None),
        (f"{SITE_BASE}/tin-tuc/category/phan-bon-vat-tu", None),
    ]
    all_urls = static_urls + urls
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in all_urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(loc)}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{html.escape(lastmod)}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    _write(DIST / "sitemap.xml", "\n".join(lines))


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    urls = []
    urls.extend(render_static_pages())
    urls.extend(render_news())
    urls.extend(render_guides())
    write_sitemap(urls)
    print(f"SEO HTML generated in {OUTPUT}")

# Báo cáo SEO Audit — Nông Nghiệp Số

> **Đối tượng audit:** Website nông nghiệp phi lợi nhuận, dùng React SPA + Vite, đang muốn lên top Google để chạy quảng cáo.
>
> **Đối tượng người dùng mục tiêu:** Nông dân nhỏ lẻ Việt Nam (chủ yếu mobile), chuyên gia + công ty nông nghiệp.
>
> **Cách dùng tài liệu này:**
> - Mỗi vấn đề có **đường dẫn file**, **giải thích đơn giản tại sao quan trọng**, và **code/cấu hình cụ thể để fix**.
> - Đưa file này cho AI agent (Claude/Cursor/Copilot) là chạy được luôn.
> - Mỗi vấn đề được đánh số `[SEO-NNN]` để bạn track.

---

## 1. Tổng quan tech stack

**Frontend:**
- **Framework:** React 18.3 (SPA — Single Page Application thuần)
- **Build tool:** Vite 6
- **Language:** TypeScript 5.7
- **Routing:** ❌ KHÔNG dùng `react-router` — chỉ dùng `useState` để switch giữa "sections"
- **Styling:** Vanilla CSS (1 file 114 KB, 15 media queries)
- **Charts:** Recharts (378 KB JS bundle)
- **Icons:** Phosphor Icons (140 KB JS bundle)
- **SSR/SSG:** ❌ KHÔNG có (không Next.js, không Remix, không Astro)
- **Meta tags động:** ❌ KHÔNG có (không react-helmet, không Vite SSR plugin)

**Backend (FastAPI):** Có route `/api/v1/content/news`, `/api/v1/content/guides` trả JSON. **Không có route trả HTML cho bot Google.**

**SEO assets hiện tại:**
- `frontend/index.html` — có meta tags + Open Graph + JSON-LD `Organization` & `WebSite`
- `frontend/public/sitemap.xml` — chỉ liệt kê 8 URL (homepage + sections), **không có URL từng bài viết**
- `frontend/public/robots.txt` — basic, allow all
- `scripts/prerender_seo.py` — có script pre-render HTML cho SEO **nhưng chưa chạy** (folder `dist/seo/` chưa tồn tại)

**Cấu trúc folder chính:**
```
marketai/
├── frontend/
│   ├── index.html              ← meta tags tĩnh
│   ├── public/                  ← sitemap, robots, ảnh
│   └── src/
│       ├── App.tsx              ← component gốc, quản lý state "section"
│       ├── main.tsx             ← entry point React
│       ├── components/          ← HomePage, NewsPortal, GuideLibrary, etc.
│       ├── contexts/AuthContext.tsx
│       └── lib/api.ts           ← fetch JSON từ backend
├── backend/                     ← FastAPI, không serve HTML
└── scripts/prerender_seo.py     ← script tạo HTML tĩnh (chưa chạy)
```

---

## 2. Điểm SEO tổng thể: **22/100** 🔴

**Tại sao thấp như vậy?** Đây là website React SPA thuần. Google bot khi vào sẽ chỉ thấy:
```html
<div id="root"></div>
```
Toàn bộ nội dung (giá, tin tức, hướng dẫn kỹ thuật) chỉ render sau khi browser chạy JavaScript. Google bot có chạy JS được nhưng:
1. **Chậm** — có thể bot index trước khi JS load xong
2. **Bị giới hạn** — Google ưu tiên index những trang HTML "ready"
3. **Không chia URL** — toàn bộ website chỉ có **1 URL duy nhất** (`/`). 200 bài viết, 50 hướng dẫn kỹ thuật, 10 dự báo giá → Google chỉ thấy **1 trang**

**Phân loại điểm:**
| Tiêu chí | Điểm | Ghi chú |
|---|---|---|
| Crawlability (Google đọc được) | 3/10 | SPA → Google khó index nội dung sâu |
| URL Structure | 1/10 | Chỉ 1 URL, không có URL bài viết riêng |
| On-page (title, H1, meta) | 4/10 | Index.html OK nhưng tất cả pages dùng chung |
| Schema markup | 3/10 | Chỉ có Organization + WebSite, thiếu Article/HowTo/Product |
| Mobile + Performance | 3/10 | Ảnh hero 2.5-3.3 MB PNG → cực chậm trên 4G nông thôn |
| Internal linking | 2/10 | Click nội dung mở ra link bên ngoài, không có backlink nội bộ |
| Sitemap | 3/10 | Có nhưng chỉ 8 URL, không tự động generate từ DB |
| Image SEO | 1/10 | `alt=""` cho tất cả ảnh |

**So sánh:** Một trang nông nghiệp tốt (như VnExpress chuyên mục Kinh tế) sẽ ở mức 75-90/100.

---

## 3. CRITICAL ISSUES — Phải sửa ngay 🔴

> **Đây là 7 vấn đề khiến Google CHƯA THỂ index hiệu quả.** Không sửa các mục này thì làm SEO khác cũng vô ích.

---

### [SEO-001] 🔴 SPA Không Có SSR — Google Không Đọc Được Nội Dung

**File ảnh hưởng:**
- `frontend/index.html` (chỉ có `<div id="root"></div>`)
- `frontend/src/main.tsx`
- Toàn bộ `frontend/src/components/`

**Tác hại — giải thích đơn giản:**

Hãy tưởng tượng bạn có 200 bài tin tức + 50 bài hướng dẫn kỹ thuật. Khi Google bot ghé thăm website, nó sẽ thấy:

```html
<!-- Google bot thấy: -->
<html>
  <head>...</head>
  <body><div id="root"></div></body>
</html>
```

Nội dung "Cách chăm sóc sầu riêng mùa ra hoa" chỉ xuất hiện SAU KHI JavaScript chạy + gọi API + render React. Google có chạy JS nhưng:
- Chậm hơn nhiều so với HTML có sẵn
- Bot Google Ad Sense (cần để chạy quảng cáo) **không** chạy JS — nó chỉ đọc HTML thuần
- Mất 70% cơ hội xếp hạng

**Cách sửa — 3 phương án (xếp từ dễ đến khó):**

#### Phương án A — Pre-rendering tĩnh (DỄ NHẤT, làm ngay được)
Dùng script `scripts/prerender_seo.py` đã có sẵn, integrate vào build pipeline:

```bash
# Tạo file frontend/build-with-seo.sh
#!/bin/bash
set -e
cd frontend
npm run build
cd ..
python scripts/prerender_seo.py
echo "✓ Build xong với SEO HTML trong frontend/dist/seo/"
```

Cập nhật `frontend/package.json` đã có `build:seo`. Đảm bảo script được chạy trước deploy:
```json
{
  "scripts": {
    "build": "tsc && vite build && python ../scripts/prerender_seo.py"
  }
}
```

Sau đó **cấu hình Cloudflare Pages** để serve HTML tĩnh khi bot truy cập:
- Tạo file `frontend/public/_redirects`:
```
# Redirect bot Google đến HTML tĩnh
/tin-tuc/:slug   /seo/news/:slug.html  200
/huong-dan/:slug /seo/guides/:slug.html  200
# Mọi URL khác → SPA
/*  /index.html  200
```

#### Phương án B — Migrate sang Next.js (BỀN VỮNG NHẤT, khó hơn)
- Effort: 1 tuần code + test
- Lợi ích: SSR/SSG tự động, Google index ngay lập tức
- App.tsx hiện tại tương thích ~70% với Next.js

#### Phương án C — Astro (GIỮA, KHUYẾN NGHỊ)
- Effort: 3-4 ngày
- Astro = static site generator, render React component thành HTML thuần
- Phù hợp với website nông nghiệp (chủ yếu là content + ít tương tác)

> **Khuyến nghị cho bạn:** Bắt đầu với **Phương án A** (1-2 ngày), sau khi traffic tăng thì migrate sang **Astro** (Phương án C).

---

### [SEO-002] 🔴 Không Có URL Riêng Cho Từng Bài Viết / Hướng Dẫn

**File ảnh hưởng:**
- `frontend/src/App.tsx` — toàn bộ "routing" dùng `useState section`
- `frontend/src/components/NewsPortal.tsx:308, 320, 388` — link news mở external
- `frontend/src/components/GuideLibrary.tsx` — guide hiển thị trong panel, không có URL

**Tác hại — giải thích đơn giản:**

Khi user đọc bài "Quản lý vườn sầu riêng giai đoạn ra hoa", URL trên trình duyệt vẫn là `https://nongnghiepso.vn/?section=guides`. Vấn đề:
1. **User không thể chia sẻ link** bài cụ thể trên Facebook/Zalo
2. **Google không có URL để index** từng bài
3. **Không có backlink** từ websites khác

So sánh:
- ❌ Hiện tại: `nongnghiepso.vn/?section=guides` → tất cả 50 hướng dẫn cùng URL
- ✅ Cần có: `nongnghiepso.vn/huong-dan/quan-ly-vuon-sau-rieng-mua-ra-hoa` → 1 URL/bài

**Cách sửa:**

**Bước 1 — Cài React Router:**
```bash
cd frontend
npm install react-router-dom@7
```

**Bước 2 — Tạo `frontend/src/router.tsx`:**
```typescript
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { HomePage } from "./components/HomePage";
import { NewsPortal } from "./components/NewsPortal";
import { GuideLibrary } from "./components/GuideLibrary";
import { GuideDetailPage } from "./components/GuideDetailPage";  // mới
import { NewsDetailPage } from "./components/NewsDetailPage";    // mới
import { AnalyticsPage } from "./components/AnalyticsPage";       // mới (tách khỏi App.tsx)
import { ForecastMethodology } from "./components/ForecastMethodology";

export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/tin-tuc", element: <NewsPortal /> },
  { path: "/tin-tuc/:slug", element: <NewsDetailPage /> },        // ← URL riêng cho bài tin
  { path: "/huong-dan", element: <GuideLibrary /> },
  { path: "/huong-dan/:slug", element: <GuideDetailPage /> },     // ← URL riêng cho hướng dẫn
  { path: "/du-bao-gia/:crop", element: <AnalyticsPage /> },      // ← URL riêng cho từng cây
  { path: "/thuat-toan-du-bao", element: <ForecastMethodology /> },
]);
```

**Bước 3 — Tạo `frontend/src/components/GuideDetailPage.tsx`:**
```typescript
import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchGuides, type GuidePost } from "../lib/api";
// import meta tag helper (xem SEO-003)

export function GuideDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [guide, setGuide] = useState<GuidePost | null>(null);
  
  useEffect(() => {
    fetchGuides().then((all) => {
      setGuide(all.find((g) => g.slug === slug) ?? null);
    });
  }, [slug]);
  
  if (!guide) return <div>Đang tải...</div>;
  
  return (
    <article>
      <h1>{guide.title}</h1>
      <p>{guide.summary}</p>
      <div dangerouslySetInnerHTML={{ __html: guide.content }} />
    </article>
  );
}
```

**Bước 4 — Backend đã có slug (xem `backend/app/models.py:184` — `slug: Mapped[str]`). Cần thêm endpoint detail:**

```python
# backend/app/api/content.py — thêm endpoint mới
@router.get("/content/guides/{slug}", response_model=GuidePostOut)
@cached(prefix="guide-detail", ttl_seconds=3600)
def guide_detail(slug: str, db: Session = Depends(get_db)) -> GuidePost:
    guide = db.scalar(select(GuidePost).where(GuidePost.slug == slug))
    if not guide:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài hướng dẫn")
    return guide
```

**Quan trọng:** Sau khi có URL riêng, **Google sẽ index 50+ trang thay vì 1 trang**.

---

### [SEO-003] 🔴 Mọi Trang Dùng Chung Title / Meta Description

**File ảnh hưởng:**
- `frontend/index.html` (hardcoded title chung cho toàn site)
- Toàn bộ pages (`HomePage`, `NewsPortal`, `GuideLibrary`)

**Tác hại — giải thích đơn giản:**

Hiện tại bạn vào trang nào cũng thấy title:
```
Nông nghiệp số - Dự báo giá nông sản Việt Nam
```

Khi Google hiển thị kết quả tìm kiếm, mỗi trang phải có title riêng:
- ❌ Hiện tại: "Nông nghiệp số - Dự báo giá nông sản Việt Nam" (cho tất cả)
- ✅ Cần có: 
  - Trang dự báo cà phê: "Giá Cà Phê Hôm Nay & Dự Báo 30 Ngày | Nông Nghiệp Số"
  - Bài hướng dẫn: "Cách Chăm Sóc Sầu Riêng Mùa Ra Hoa | Quy Trình Kỹ Thuật"
  - Trang tin: "Tin Thị Trường Nông Sản Mới Nhất | Nông Nghiệp Số"

Title quyết định ~30% xếp hạng SEO. Title trùng lặp = Google coi là duplicate.

**Cách sửa — Cài thư viện cập nhật meta động:**

```bash
cd frontend
npm install react-helmet-async
```

**`frontend/src/main.tsx`:**
```typescript
import { HelmetProvider } from "react-helmet-async";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HelmetProvider>
      <ErrorBoundary>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ErrorBoundary>
    </HelmetProvider>
  </React.StrictMode>
);
```

**Tạo helper `frontend/src/components/SeoHead.tsx`:**
```typescript
import { Helmet } from "react-helmet-async";

type Props = {
  title: string;
  description: string;
  canonical?: string;
  image?: string;
  type?: "website" | "article";
  publishedAt?: string;
  schemaJsonLd?: object;
};

export function SeoHead({
  title,
  description,
  canonical,
  image = "https://nongnghiepso.vn/og-cover.jpg",
  type = "website",
  publishedAt,
  schemaJsonLd,
}: Props) {
  const fullTitle = `${title} | Nông Nghiệp Số`;
  const fullCanonical = canonical ? `https://nongnghiepso.vn${canonical}` : undefined;
  
  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description.slice(0, 160)} />
      {fullCanonical && <link rel="canonical" href={fullCanonical} />}
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description.slice(0, 160)} />
      <meta property="og:type" content={type} />
      {fullCanonical && <meta property="og:url" content={fullCanonical} />}
      <meta property="og:image" content={image} />
      {publishedAt && <meta property="article:published_time" content={publishedAt} />}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description.slice(0, 160)} />
      {schemaJsonLd && (
        <script type="application/ld+json">
          {JSON.stringify(schemaJsonLd)}
        </script>
      )}
    </Helmet>
  );
}
```

**Áp dụng vào từng page:**

```typescript
// HomePage.tsx — đầu component
<SeoHead
  title="Dự báo giá nông sản Việt Nam"
  description="Cập nhật giá sầu riêng, cà phê, hồ tiêu, lúa hàng ngày. Dự báo 30 ngày theo vùng trồng, cẩm nang kỹ thuật và tin thị trường."
  canonical="/"
/>

// GuideDetailPage.tsx
<SeoHead
  title={guide.title}
  description={guide.summary}
  canonical={`/huong-dan/${guide.slug}`}
  type="article"
  publishedAt={guide.published_at}
  schemaJsonLd={{
    "@context": "https://schema.org",
    "@type": "HowTo",  // xem SEO-008
    "name": guide.title,
    "description": guide.summary,
    "datePublished": guide.published_at,
  }}
/>

// AnalyticsPage.tsx (cho từng cây)
<SeoHead
  title={`Giá ${cropLabel} hôm nay & Dự báo 30 ngày`}
  description={`Cập nhật giá ${cropLabel} mới nhất theo vùng trồng. Dự báo 30 ngày, cảnh báo bán, top tăng giảm.`}
  canonical={`/du-bao-gia/${crop}`}
/>
```

---

### [SEO-004] 🔴 Ảnh Hero 2.5-3.3 MB — Trang Tải Cực Chậm Trên Mobile

**File ảnh hưởng:**
- `frontend/public/coffee-hero.png` — **2.5 MB** ❌
- `frontend/public/durian-hero.png` — **2.9 MB** ❌
- `frontend/public/guide-fruit.png` — **2.2 MB** ❌
- `frontend/public/guide-industrial.png` — **3.3 MB** ❌
- `frontend/public/guide-food-crop.png` — **2.3 MB** ❌
- `frontend/public/guide-other.png` — **2.8 MB** ❌
- **Tổng cộng:** ~16 MB ảnh — load hết = 5+ giây trên 4G

**Tác hại — giải thích đơn giản:**

Đối tượng của bạn là **nông dân nhỏ lẻ ở vùng nông thôn dùng điện thoại 4G**. Khi họ vào trang:
1. Tải 1 ảnh PNG 3 MB ≈ 8-15 giây trên 4G yếu
2. Google PageSpeed sẽ chấm điểm rất thấp (LCP > 4s)
3. Google ưu tiên xếp hạng **trang tải nhanh** trên mobile (Core Web Vitals)
4. User đợi quá 3 giây sẽ thoát → bounce rate cao → SEO tệ hơn

**Cách sửa — 3 bước:**

#### Bước 1 — Convert PNG → WebP (giảm 60-80% size)
```bash
# Cài cwebp (Windows: tải từ Google)
# Hoặc dùng online: squoosh.app (kéo thả ảnh)

cd frontend/public
cwebp -q 80 coffee-hero.png -o coffee-hero.webp        # 2.5 MB → ~250 KB
cwebp -q 80 durian-hero.png -o durian-hero.webp        # 2.9 MB → ~290 KB
cwebp -q 80 guide-fruit.png -o guide-fruit.webp        # 2.2 MB → ~220 KB
cwebp -q 80 guide-industrial.png -o guide-industrial.webp
cwebp -q 80 guide-food-crop.png -o guide-food-crop.webp
cwebp -q 80 guide-other.png -o guide-other.webp
```

#### Bước 2 — Resize ảnh xuống kích thước hợp lý
Hero card hiển thị cỡ 800×600 px là đủ. Không cần ảnh 4000×3000 px:
```bash
# Cài ImageMagick: choco install imagemagick (Windows)
magick coffee-hero.webp -resize 800x600^ -quality 80 coffee-hero.webp
magick durian-hero.webp -resize 800x600^ -quality 80 durian-hero.webp
# Tương tự cho ảnh khác
```

#### Bước 3 — Dùng `<picture>` để fallback PNG
Trong `GuideLibrary.tsx:435` thay:
```tsx
{image ? <img src={image} alt="" loading="lazy" /> : null}
```
bằng:
```tsx
{image ? (
  <picture>
    <source srcSet={image.replace(".png", ".webp")} type="image/webp" />
    <img 
      src={image} 
      alt={`Hình minh họa nhóm ${family}`}    // ← thêm alt
      loading="lazy"
      width="400" 
      height="300"
    />
  </picture>
) : null}
```

**Mong đợi sau fix:** Thời gian tải trang giảm từ 8-15 giây → 1-2 giây.

---

### [SEO-005] 🔴 Tất Cả Ảnh Có `alt=""` — Mất Cơ Hội Image SEO

**File ảnh hưởng:**
- `frontend/src/components/HomePage.tsx:276` — `<img src={lead.image_url} alt="" />`
- `frontend/src/components/NewsPortal.tsx:407, 417` — `alt=""`
- `frontend/src/components/GuideLibrary.tsx:301, 435` — `alt=""`

**Tác hại — giải thích đơn giản:**

`alt` là text mô tả ảnh cho Google + screen reader. Hiện tại tất cả `alt=""` (rỗng) nghĩa là:
1. Google **không hiểu** ảnh nội dung gì → mất index Google Images (nguồn traffic lớn cho từ khóa "ảnh sầu riêng", "vườn cà phê")
2. Người mù dùng screen reader **không nghe được** mô tả
3. Khi ảnh load fail (mạng yếu), user không biết ảnh chứa gì

**Cách sửa:**

```tsx
// HomePage.tsx:274 — ảnh tin tức
<img
  src={lead.image_url || "/coffee-hero-photo.jpg"}
  alt={lead.title}    // ← thay vì alt=""
  loading="lazy"
  width="800"
  height="450"
/>

// NewsPortal.tsx:405 — thumbnail tin
<img
  src={article.image_url ?? ""}
  alt={`Ảnh minh họa: ${article.title}`}   // ← mô tả rõ
  loading="lazy"
  width="200"
  height="120"
/>

// NewsPortal.tsx:417 — logo nguồn
<img
  src={logoUrl}
  alt={`Logo ${article.source_name}`}       // ← alt cho logo
  loading="lazy"
  width="64"
  height="64"
/>

// GuideLibrary.tsx:298-307 — ảnh trong bài hướng dẫn
<img
  src={guideImageUrl(url)}
  alt={`${guide.title} — ${block.heading}`}  // ← mô tả ngữ cảnh
  loading="lazy"
  width="600"
  height="400"
/>

// GuideLibrary.tsx:435 — ảnh family (cây ăn quả, công nghiệp...)
{image ? (
  <img 
    src={image} 
    alt={`Nhóm ${family}`}   // ← alt cụ thể
    loading="lazy"
    width="400"
    height="300"
  /> 
) : null}
```

**Quy tắc viết alt cho ảnh nông nghiệp:**
- ✅ "Vườn sầu riêng Ri6 đang ra hoa tại Tiền Giang"
- ✅ "Nông dân thu hoạch cà phê Robusta ở Đắk Lắk"
- ❌ "image123.jpg"
- ❌ "" (rỗng — chỉ dùng cho ảnh trang trí thuần túy)

---

### [SEO-006] 🔴 Sitemap Chỉ Có 8 URL — Bài Viết Không Được Index

**File ảnh hưởng:** `frontend/public/sitemap.xml`

**Tác hại — giải thích đơn giản:**

Sitemap = "danh sách trang" bạn submit cho Google biết. Hiện tại bạn nói với Google:
"Tôi có 8 trang." 

Nhưng thực tế bạn có 200+ bài tin tức và 50+ hướng dẫn kỹ thuật — Google **không biết** chúng tồn tại.

**Cách sửa — Tạo sitemap.xml động từ database:**

**Tạo backend endpoint mới `backend/app/api/content.py`:**
```python
from fastapi.responses import Response
from datetime import datetime, UTC

@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_db)) -> Response:
    site = "https://nongnghiepso.vn"
    
    # Static URLs
    urls = [
        (f"{site}/", "1.0", "daily"),
        (f"{site}/tin-tuc", "0.9", "hourly"),
        (f"{site}/huong-dan", "0.9", "weekly"),
        (f"{site}/du-bao-gia/sau_rieng", "0.9", "daily"),
        (f"{site}/du-bao-gia/ca_phe", "0.9", "daily"),
        (f"{site}/du-bao-gia/ho_tieu", "0.9", "daily"),
        (f"{site}/du-bao-gia/lua", "0.9", "daily"),
        (f"{site}/thuat-toan-du-bao", "0.6", "monthly"),
    ]
    
    # Guide detail URLs (50+ guides)
    guides = db.scalars(
        select(GuidePost.slug, GuidePost.published_at)
        .order_by(GuidePost.published_at.desc())
    ).all()
    for guide in guides:
        urls.append((f"{site}/huong-dan/{guide.slug}", "0.7", "monthly"))
    
    # News URLs (latest 500 articles)
    articles = db.scalars(
        select(NewsArticle)
        .order_by(NewsArticle.published_at.desc().nullslast())
        .limit(500)
    ).all()
    for article in articles:
        # Use slug derived from URL
        slug = article.source_url.rstrip("/").split("/")[-1].replace(".html", "")[:80]
        lastmod = (article.published_at or article.scraped_at).strftime("%Y-%m-%d")
        urls.append((f"{site}/tin-tuc/{slug}", "0.5", "weekly", lastmod))
    
    # Build XML
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url_data in urls:
        loc, priority, changefreq = url_data[:3]
        lastmod = url_data[3] if len(url_data) > 3 else datetime.now(UTC).strftime("%Y-%m-%d")
        xml_parts.append(
            f"  <url>"
            f"<loc>{loc}</loc>"
            f"<lastmod>{lastmod}</lastmod>"
            f"<changefreq>{changefreq}</changefreq>"
            f"<priority>{priority}</priority>"
            f"</url>"
        )
    xml_parts.append("</urlset>")
    
    return Response(content="\n".join(xml_parts), media_type="application/xml")
```

**Cập nhật `frontend/public/robots.txt`:**
```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /?utm_*

# Sitemap động từ backend
Sitemap: https://api.nongnghiepso.vn/api/v1/sitemap.xml

# Sitemap tĩnh (fallback)
Sitemap: https://nongnghiepso.vn/sitemap.xml
```

**Setup Cloudflare để bot tìm sitemap đúng URL:**
```
# frontend/public/_redirects
/sitemap.xml https://api.nongnghiepso.vn/api/v1/sitemap.xml 200
```

**Submit sitemap lên Google:**
1. Vào https://search.google.com/search-console
2. Add property `nongnghiepso.vn`
3. Submit sitemap: `https://nongnghiepso.vn/sitemap.xml`

---

### [SEO-007] 🔴 Bài Tin Tức Đều Mở Link Ngoài (`target="_blank"`) — Mất Traffic

**File ảnh hưởng:**
- `frontend/src/components/HomePage.tsx:294, 308` — `<a href={lead.source_url} target="_blank">`
- `frontend/src/components/NewsPortal.tsx:260, 320, 388` — tất cả link news mở external

**Tác hại — giải thích đơn giản:**

Hiện tại khi user click vào tin tức, browser mở **website gốc của báo** (như `nongnghiepmoitruong.vn`). Bạn:
1. Mất user (họ rời website của bạn)
2. Mất chance hiện quảng cáo
3. Google không thấy "engagement" trên website → tụt xếp hạng
4. Website không có **content unique** → Google đánh giá là "thin content" (nội dung mỏng)

**Cách sửa — Xây dựng landing page riêng cho từng tin (giữ user lại):**

**Bước 1 — Backend lưu thêm field `excerpt` đầy đủ hơn:**

Hiện tại `NewsArticle.summary` chỉ có 1-2 câu. Cần scrape thêm 200-500 từ excerpt và thêm "đọc thêm tại nguồn" ở cuối.

```python
# backend/app/services/content_portal.py — sửa _extract_listing
def _extract_listing(self, source: dict) -> Generator:
    # ... existing code ...
    # Sau khi có summary, fetch URL gốc để lấy first paragraph
    try:
        article_html = fetch_html(item["source_url"], timeout=10)
        soup = BeautifulSoup(article_html, "html.parser")
        # Lấy 3 paragraph đầu tiên
        paragraphs = soup.find_all("p")[:3]
        item["excerpt"] = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))[:1500]
    except Exception:
        pass
```

**Bước 2 — Tạo `NewsDetailPage.tsx`:**
```tsx
import { useParams } from "react-router-dom";
import { SeoHead } from "./SeoHead";

export function NewsDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [article, setArticle] = useState<NewsArticle | null>(null);
  
  useEffect(() => {
    fetch(`/api/v1/content/news/${slug}`)
      .then(r => r.json())
      .then(setArticle);
  }, [slug]);
  
  if (!article) return <div>Đang tải...</div>;
  
  return (
    <>
      <SeoHead
        title={article.title}
        description={article.summary}
        canonical={`/tin-tuc/${slug}`}
        type="article"
        publishedAt={article.published_at}
        image={article.image_url || undefined}
        schemaJsonLd={{
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "headline": article.title,
          "datePublished": article.published_at,
          "image": article.image_url,
          "publisher": {
            "@type": "Organization",
            "name": "Nông Nghiệp Số"
          }
        }}
      />
      <article className="news-detail">
        <h1>{article.title}</h1>
        <div className="news-meta">
          <span>{article.source_name}</span>
          <time>{formatDate(article.published_at)}</time>
        </div>
        {article.image_url && (
          <img src={article.image_url} alt={article.title} loading="lazy" />
        )}
        <div className="news-summary">
          <p>{article.summary}</p>
        </div>
        <div className="news-excerpt">
          {article.excerpt?.split("\n\n").map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
        <div className="news-source-link">
          <p>Bài viết tổng hợp từ <strong>{article.source_name}</strong>.</p>
          <a href={article.source_url} target="_blank" rel="noreferrer nofollow">
            Đọc bài viết đầy đủ tại {article.source_name}
          </a>
        </div>
        
        {/* Related: link sang dự báo giá liên quan (xem SEO-014) */}
        <RelatedForecastWidget category={article.category} />
      </article>
    </>
  );
}
```

**Quan trọng:** Thêm `rel="nofollow"` vào link external để Google không "chuyển" SEO rank cho báo gốc.

---

## 4. HIGH PRIORITY — Nên sửa sớm 🟠

---

### [SEO-008] 🟠 Thiếu Schema HowTo Cho Hướng Dẫn Kỹ Thuật

**File ảnh hưởng:** `frontend/src/components/GuideLibrary.tsx`, `frontend/src/components/GuideDetailPage.tsx` (tạo mới)

**Tác hại:**

Bài hướng dẫn kỹ thuật là tài sản SEO quý nhất. Google có **rich snippet đặc biệt cho HowTo** — hiển thị các bước trong kết quả tìm kiếm:
```
🔍 "cách chăm sóc sầu riêng mùa ra hoa"

📋 Cách chăm sóc sầu riêng mùa ra hoa - Nông Nghiệp Số
   ⭐⭐⭐⭐⭐ 4.8 (240 đánh giá) - 15 phút - Trung bình
   1. Tưới nước đúng nhịp
   2. Bón phân kích hoa
   3. Tỉa nụ chọn lọc
```

Có HowTo schema → CTR (click rate) tăng 30-50% so với kết quả thường.

**Cách sửa:**

Trong `GuideDetailPage.tsx` parse content thành steps:
```typescript
function buildHowToSchema(guide: GuidePost) {
  // Parse content theo block headings (đã có logic trong GuideLibrary.tsx:266)
  const lines = guide.content.split(/\n+/).map(l => l.trim()).filter(Boolean);
  const steps: { name: string; text: string }[] = [];
  let current: { name: string; text: string } | null = null;
  
  for (const line of lines) {
    if (["Mục tiêu", "Khi nào áp dụng", "Cách làm tại vườn", 
         "Theo dõi sau khi làm", "Lỗi cần tránh"].includes(line)) {
      if (current) steps.push(current);
      current = { name: line, text: "" };
    } else if (current && !line.startsWith("IMAGE::")) {
      current.text += (current.text ? "\n" : "") + line;
    }
  }
  if (current) steps.push(current);
  
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    "name": guide.title,
    "description": guide.summary,
    "image": "https://nongnghiepso.vn/og-cover.jpg",
    "totalTime": `PT${estimateReadingMinutes(guide.content)}M`,
    "step": steps.map((s, i) => ({
      "@type": "HowToStep",
      "position": i + 1,
      "name": s.name,
      "text": s.text.slice(0, 500),
    })),
  };
}

// Trong component:
<SeoHead
  title={guide.title}
  description={guide.summary}
  canonical={`/huong-dan/${guide.slug}`}
  type="article"
  schemaJsonLd={buildHowToSchema(guide)}
/>
```

---

### [SEO-009] 🟠 Trang Dự Báo Giá Thiếu Schema Product / PriceSpecification

**File ảnh hưởng:** `frontend/src/components/AnalyticsPage.tsx` (cần tách từ App.tsx)

**Tác hại:**

Trang dự báo giá là content "vàng" cho SEO Việt Nam. Mọi nông dân đều search "giá sầu riêng hôm nay", "giá cà phê hôm nay". Google có rich snippet riêng cho **Product** với giá:

```
🔍 "giá sầu riêng hôm nay"

📦 Sầu riêng Ri6 Tiền Giang | Giá hôm nay
   86.000 ₫ - 92.000 ₫/kg
   ⏰ Cập nhật: 1 giờ trước
   📍 Tiền Giang
```

**Cách sửa — thêm vào AnalyticsPage:**

```typescript
function buildPriceSchema(crop: string, region: string, variety: string, latestPrice: number, minPrice: number, maxPrice: number) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": `${variety} ${region}`,
    "description": `Giá ${variety} tại ${region} cập nhật hàng ngày kèm dự báo 30 ngày.`,
    "category": `Nông sản / ${crop}`,
    "offers": {
      "@type": "AggregateOffer",
      "priceCurrency": "VND",
      "lowPrice": minPrice,
      "highPrice": maxPrice,
      "offerCount": 1,
      "priceSpecification": {
        "@type": "UnitPriceSpecification",
        "price": latestPrice,
        "priceCurrency": "VND",
        "unitText": "kg",
        "validFrom": new Date().toISOString(),
      }
    }
  };
}

// Trong AnalyticsPage component:
<SeoHead
  title={`Giá ${cropLabel} ${selectedRegion?.province ?? ""} hôm nay`}
  description={`Cập nhật giá ${cropLabel} mới nhất ${latestPrice.toLocaleString("vi-VN")} VND/kg. Dự báo 30 ngày, tín hiệu bán, top tăng giảm theo vùng trồng.`}
  canonical={`/du-bao-gia/${crop}`}
  schemaJsonLd={buildPriceSchema(crop, selectedRegion?.province ?? "", selectedVariety?.name ?? "", latestPrice, minPrice, maxPrice)}
/>
```

---

### [SEO-010] 🟠 Open Graph Image `/og-cover.jpg` Không Tồn Tại

**File ảnh hưởng:** 
- `frontend/index.html:24` (reference `og-cover.jpg`)
- `frontend/public/` — KHÔNG có `og-cover.jpg`

**Tác hại:**

Khi user share link Nông Nghiệp Số trên Facebook/Zalo, Facebook tìm `og-cover.jpg` → **không tìm thấy** → hiển thị link không có thumbnail → CTR giảm 60-70%.

**Cách sửa:**

1. Tạo ảnh `og-cover.jpg` kích thước **1200×630 px** (Facebook chuẩn)
2. Nội dung: Logo + tên website + tagline "Dự báo giá nông sản Việt Nam"
3. File size < 300 KB
4. Lưu vào `frontend/public/og-cover.jpg`

**Tool tạo ảnh nhanh (free):**
- https://www.canva.com (có template "Facebook Post" 1200×630)
- https://www.figma.com

**Test sau khi tạo:**
- https://developers.facebook.com/tools/debug/ — paste URL website → Facebook sẽ refresh cache OG

---

### [SEO-011] 🟠 Heading Hierarchy Các Trang Quá Generic

**File ảnh hưởng:**
- `frontend/src/components/GuideLibrary.tsx:97` — `<h1>Quy trình kỹ thuật</h1>` — quá chung
- `frontend/src/App.tsx:525` — `<h1>Dự báo giá {cropLabel}</h1>` — OK nhưng có thể tốt hơn

**Tác hại:**

H1 = từ khóa quan trọng nhất của trang. "Quy trình kỹ thuật" không có cây trồng cụ thể → không match từ khóa user search.

**So sánh:**
- ❌ Hiện tại: `<h1>Quy trình kỹ thuật</h1>`
- ✅ Tốt hơn: `<h1>Quy Trình Kỹ Thuật Trồng Sầu Riêng, Cà Phê, Hồ Tiêu, Lúa</h1>`

**Cách sửa:**

```tsx
// GuideLibrary.tsx:97
<h1>Quy Trình Kỹ Thuật Trồng Trọt Cho Cây {currentFamily}</h1>
// Hoặc dynamic theo plant đang chọn:
<h1>Hướng Dẫn Kỹ Thuật {currentPlant} - {currentFamily}</h1>

// App.tsx:525 — analytics
<h1>Giá {cropLabel} hôm nay & Dự báo 30 ngày {selectedRegion?.province ? `tại ${selectedRegion.province}` : ""}</h1>

// NewsPortal.tsx:183
<h1>Tin Tức Thị Trường Nông Sản, Phân Bón, Chính Sách Nông Nghiệp Mới Nhất</h1>

// HomePage.tsx:201
<h1>Nông Nghiệp Số - Dự Báo Giá Nông Sản & Hướng Dẫn Kỹ Thuật Việt Nam</h1>
```

**Quy tắc:** H1 nên 40-70 ký tự, chứa 2-3 từ khóa chính, có đề cập cây trồng cụ thể.

---

### [SEO-012] 🟠 JS Bundle Quá Lớn (Recharts 378 KB)

**File ảnh hưởng:** `frontend/dist/assets/recharts-CYW2fh69.js` (378 KB)

**Tác hại:**

Recharts là thư viện vẽ biểu đồ. **378 KB** trên 4G nông thôn = thêm 1-2 giây load. Mobile users sẽ rời đi.

**Cách sửa — Lazy load Recharts:**

Recharts đã được bundle riêng (đã làm). Nhưng MasterChart có lazy import. Đảm bảo Recharts **chỉ load khi user xem trang Analytics**, không load khi vào HomePage:

```typescript
// App.tsx — đã có:
const MasterChart = lazy(() => import("./components/MasterChart")...);

// Vấn đề: HomePage có Sparkline tự vẽ SVG (không dùng Recharts) — TỐT
// Nhưng cần verify: vào HomePage có request `recharts-*.js` không?

// Test bằng:
// 1. npm run build && npm run preview
// 2. Mở DevTools > Network > vào HomePage
// 3. Check `recharts-*.js` có trong list không
// Nếu CÓ → cần debug import chain để loại
```

**Optimization khác — dùng Lightweight chart cho HomePage:**

Sparkline hiện tại trong HomePage.tsx tự vẽ SVG (tốt!). Giữ nguyên.

Cho `MasterChart`, có thể thay Recharts bằng `chart.js` (130 KB) hoặc `apexcharts` (200 KB) — nhưng work overhead lớn. Để sau.

---

### [SEO-013] 🟠 Pre-render Script Có Nhưng Chưa Chạy

**File ảnh hưởng:** `scripts/prerender_seo.py` (script tồn tại) + `frontend/dist/seo/` (folder không có)

**Tác hại:**

Bạn đã có script tạo HTML tĩnh cho từng bài tin/hướng dẫn — đây là cách rẻ + nhanh nhất để Google index nội dung. Nhưng script **chưa được chạy** trong build pipeline.

**Cách sửa:**

**Bước 1 — Cập nhật `frontend/package.json`:**
```json
{
  "scripts": {
    "build": "tsc && vite build",
    "build:full": "npm run build && python ../scripts/prerender_seo.py",
    "preview": "vite preview --host 127.0.0.1"
  }
}
```

**Bước 2 — Sửa script để xử lý slug an toàn (xem AUDIT_REPORT_V2.md NEW-014):**
```python
import re

def _slug_from_url(url: str) -> str:
    tail = url.rstrip("/").split("/")[-1] or "article"
    tail = tail.split("?")[0].replace(".html", "").replace(".htm", "")
    tail = re.sub(r"[^a-zA-Z0-9\-_]", "-", tail)
    tail = re.sub(r"-+", "-", tail).strip("-")
    return tail[:120] or "article"
```

**Bước 3 — Cập nhật `frontend/public/_redirects` để serve HTML tĩnh:**
```
# Khi user/bot vào /tin-tuc/<slug>, nếu có HTML tĩnh thì serve, không thì SPA
/tin-tuc/:slug   /seo/news/:slug.html  200
/huong-dan/:slug /seo/guides/:slug.html  200
/*  /index.html  200
```

**Bước 4 — Setup CI/CD chạy lại sau mỗi 6h** (vì có tin mới):
- Nếu deploy bằng GitHub Actions: thêm cron job
- Nếu Cloudflare Pages: webhook trigger từ backend sau scrape

---

### [SEO-014] 🟠 Thiếu Internal Linking Giữa Các Trang

**File ảnh hưởng:** Tất cả components

**Tác hại:**

Google đọc internal link để hiểu cấu trúc website + chuyển "SEO juice" giữa các trang. Hiện tại:
- Bài tin "Cà phê tăng giá" → KHÔNG link sang trang dự báo cà phê
- Hướng dẫn "Chăm sóc sầu riêng" → KHÔNG link sang giá sầu riêng

**Cách sửa — Tạo widget liên quan:**

```typescript
// frontend/src/components/RelatedForecastWidget.tsx
import { Link } from "react-router-dom";

const TOPIC_TO_CROP: Record<string, string> = {
  "Cà phê": "ca_phe",
  "Sầu riêng": "sau_rieng",
  "Hồ tiêu": "ho_tieu",
  "Lúa": "lua",
};

export function RelatedForecastWidget({ category }: { category: string }) {
  const crop = TOPIC_TO_CROP[category];
  if (!crop) return null;
  const cropLabel = category.toLowerCase();
  
  return (
    <aside className="related-forecast">
      <h3>Xem thêm</h3>
      <ul>
        <li>
          <Link to={`/du-bao-gia/${crop}`}>
            📊 Giá {cropLabel} hôm nay & dự báo 30 ngày
          </Link>
        </li>
        <li>
          <Link to={`/huong-dan?cay=${crop}`}>
            📚 Hướng dẫn kỹ thuật trồng {cropLabel}
          </Link>
        </li>
        <li>
          <Link to={`/tin-tuc?topic=${encodeURIComponent(category)}`}>
            📰 Tin tức {cropLabel} mới nhất
          </Link>
        </li>
      </ul>
    </aside>
  );
}
```

Áp dụng vào NewsDetailPage, GuideDetailPage, AnalyticsPage.

---

## 5. MEDIUM PRIORITY — Sửa khi có thời gian 🟡

---

### [SEO-015] 🟡 Search Box Trên HomePage Không Hoạt Động

**File ảnh hưởng:** `frontend/src/components/HomePage.tsx:204-208`

**Tác hại:**

Có search box nhưng input không submit form, không trigger search. Google `SearchAction` schema trong index.html (`/?q={search_term_string}`) "lừa" Google rằng có search → khi bot test sẽ fail.

**Cách sửa:**

```tsx
// HomePage.tsx
const [searchQuery, setSearchQuery] = useState("");

function handleSearch(event: React.FormEvent) {
  event.preventDefault();
  if (searchQuery.trim()) {
    // Navigate to news with search query
    window.location.href = `/tin-tuc?q=${encodeURIComponent(searchQuery.trim())}`;
  }
}

<form onSubmit={handleSearch} role="search" className="home-quick-search">
  <Search size={19} />
  <input 
    name="q"
    aria-label="Tìm nhanh cây trồng hoặc tin thị trường" 
    placeholder="Tìm nhanh: cà phê, sầu riêng, phân bón..." 
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
  />
  <button type="submit">Tìm</button>
</form>
```

---

### [SEO-016] 🟡 Không Có Custom 404 Page

**File ảnh hưởng:** `frontend/public/_redirects` (chưa có), không có 404 component

**Tác hại:**

Khi user gõ sai URL hoặc bài viết bị xóa → trang trắng hoặc lỗi. Google đọc page có 200 status mà không có nội dung → tệ cho SEO.

**Cách sửa:**

**Tạo `frontend/src/components/NotFoundPage.tsx`:**
```tsx
import { Link } from "react-router-dom";
import { SeoHead } from "./SeoHead";

export function NotFoundPage() {
  return (
    <>
      <SeoHead 
        title="Không tìm thấy trang"
        description="Trang bạn tìm không tồn tại. Quay về trang chủ Nông Nghiệp Số."
        canonical="/404"
      />
      <main className="not-found-page">
        <h1>404 - Không tìm thấy trang</h1>
        <p>Trang bạn đang tìm không tồn tại hoặc đã bị di chuyển.</p>
        <nav>
          <Link to="/">Về trang chủ</Link>
          <Link to="/tin-tuc">Đọc tin nông nghiệp</Link>
          <Link to="/huong-dan">Xem hướng dẫn kỹ thuật</Link>
          <Link to="/du-bao-gia/sau_rieng">Dự báo giá nông sản</Link>
        </nav>
      </main>
    </>
  );
}
```

**Cập nhật router:**
```typescript
{ path: "*", element: <NotFoundPage /> }
```

---

### [SEO-017] 🟡 Canonical URL Chỉ Có 1 Cho Toàn Site

**File ảnh hưởng:** `frontend/index.html:16` — `canonical href="https://nongnghiepso.vn/"`

**Tác hại:**

Mọi page đều có canonical về `/` → Google nghĩ tất cả pages là duplicate của trang chủ → chỉ index trang chủ.

**Cách sửa:** Đã được giải quyết bởi SEO-003 (dùng `react-helmet-async` cập nhật canonical động cho từng page).

---

### [SEO-018] 🟡 Không Có Schema FAQPage Cho Trang Dự Báo

**File ảnh hưởng:** `frontend/src/components/ForecastMethodology.tsx`

**Tác hại:**

Trang "Cách hệ thống dự báo giá nông sản" có cấu trúc câu hỏi + trả lời (8 sections) — perfect cho FAQ schema. Google sẽ hiển thị accordion FAQ trong search results → CTR tăng.

**Cách sửa:**

Thêm vào `ForecastMethodology.tsx`:
```tsx
const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Bài toán dự báo giá nông sản được định nghĩa như thế nào?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Hệ thống không dự báo một giá chung, mà tách bài toán theo từng tổ hợp cây trồng, vùng, giống. Cùng là sầu riêng Ri6, giá ở Đắk Lắk khác Tiền Giang."
      }
    },
    {
      "@type": "Question",
      "name": "Hệ thống dùng dữ liệu nào để dự báo?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Cửa sổ 60 ngày gần nhất gồm: giá VND/kg, nhiệt độ, lượng mưa, độ chín và khối lượng giao dịch."
      }
    },
    // ... thêm 6 câu nữa từ 8 sections
  ]
};

<SeoHead
  title="Cách hệ thống dự báo giá nông sản"
  description="Giải thích chi tiết thuật toán dự báo giá: dữ liệu đầu vào, mô hình LSTM, khoảng tin cậy."
  canonical="/thuat-toan-du-bao"
  schemaJsonLd={faqSchema}
/>
```

---

### [SEO-019] 🟡 Không Có Breadcrumb Navigation

**File ảnh hưởng:** Tất cả pages

**Tác hại:**

Breadcrumb (đường dẫn) giúp:
1. User biết mình đang ở đâu trong website
2. Google hiển thị breadcrumb trong search result thay vì URL dài

```
🔍 Cách chăm sóc sầu riêng mùa ra hoa
   nongnghiepso.vn › Hướng dẫn › Cây ăn quả › Sầu riêng
```

**Cách sửa:**

```tsx
// frontend/src/components/Breadcrumb.tsx
import { Link } from "react-router-dom";

type Item = { label: string; to?: string };

export function Breadcrumb({ items }: { items: Item[] }) {
  return (
    <>
      <nav aria-label="Breadcrumb" className="breadcrumb">
        <ol>
          {items.map((item, i) => (
            <li key={i}>
              {item.to ? <Link to={item.to}>{item.label}</Link> : <span>{item.label}</span>}
              {i < items.length - 1 && <span aria-hidden> › </span>}
            </li>
          ))}
        </ol>
      </nav>
      <script type="application/ld+json">
        {JSON.stringify({
          "@context": "https://schema.org",
          "@type": "BreadcrumbList",
          "itemListElement": items.map((item, i) => ({
            "@type": "ListItem",
            "position": i + 1,
            "name": item.label,
            "item": item.to ? `https://nongnghiepso.vn${item.to}` : undefined
          }))
        })}
      </script>
    </>
  );
}

// Sử dụng trong GuideDetailPage:
<Breadcrumb items={[
  { label: "Trang chủ", to: "/" },
  { label: "Hướng dẫn", to: "/huong-dan" },
  { label: guide.family, to: `/huong-dan?family=${guide.family}` },
  { label: guide.title }
]} />
```

---

### [SEO-020] 🟡 Newsletter Form Thiếu Thuộc Tính HTML Chuẩn

**File ảnh hưởng:** `frontend/src/components/SiteFooter.tsx:64-68`

**Tác hại:**

Input thiếu `name="email"` chuẩn → trình duyệt không gợi ý autofill → tỷ lệ subscribe thấp hơn.

**Cách sửa:**

```tsx
<input
  id="footer-email"
  name="email"                  // ← thêm
  type="email"
  autoComplete="email"          // ← thêm
  required                      // ← thêm
  inputMode="email"             // ← tốt cho mobile keyboard
  value={email}
  onChange={...}
  placeholder="email@example.com"
  aria-invalid={status === "error"}
  aria-describedby={message ? "footer-email-feedback" : undefined}
/>
```

---

### [SEO-021] 🟡 Thiếu `lang` Attribute Trong Content Động

**File ảnh hưởng:** Tất cả pages

**Tác hại:** `<html lang="vi">` đã có (tốt) nhưng nếu có content tiếng Anh (ví dụ tên giống "Black Thorn", "Robusta") nên dùng `<span lang="en">` để Google biết language switching.

**Cách sửa:** Optional, không quan trọng cho SEO Việt Nam.

---

## 6. LOW PRIORITY — Tùy chọn 🟢

---

### [SEO-022] 🟢 Thêm Hreflang Nếu Có Plan Đa Ngôn Ngữ

Bỏ qua nếu chỉ làm tiếng Việt.

---

### [SEO-023] 🟢 Cập Nhật `robots.txt` Chi Tiết Hơn

```
User-agent: *
Allow: /

# Chặn API endpoints khỏi crawl
Disallow: /api/
Disallow: /*?utm_*
Disallow: /*?fbclid=*

# Cho phép Google Image bot
User-agent: Googlebot-Image
Allow: /

# Sitemap
Sitemap: https://nongnghiepso.vn/sitemap.xml

# Crawl delay (tránh tải nặng server)
Crawl-delay: 1
```

---

### [SEO-024] 🟢 Cấu Hình Cache Headers

**File ảnh hưởng:** `deploy/Caddyfile`, Cloudflare Pages settings

Hiện tại Caddy chỉ proxy API, không serve frontend. Nếu deploy lên Cloudflare Pages, default headers OK.

Nếu self-host frontend bằng Caddy, thêm:
```
{$FRONTEND_DOMAIN} {
    root * /var/www/frontend
    file_server
    
    # Cache static assets 1 year
    @assets {
        path /assets/*
    }
    header @assets Cache-Control "public, max-age=31536000, immutable"
    
    # Cache HTML 5 minutes (vẫn cần update khi có bài mới)
    @html {
        path *.html
    }
    header @html Cache-Control "public, max-age=300, must-revalidate"
    
    # Cache images 7 days
    @images {
        path *.jpg *.png *.webp *.svg
    }
    header @images Cache-Control "public, max-age=604800"
}
```

---

### [SEO-025] 🟢 Thêm RSS Feed

Nông dân + chuyên gia thích đọc RSS. Cũng giúp Google News index nhanh hơn.

```python
# backend/app/api/content.py
@router.get("/rss/news.xml", include_in_schema=False)
def news_rss(db: Session = Depends(get_db)) -> Response:
    articles = db.scalars(
        select(NewsArticle)
        .order_by(NewsArticle.published_at.desc().nullslast())
        .limit(50)
    ).all()
    
    items = []
    for a in articles:
        items.append(f"""
        <item>
          <title><![CDATA[{a.title}]]></title>
          <link>https://nongnghiepso.vn/tin-tuc/{slug_from_url(a.source_url)}</link>
          <description><![CDATA[{a.summary}]]></description>
          <pubDate>{a.published_at.strftime('%a, %d %b %Y %H:%M:%S +0000') if a.published_at else ''}</pubDate>
          <category>{a.category}</category>
        </item>
        """)
    
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Nông Nghiệp Số - Tin nông nghiệp</title>
        <link>https://nongnghiepso.vn</link>
        <description>Tin tức thị trường nông sản Việt Nam</description>
        <language>vi</language>
        {"".join(items)}
      </channel>
    </rss>"""
    return Response(content=rss, media_type="application/rss+xml")
```

Add link in index.html:
```html
<link rel="alternate" type="application/rss+xml" title="Nông Nghiệp Số RSS" href="/rss/news.xml" />
```

---

### [SEO-026] 🟢 Thêm Tags / Categories System

Hiện tại có category nhưng chưa có URL riêng cho từng category. Tạo:
- `/tin-tuc/category/ca-phe` — tin cà phê
- `/huong-dan/family/cay-an-qua` — hướng dẫn cây ăn quả

Giúp tăng số trang Google index.

---

### [SEO-027] 🟢 Tracking Google Search Console + Analytics

Sau khi setup xong các fix trên:

1. **Google Search Console:**
   - Add property `nongnghiepso.vn`
   - Verify ownership (tag DNS hoặc HTML file)
   - Submit sitemap
   - Theo dõi: impressions, clicks, position từng query

2. **Google Analytics 4:**
   - Tạo property mới
   - Add tracking code vào `index.html`:
   ```html
   <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'G-XXXXXXXXXX');
   </script>
   ```

3. **Google AdSense:**
   - Apply sau khi có 1000 page views/ngày
   - Yêu cầu: nội dung gốc, không vi phạm policy

---

## 7. Đề xuất ưu tiên

- [ ] **SEO-004** Convert PNG hero → WebP, resize
- [ ] **SEO-005** Thêm alt text cho tất cả `<img>`
- [ ] **SEO-010** Tạo og-cover.jpg 1200×630 
- [ ] **SEO-013** Setup pre-render script chạy trong build
- [ ] **SEO-006** Tạo sitemap.xml động từ DB
- [ ] **SEO-002** Cài React Router + tạo NewsDetailPage, GuideDetailPage
- [ ] **SEO-003** Cài react-helmet-async + SeoHead component
- [ ] **SEO-011** Cải thiện H1 các trang
- [ ] Backend: thêm endpoint `/api/v1/content/news/{slug}`, `/guides/{slug}`
- [ ] **SEO-007** Tạo NewsDetailPage với content excerpt + related (1 ngày)
- [ ] **SEO-008** HowTo schema cho guides
- [ ] **SEO-009** Product/PriceSpecification schema cho dự báo
- [ ] **SEO-018** FAQPage schema cho ForecastMethodology
- [ ] **SEO-019** Breadcrumb component + schema
- [ ] **SEO-001** Phương án B.
- [ ] Setup Cloudflare Pages `_redirects` để serve HTML tĩnh cho bot (4 giờ)
- [ ] Test với https://search.google.com/test/rich-results
- [ ] Submit sitemap lên Google Search Console
- [ ] **SEO-014** RelatedForecastWidget + integrate
- [ ] **SEO-015** Search box hoạt động 
- [ ] **SEO-016** Custom 404 page
- [ ] **SEO-020** Form newsletter chuẩn
- [ ] **SEO-012** Test bundle, lazy load Recharts đúng cách
- [ ] **SEO-024** Cache headers cấu hình
- [ ] Test với https://pagespeed.web.dev
- [ ] Tối ưu CSS (114 KB → mục tiêu <80 KB)
- [ ] Lazy load font
- [ ] **SEO-027** Setup Google Search Console + Analytics 
- [ ] **SEO-026** Category/tag system
- [ ] **SEO-025** RSS feed
- [ ] Viết 10-20 bài hướng dẫn mới với từ khóa target (ongoing)


---

## 📊 Mong đợi sau khi fix

| Metric | Hiện tại | Sau Tuần 4 | Sau Tuần 8 |
|---|---|---|---|
| Số URL Google index | 1 | ~80 | ~300+ |
| PageSpeed Mobile score | 30-40 | 60-70 | 85+ |
| Time to First Contentful Paint | 4-8s | 1.5-2s | <1s |
| Organic traffic (impressions/tháng) | 0-50 | 500-2000 | 10,000+ |
| Tỷ lệ rich snippet hiển thị | 0% | 20% | 60%+ |


---

## 🎯 Format prompt khi giao việc cho AI agent

```
Đọc file SEO_AUDIT_REPORT.md ở thư mục gốc.

Implement [SEO-001] đến [SEO-027] theo đúng chỉ dẫn trong file.

Sau khi fix xong:
1. Run `cd frontend && npm run build` để verify build pass
2. Run `cd backend && pytest tests/` để verify backend tests pass  


Báo cáo kết quả từng SEO-NNN sau khi xong.
```

---

## 📚 Tài liệu tham khảo (free, tiếng Việt + Anh)

- **Google Search Central** (chính thức): https://developers.google.com/search/docs?hl=vi
- **Schema.org examples**: https://schema.org/HowTo, https://schema.org/Product
- **Test rich snippet**: https://search.google.com/test/rich-results
- **Test PageSpeed**: https://pagespeed.web.dev/
- **Test Open Graph**: https://developers.facebook.com/tools/debug/
- **Squoosh** (compress ảnh): https://squoosh.app
- **Sitemap validator**: https://www.xml-sitemaps.com/validate-xml-sitemap.html

---


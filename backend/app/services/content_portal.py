from __future__ import annotations

import re
import threading
import unicodedata
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import invalidate_cache
from app.core.config import get_settings
from app.models import GuidePost, NewsArticle


HAINONG_TECHNICAL_API = "https://panel.hainong.vn/api/v2/technical_processes"
HAINONG_GUIDE_SOURCE = "https://hainong.vn/quy-trinh-ky-thuat"
HAINONG_GUIDE_SECTIONS = {"Cẩm nang", "Chăm sóc"}
HAINONG_EXCLUDED_TERMS = {"bón phân", "bon phan", "phân bón", "phan bon"}
HAINONG_EXCLUDED_IMAGE_TERMS = {
    "bon-phan",
    "phan-bon",
    "phanbon",
    "fertilizer",
    "npk",
    "infographic",
    "screenshot",
    "screen-shot",
    "chup-man-hinh",
    "imgpsh",
    "logo",
}

GUIDE_TARGET_MIN_WORDS = 700
GUIDE_DEPTH_MARKER = "Ngưỡng kiểm tra nhanh"

NEWS_SOURCES = [
    {
        "name": "Báo Nông nghiệp và Môi trường",
        "url": "https://nongnghiepmoitruong.vn/kinh-te-thi-truong/",
        "pages": 3,
        "max_items": 80,
        "category": "Giá và thị trường",
    },
    {
        "name": "Bộ Nông nghiệp và Môi trường",
        "url": "https://mae.gov.vn/chuyen-muc/tin-tong-hop-300.htm",
        "pages": 1,
        "max_items": 36,
        "category": "Chính sách ngành",
    },
    {
        "name": "Báo Nông nghiệp và Môi trường",
        "url": "https://nongnghiepmoitruong.vn/kinh-te/",
        "pages": 2,
        "max_items": 60,
        "category": "Giá và thị trường",
    },
    {
        "name": "Nông sản Việt",
        "url": "https://nongsanviet.nongnghiepmoitruong.vn/thi-truong/",
        "pages": 3,
        "max_items": 80,
        "category": "Giá nông sản",
    },
    {
        "name": "Vinanet",
        "url": "https://vinanet.vn/nong-san/",
        "pages": 1,
        "max_items": 80,
        "category": "Giá nông sản",
    },
    {
        "name": "Vinanet",
        "url": "https://vinanet.vn/hang-hoa/",
        "pages": 1,
        "max_items": 80,
        "category": "Giá hàng hóa",
    },
    {
        "name": "Báo Công Thương",
        "url": "https://congthuong.vn/nong-san",
        "pages": 1,
        "max_items": 80,
        "category": "Giá nông sản",
    },
    {
        "name": "Báo Công Thương",
        "url": "https://congthuong.vn/tag/phan-bon-1148.tag",
        "pages": 1,
        "max_items": 120,
        "category": "Phân bón - vật tư",
    },
    {
        "name": "Báo Công Thương",
        "url": "https://congthuong.vn/search_enginer.html?p=search&q=ph%C3%A2n%20b%C3%B3n",
        "pages": 1,
        "max_items": 100,
        "category": "Phân bón - vật tư",
    },
]

NEWS_CANDIDATE_MULTIPLIER = 8
NEWS_MIN_CANDIDATES = 240
NEWS_MAX_ITEMS_PER_SOURCE = 120
NEWS_HTTP_TIMEOUT_SECONDS = 6
NEWS_DETAIL_LOOKUP_LIMIT = 6

CURATED_GUIDE_SLUGS = {
    "quan-ly-vuon-sau-rieng-mua-ra-hoa",
    "quan-ly-ca-phe-mua-kho",
    "nhat-ky-nong-nghiep-so",
}

_news_seed_lock = threading.Lock()
_guide_seed_lock = threading.Lock()


class ContentPortalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def latest_news(self, limit: int = 24, category: str | None = None) -> list[NewsArticle]:
        stmt = select(NewsArticle).order_by(desc(NewsArticle.published_at), desc(NewsArticle.scraped_at))
        if category:
            stmt = stmt.where(NewsArticle.category == category)
        rows = self.db.scalars(stmt.limit(max(limit * NEWS_CANDIDATE_MULTIPLIER, NEWS_MIN_CANDIDATES))).all()
        combined = sorted([row for row in rows if _is_keepable_news_article(row)], key=_news_time_key, reverse=True)
        if combined:
            return combined[:limit]

        if not self.db.scalar(select(NewsArticle.article_id).limit(1)):
            with _news_seed_lock:
                if not self.db.scalar(select(NewsArticle.article_id).limit(1)):
                    self.seed_fallback_news()
        rows = self.db.scalars(stmt.limit(max(limit * NEWS_CANDIDATE_MULTIPLIER, NEWS_MIN_CANDIDATES))).all()
        return sorted([row for row in rows if _is_keepable_news_article(row)], key=_news_time_key, reverse=True)[:limit]

    def _normalize_news_records(self) -> None:
        rows = self.db.scalars(select(NewsArticle).limit(600)).all()
        changed = False
        for row in rows:
            next_title = _compact_news_title(row.title)
            next_summary = _summary_without_title(row.summary or row.excerpt or row.title, next_title)
            next_excerpt = _truncate_words(next_summary or next_title, 180)
            next_source_name = _normalize_news_source_name(row.source_name, row.source_url)
            next_published_at = row.published_at or _parse_date(f"{next_title} {next_summary} {next_excerpt}")
            if row.title != next_title:
                row.title = next_title
                changed = True
            if row.summary != next_summary:
                row.summary = next_summary
                changed = True
            if row.excerpt != next_excerpt:
                row.excerpt = next_excerpt
                changed = True
            if row.source_name != next_source_name:
                row.source_name = next_source_name
                changed = True
            if next_published_at is not None and not _same_datetime(row.published_at, next_published_at):
                row.published_at = next_published_at
                changed = True
        if changed:
            self.db.commit()

    def scrape_news(self) -> dict:
        inserted = 0
        updated = 0
        unchanged = 0
        errors = []
        seen_urls: set[str] = set()
        for source in NEWS_SOURCES:
            try:
                for item in self._extract_listing(source):
                    if item["source_url"] in seen_urls:
                        unchanged += 1
                        continue
                    seen_urls.add(item["source_url"])
                    existing = self.db.scalar(select(NewsArticle).where(NewsArticle.source_url == item["source_url"]))
                    if existing:
                        next_image_url = item["image_url"] or existing.image_url
                        next_published_at = item["published_at"] or existing.published_at
                        content_changed = any(
                            (
                                existing.title != item["title"],
                                existing.summary != item["summary"],
                                existing.excerpt != item["excerpt"],
                                existing.category != item["category"],
                                existing.image_url != next_image_url,
                                not _same_datetime(existing.published_at, next_published_at),
                                existing.source_name != item["source_name"],
                            )
                        )
                        existing.title = item["title"]
                        existing.summary = item["summary"]
                        existing.excerpt = item["excerpt"]
                        existing.category = item["category"]
                        existing.image_url = next_image_url
                        existing.published_at = next_published_at
                        existing.source_name = item["source_name"]
                        if content_changed:
                            existing.scraped_at = datetime.now(UTC)
                            updated += 1
                        else:
                            unchanged += 1
                    else:
                        self.db.add(NewsArticle(**item))
                        inserted += 1
            except Exception as exc:
                errors.append({"source": source["name"], "error": str(exc)})
        try:
            self.db.commit()
            self._normalize_news_records()
        except IntegrityError:
            self.db.rollback()
            inserted = 0
            updated = 0
            errors.append({"source": "database", "error": "Trùng URL tin tức trong cùng lần quét; giao dịch đã được hoàn tác."})
        cleanup = self.cleanup_news_archive()
        if not self.db.scalar(select(NewsArticle.article_id).where(NewsArticle.category == "Phân bón - vật tư").limit(1)):
            self.seed_fallback_news()
        if inserted == 0 and updated == 0 and unchanged == 0:
            self.seed_fallback_news()
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged, "deleted": cleanup["deleted"], "errors": errors}

    def cleanup_news_archive(self) -> dict:
        rows = self.db.scalars(select(NewsArticle).limit(2000)).all()
        deleted = 0
        seen_titles: set[str] = set()
        rows = sorted(rows, key=_news_time_key, reverse=True)
        for row in rows:
            title_key = _normalize_ascii(_compact_news_title(row.title))
            # Archive policy: only remove invalid or duplicate news. Clean older
            # articles stay in the database so the public news archive grows.
            if not _is_keepable_news_article(row) or title_key in seen_titles:
                self.db.delete(row)
                deleted += 1
                continue
            seen_titles.add(title_key)
        if deleted:
            self.db.commit()
        return {"deleted": deleted}

    def guides(self, crop: str | None = None, limit: int = 120) -> list[GuidePost]:
        if not self.db.scalar(select(GuidePost.post_id).limit(1)):
            with _guide_seed_lock:
                if not self.db.scalar(select(GuidePost.post_id).limit(1)):
                    self.seed_guides()
        stmt = select(GuidePost).order_by(desc(GuidePost.published_at))
        if crop:
            stmt = stmt.where((GuidePost.crop_type == crop) | (GuidePost.crop_type.is_(None)))
        return self.db.scalars(stmt.limit(limit)).all()

    def ensure_guide_depth(self, force: bool = False) -> dict:
        rows = self.db.scalars(select(GuidePost).limit(2000)).all()
        updated = 0
        for row in rows:
            if not force and not _guide_needs_depth_upgrade(row.content):
                continue
            plant = _guide_plant_label(row)
            row.content = _expanded_guide_content(
                title=row.title,
                plant=plant,
                summary=row.summary,
                existing_content=row.content,
            )
            updated += 1
        if updated:
            self.db.commit()
            invalidate_cache("guides")
            invalidate_cache("guide-detail")
        return {"checked": len(rows), "updated": updated, "target_min_words": GUIDE_TARGET_MIN_WORDS}

    def seed_fallback_news(self) -> None:
        now = datetime.now(UTC)
        fallback_date = now - timedelta(days=14)
        fallback = [
            {
                "source_name": "Báo Nông nghiệp và Môi trường",
                "source_url": "https://nongnghiepmoitruong.vn/so-lieu-chi-tiet-ve-bien-dong-thi-truong-gia-ca-nong-san-8-thang-dau-nam-i360672.html",
                "title": "Số liệu biến động thị trường, giá cả nông sản",
                "summary": "Theo dõi biến động giá nông sản, xuất khẩu và các yếu tố thị trường có thể ảnh hưởng đến quyết định sản xuất.",
                "excerpt": "Ưu tiên dữ liệu giá và thị trường.",
                "category": "Giá và thị trường",
                "image_url": None,
                "published_at": fallback_date,
                "scraped_at": fallback_date,
            },
            {
                "source_name": "Báo Nông nghiệp và Môi trường",
                "source_url": "https://nongnghiepmoitruong.vn/tich-cuc-mo-rong-thi-truong-xuat-khau-nong-lam-thuy-san-tang-hon-15-d761075.html",
                "title": "Mở rộng thị trường, xuất khẩu nông lâm thủy sản tăng",
                "summary": "Thông tin xuất khẩu và mở rộng thị trường giúp nhìn nhanh sức cầu của nông sản Việt Nam.",
                "excerpt": "Xuất khẩu là nhóm tin có tác động trực tiếp tới giá nông sản.",
                "category": "Xuất khẩu",
                "image_url": None,
                "published_at": fallback_date,
                "scraped_at": fallback_date,
            },
            {
                "source_name": "Vinanet",
                "source_url": "https://vinanet.vn/vat-tu/gia-phan-bon-vat-tu-nong-nghiep-can-duoc-theo-doi-cung-gia-nong-san-000001.html",
                "title": "Theo dõi giá phân bón và vật tư đầu vào trong mùa vụ",
                "summary": "Biến động phân bón, thuốc bảo vệ thực vật và chi phí logistics có thể làm thay đổi biên lợi nhuận của nông dân ngay cả khi giá nông sản giữ ổn định.",
                "excerpt": "Nhóm tin phân bón - vật tư được đưa vào để đọc cùng giá nông sản và cảnh báo chi phí đầu vào.",
                "category": "Phân bón - vật tư",
                "image_url": None,
                "published_at": fallback_date,
                "scraped_at": fallback_date,
            },
        ]
        for item in fallback:
            existing = self.db.scalar(select(NewsArticle).where(NewsArticle.source_url == item["source_url"]))
            if existing:
                existing.title = item["title"]
                existing.summary = item["summary"]
                existing.excerpt = item["excerpt"]
                existing.category = item["category"]
                existing.image_url = item["image_url"]
                existing.published_at = item["published_at"]
                existing.scraped_at = item["scraped_at"]
                existing.source_name = item["source_name"]
            else:
                self.db.add(NewsArticle(**item))
        self.db.commit()

    def seed_guides(self) -> None:
        now = datetime.now(UTC)
        guides = [
            {
                "slug": "quan-ly-vuon-sau-rieng-mua-ra-hoa",
                "title": "Quản lý vườn sầu riêng giai đoạn ra hoa và đậu trái",
                "crop_type": "sau_rieng",
                "category": "Canh tác sầu riêng",
                "summary": "Khung thực hành cho nước tưới, dinh dưỡng, tỉa trái và kiểm soát stress trong giai đoạn quyết định năng suất.",
                "content": """
Mục tiêu
Giữ cây ổn định trong giai đoạn ra hoa, đậu trái và nuôi trái non. Trọng tâm là nước tưới đều, tán thông thoáng, dinh dưỡng vừa sức cây và kiểm soát stress sau mưa nắng thất thường.
Khi nào áp dụng
Áp dụng từ lúc mắt cua sáng rõ, cây chuẩn bị xổ nhụy, vừa đậu trái hoặc bước vào giai đoạn cần tỉa trái. Đây là thời điểm cây nhạy với dao động nước, thừa đạm và sâu bệnh trên bông, trái non.
Cách làm tại vườn
- Theo dõi ẩm đất hằng ngày, ưu tiên giữ ẩm ổn định thay vì tưới thật nhiều rồi để khô đột ngột.
- Hạn chế bón đạm mạnh khi cây đang phân hóa mầm hoa; ưu tiên kali, canxi, magie và trung vi lượng theo sức cây.
- Sau đậu trái, tỉa trái theo cành mang trái, tuổi cây và bộ lá; không giữ trái quá dày chỉ vì giá đang cao.
- Vệ sinh tán, bỏ cành khuất, cành sâu bệnh và trái dị dạng để giảm ẩm độ trong tán.
- Sau mưa lớn, kiểm tra nấm bệnh trên bông, cuống trái và vùng rễ; xử lý sớm trước khi lan rộng.
Theo dõi sau khi làm
Ghi tỷ lệ đậu trái, số trái giữ lại mỗi cây, lượng nước tưới và biểu hiện lá sau 3-5 ngày. Nếu lá rũ, trái non rụng nhiều hoặc cuống thâm nhanh, cần kiểm tra lại nước, rễ và nấm bệnh trước khi bón thêm phân.
Lỗi cần tránh
- Ép cây giữ quá nhiều trái khiến trái lớn chậm, cơm không đều và cây suy sau thu hoạch.
- Tưới thất thường trong giai đoạn bông và trái non.
- Bón phân theo cảm tính khi chưa xem sức lá, độ ẩm đất và bộ rễ.
Ghi chép nên có
Ghi ngày xổ nhụy, ngày đậu trái, số trái giữ lại, vật tư đã dùng, lượng mưa và ảnh chụp từng lô. Những dữ liệu này giúp so sánh vụ sau và đọc biến động năng suất sát thực tế hơn.
""",
                "author": "Ban kỹ thuật Dự báo nông sản",
                "published_at": now,
            },
            {
                "slug": "quan-ly-ca-phe-mua-kho",
                "title": "Quản lý cà phê mùa khô: nước tưới, che phủ và phục hồi cây",
                "crop_type": "ca_phe",
                "category": "Canh tác cà phê",
                "summary": "Hướng dẫn tổ chức tưới, giữ ẩm và phục hồi vườn cà phê trước giai đoạn nuôi trái.",
                "content": """
Mục tiêu
Giữ cây cà phê không bị sốc khô, phục hồi bộ lá sau thu hoạch và chuẩn bị nền sinh trưởng cho giai đoạn ra hoa, nuôi trái. Cách làm cần ưu tiên nước, che phủ và dinh dưỡng chia nhỏ.
Khi nào áp dụng
Áp dụng trong mùa khô, sau thu hoạch hoặc khi vườn có dấu hiệu rụng lá, lá cụp, cành mang trái yếu. Với vùng khô nóng kéo dài, nên kiểm tra ẩm đất trước khi quyết định lịch tưới.
Cách làm tại vườn
- Tưới theo ngưỡng ẩm đất, không tưới máy móc theo lịch cố định nếu đất vẫn còn ẩm.
- Che phủ gốc bằng cỏ khô, vỏ cà phê ủ hoai hoặc vật liệu hữu cơ sạch; chừa khoảng cách quanh gốc để hạn chế nấm.
- Tỉa cành khô, cành sâu bệnh và cành vô hiệu sau thu hoạch để cây tập trung phục hồi.
- Chia phân thành nhiều lần nhỏ, kết hợp hữu cơ hoai mục và khoáng theo sức cây.
- Kiểm tra rệp sáp, mọt đục cành và nấm rễ sau các đợt khô nóng, nhất là ở vườn có tán rậm.
Theo dõi sau khi làm
Theo dõi màu lá, chồi mới, độ ẩm lớp đất mặt và khả năng phục hồi sau mỗi lần tưới. Nếu cây vẫn héo sau tưới, cần kiểm tra rễ, tuyến trùng hoặc tình trạng đất nén chặt.
Lỗi cần tránh
- Tưới quá dày làm rễ thiếu oxy, sau đó lại để đất khô kiệt.
- Bón phân mạnh ngay sau thu hoạch khi cây chưa ra rễ mới.
- Dọn sạch toàn bộ lớp phủ khiến đất nóng nhanh và mất ẩm.
Ghi chép nên có
Ghi ngày tưới, lượng nước, lượng mưa, vật liệu che phủ, lượng phân và tình trạng sâu bệnh. Nhật ký này giúp tính chi phí mùa khô và dự báo năng suất vụ tới sát hơn.
""",
                "author": "Ban kỹ thuật Dự báo nông sản",
                "published_at": now,
            },
            {
                "slug": "nhat-ky-canh-tac-so",
                "title": "Thiết lập nhật ký canh tác số cho trang trại",
                "crop_type": None,
                "category": "Quản trị trang trại",
                "summary": "Cấu trúc dữ liệu tối thiểu để theo dõi chi phí, thời tiết, canh tác, sâu bệnh và chất lượng thu hoạch.",
                "content": """
Mục tiêu
Xây dựng nhật ký đủ dùng cho trang trại: dễ nhập, dễ tra cứu và đủ dữ liệu để kiểm soát chi phí, truy xuất nguồn gốc, đánh giá kỹ thuật và theo dõi rủi ro mùa vụ.
Khi nào áp dụng
Áp dụng ngay từ đầu vụ hoặc khi trang trại bắt đầu chia lô, thuê nhân công, dùng nhiều loại vật tư và cần theo dõi hiệu quả từng khu vực. Không nên đợi đến cuối vụ mới ghi lại vì dữ liệu rất dễ sai lệch.
Cách làm tại vườn
- Chia trang trại theo lô rõ ràng: tên lô, diện tích, giống, tuổi cây, mật độ và người phụ trách.
- Mỗi thao tác cần ghi ngày, nội dung công việc, vật tư dùng, liều lượng, nhân công, thời tiết và ảnh hiện trường nếu có.
- Với sâu bệnh, ghi triệu chứng, mật số, khu vực xuất hiện, cách xử lý và kết quả sau 3-7 ngày.
- Với thu hoạch, ghi sản lượng, loại hàng, tỷ lệ loại bỏ, giá bán, bên mua và chi phí vận chuyển.
- Dùng danh mục vật tư thống nhất để tránh một loại phân hoặc thuốc bị ghi thành nhiều tên khác nhau.
Theo dõi sau khi làm
Mỗi tuần xem lại chi phí theo lô, số lần xử lý sâu bệnh, lượng nước tưới và tiến độ sinh trưởng. Nếu một lô tốn chi phí cao nhưng sản lượng thấp, cần kiểm tra lại đất, giống, nước và quy trình chăm sóc.
Lỗi cần tránh
- Ghi quá nhiều trường khiến người làm ngại nhập, rồi bỏ dở giữa vụ.
- Chỉ ghi chi phí mà không ghi tình trạng cây, thời tiết và kết quả sau xử lý.
- Dùng ảnh nhưng không gắn ngày, lô và nội dung công việc.
Ghi chép nên có
Tối thiểu cần có ngày, lô, thao tác, vật tư, liều lượng, nhân công, thời tiết, ảnh và kết quả. Khi dữ liệu đều, trang trại có thể so sánh vụ này với vụ trước và ra quyết định bớt cảm tính hơn.
""",
                "author": "Ban kỹ thuật Dự báo nông sản",
                "published_at": now,
            },
        ]
        guides.extend(_durian_technical_guides(now))
        guides.extend(_urban_ornamental_guides(now))
        for item in guides:
            existing = self.db.scalar(select(GuidePost).where(GuidePost.slug == item["slug"]))
            if not existing:
                self.db.add(GuidePost(**item))
            elif item["slug"].startswith(("do-thi-", "sau-rieng-")) or item["slug"] in CURATED_GUIDE_SLUGS:
                existing.title = item["title"]
                existing.category = item["category"]
                existing.summary = item["summary"]
                existing.content = item["content"]
                existing.author = item["author"]
        self.db.commit()
        self.seed_hainong_guides()

    def seed_hainong_guides(self) -> None:
        if get_settings().database_url == "sqlite:///:memory:":
            return
        if self.db.scalar(select(GuidePost).where(GuidePost.slug.like("hainong-%"))):
            return
        try:
            catalogues = self._fetch_hainong_catalogues()
            guides = self._fetch_hainong_technical_guides(catalogues)
        except Exception:
            return
        for item in guides:
            if not self.db.scalar(select(GuidePost).where(GuidePost.slug == item["slug"])):
                self.db.add(GuidePost(**item))
        self.db.commit()

    def _fetch_hainong_catalogues(self) -> list[dict]:
        response = requests.get(
            f"{HAINONG_TECHNICAL_API}/catalogues",
            params={"limit": 2000},
            timeout=20,
            headers={"User-Agent": "MarketAI/1.0"},
        )
        response.raise_for_status()
        rows = response.json().get("data", [])
        return [
            row
            for row in rows
            if row.get("name") in HAINONG_GUIDE_SECTIONS
            and not _contains_any(_normalize_ascii(row.get("fullname", "")), HAINONG_EXCLUDED_TERMS)
        ]

    def _fetch_hainong_technical_guides(self, catalogues: list[dict]) -> list[dict]:
        now = datetime.now(UTC)
        guides = []
        seen: set[int] = set()
        for catalogue in catalogues:
            response = requests.get(
                HAINONG_TECHNICAL_API,
                params={"limit": 100, "page": 1, "technical_process_catalogue_id": catalogue["id"]},
                timeout=20,
                headers={"User-Agent": "MarketAI/1.0"},
            )
            response.raise_for_status()
            for article in response.json().get("data", []):
                if article.get("id") in seen:
                    continue
                title = _clean(article.get("title", ""))
                if not title or _contains_any(_normalize_ascii(title), HAINONG_EXCLUDED_TERMS):
                    continue
                source_url = f"https://hainong.vn/quy-trinh-ky-thuat/chi-tiet/{article.get('slug') or article.get('id')}"
                plant = _plant_from_fullname(catalogue.get("fullname", ""))
                if plant == "Cây trồng":
                    plant = _plant_from_title(title)
                category = _guide_category(catalogue.get("name", ""), plant)
                images = _extract_hainong_images(article)
                content = _technical_guide_content(
                    title=title,
                    plant=plant,
                    source_url=source_url,
                    source_text=_strip_html(article.get("content", "")),
                    image_urls=images,
                )
                guides.append(
                    {
                        "slug": f"{_slugify(article.get('slug') or title)}-{article.get('id')}",
                        "title": _guide_title(title, plant),
                        "crop_type": _crop_key(plant),
                        "category": category,
                        "summary": _guide_summary(title, plant),
                        "content": content,
                        "author": "Ban kỹ thuật Dự báo nông sản",
                        "published_at": now,
                    }
                )
                seen.add(article.get("id"))
        return guides

    def _extract_listing(self, source: dict) -> list[dict]:
        items = []
        seen = set()
        max_items = int(source.get("max_items", NEWS_MAX_ITEMS_PER_SOURCE))
        detail_lookups = 0
        for listing_url in _listing_urls(source):
            response = requests.get(
                listing_url,
                timeout=NEWS_HTTP_TIMEOUT_SECONDS,
                headers={"User-Agent": "Mozilla/5.0 MarketAI/1.0"},
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.find_all("a", href=True):
                raw_title = _clean(link.get_text(" ", strip=True))
                title = _compact_news_title(raw_title)
                href = _normalize_news_url(urljoin(listing_url, link["href"]), listing_url)
                if len(title) < 24 or href in seen:
                    continue
                if not _is_supported_news_url(href):
                    continue
                if not _is_vietnamese_text(title):
                    continue
                if not _looks_like_article(href):
                    continue
                summary = _clean(_nearby_text(link))
                article_summary = _summary_without_title(summary or raw_title, title)
                if not _is_relevant_market_news(f"{title} {article_summary}"):
                    continue
                published_at = _parse_date(article_summary or summary)
                image_url = _nearby_image(link, listing_url)
                if (published_at is None or image_url is None) and detail_lookups < NEWS_DETAIL_LOOKUP_LIMIT:
                    meta_published_at, meta_image_url = _article_metadata(href)
                    detail_lookups += 1
                    published_at = published_at or meta_published_at
                    image_url = image_url or meta_image_url
                items.append(
                    {
                        "source_name": _normalize_news_source_name(source["name"], href),
                        "source_url": href,
                        "title": title,
                        "summary": article_summary[:700],
                        "excerpt": _truncate_words(article_summary or title, 180),
                        "category": _category_for(title, article_summary, source["category"]),
                        "image_url": image_url,
                        "published_at": published_at,
                        "scraped_at": datetime.now(UTC),
                    }
                )
                seen.add(href)
                if len(items) >= max_items:
                    return items
        return items


def _durian_technical_guides(now: datetime) -> list[dict]:
    return [
        {
            "slug": "sau-rieng-thiet-lap-vuon-moi",
            "title": "Thiết lập vườn sầu riêng mới: đất, mương, bờ và cây giống",
            "crop_type": "sau_rieng",
            "category": "Cẩm nang sầu riêng",
            "summary": "Các bước chuẩn bị nền vườn sầu riêng từ thoát nước, mật độ, cây giống đến kế hoạch ghi chép trước khi xuống giống.",
            "content": """
Mục tiêu
Tạo nền vườn thông thoáng, chủ động nước và giảm rủi ro chết cây trong 12 tháng đầu. Với sầu riêng, chuẩn bị đất và thoát nước tốt quan trọng hơn việc bón thật nhiều phân lúc mới trồng.
Khi nào áp dụng
Áp dụng trước khi mở vườn mới, cải tạo vườn tạp hoặc trồng lại sau khi vườn cũ bị bệnh rễ. Nên làm trước mùa mưa để kịp ổn định mô, mương và nguồn cây giống.
Cách làm tại vườn
- Khảo sát cao độ vườn, hướng thoát nước và điểm thường ngập sau mưa lớn; không trồng khi chưa có đường thoát nước rõ.
- Lên mô hoặc líp cao ở vùng đất thấp; mương phải đủ sâu để rút nước nhanh nhưng không làm khô kiệt tầng rễ mùa nắng.
- Chọn cây giống có nguồn rõ, mắt ghép liền, lá già ổn định, rễ trắng khỏe; loại cây có bầu nứt, rễ xoắn hoặc thân bị xì mủ.
- Bố trí mật độ theo giống, đất và khả năng cơ giới; chừa lối đi để vận chuyển, phun tưới và thu hoạch sau này.
- Chuẩn bị trụ che nắng, cọc giữ cây và lớp phủ gốc ngay sau trồng, nhưng không phủ sát cổ rễ.
Theo dõi sau khi làm
Trong 30 ngày đầu, kiểm tra tỷ lệ sống, độ đứng cây, màu lá và độ ẩm mô sau mưa. Cây ổn định thường giữ lá xanh, không rũ kéo dài và bắt đầu ra đọt mới sau khi hồi rễ.
Lỗi cần tránh
- Trồng theo phong trào khi chưa có hệ thống thoát nước.
- Chọn cây giống chỉ theo giá rẻ hoặc lời giới thiệu miệng.
- Đào hố sâu ở đất nặng làm nước đọng quanh rễ non.
Ghi chép nên có
Ghi nguồn giống, ngày trồng, mật độ, kích thước mô, vật liệu cải tạo đất và ảnh từng lô. Đây là dữ liệu nền để truy lại khi cây sinh trưởng không đồng đều.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-quan-ly-nuoc-mua-kho",
            "title": "Quản lý nước mùa khô cho sầu riêng: giữ ẩm đều, tránh sốc cây",
            "crop_type": "sau_rieng",
            "category": "Chăm sóc sầu riêng",
            "summary": "Cách kiểm soát nước tưới, che phủ và theo dõi ẩm đất để vườn sầu riêng không bị sốc khô hoặc úng cục bộ.",
            "content": """
Mục tiêu
Giữ ẩm tầng rễ ổn định để cây không rụng lá, cháy mép lá hoặc rụng trái non. Quản lý nước tốt giúp cây hấp thu dinh dưỡng đều và giảm áp lực bệnh rễ.
Khi nào áp dụng
Áp dụng trong mùa khô, giai đoạn cây ra đọt, ra hoa, nuôi trái hoặc sau những ngày nắng nóng kéo dài. Vườn có đất cát, mô cao hoặc tán lớn cần kiểm tra ẩm thường xuyên hơn.
Cách làm tại vườn
- Kiểm tra ẩm đất ở vùng rìa tán, không chỉ nhìn mặt đất quanh gốc.
- Tưới chậm, chia đều theo vùng rễ hoạt động; tránh tưới dồn một điểm làm rễ thiếu oxy.
- Che phủ bằng cỏ khô, lá cây sạch hoặc vật liệu hữu cơ hoai; chừa cổ rễ thoáng để hạn chế nấm.
- Sau một đợt khô dài, tăng nước từ từ, không tưới quá mạnh ngay lần đầu.
- Theo dõi dự báo thời tiết để giảm tưới trước mưa lớn, tránh mô đang ướt lại gặp mưa dầm.
Theo dõi sau khi làm
Quan sát lá non, độ bóng lá, tình trạng rụng lá già và độ khô của lớp đất dưới phủ. Nếu cây vẫn héo sau tưới, cần kiểm tra rễ, tuyến trùng hoặc nấm đất.
Lỗi cần tránh
- Tưới theo lịch cứng mà không kiểm tra ẩm thực tế.
- Phủ kín cổ rễ khiến vùng gốc ẩm kéo dài.
- Tưới quá nhiều sau khi cây vừa trải qua khô hạn nặng.
Ghi chép nên có
Ghi ngày tưới, thời lượng tưới, lượng mưa, tình trạng lá và độ ẩm đất. Sau vài tuần sẽ xác định được chu kỳ tưới phù hợp cho từng lô.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-xu-ly-ra-hoa-an-toan",
            "title": "Xử lý ra hoa sầu riêng an toàn: đọc sức cây trước khi làm bông",
            "crop_type": "sau_rieng",
            "category": "Cẩm nang sầu riêng",
            "summary": "Khung kiểm tra sức cây, bộ lá, nước tưới và thời tiết trước khi xử lý ra hoa để giảm rụng bông và suy cây.",
            "content": """
Mục tiêu
Giúp cây ra hoa đồng đều nhưng vẫn giữ sức nuôi trái về sau. Làm bông sầu riêng cần dựa trên sức cây, tuổi lá và thời tiết, không nên chạy theo giá ngắn hạn.
Khi nào áp dụng
Áp dụng khi cây đã qua thu hoạch, phục hồi tán đủ tốt, lá đã già ổn định và vườn có khả năng chủ động nước. Không áp dụng cho cây vừa suy, rễ yếu hoặc tán lá thưa.
Cách làm tại vườn
- Đánh giá cây theo từng lô: màu lá, độ dày lá, số cơi đọt, tình trạng rễ và lịch bệnh gần nhất.
- Dọn tán thông thoáng, bỏ cành sâu bệnh và cành khuất sáng trước khi xử lý.
- Điều tiết nước theo ngưỡng vừa đủ tạo phân hóa mầm, không để cây khô kiệt kéo dài.
- Khi mắt cua sáng, giữ ẩm ổn định và hạn chế tác động mạnh lên rễ.
- Theo dõi mưa trái mùa; nếu mưa kéo dài, ưu tiên ổn định cây hơn là ép ra hoa bằng mọi giá.
Theo dõi sau khi làm
Ghi tỷ lệ mắt cua, độ đồng đều bông và số cành mang bông. Nếu bông ra loạt nhưng lá xuống màu nhanh, cần giảm tải sớm và kiểm tra dinh dưỡng, nước, rễ.
Lỗi cần tránh
- Xử lý ra hoa khi lá còn non hoặc cây chưa phục hồi sau vụ trước.
- Siết nước quá mạnh làm cây rụng lá, nứt cành nhỏ hoặc suy rễ.
- Bón phân kích quá tay nhưng không theo dõi phản ứng của cây.
Ghi chép nên có
Ghi ngày bắt đầu xử lý, trạng thái lá, lượng mưa, ngày mắt cua, ngày xổ nhụy và tỷ lệ bông hữu hiệu. Dữ liệu này giúp điều chỉnh lịch vụ sau.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-thu-phan-dau-trai",
            "title": "Thụ phấn và giữ trái non sầu riêng: thao tác đúng thời điểm",
            "crop_type": "sau_rieng",
            "category": "Chăm sóc sầu riêng",
            "summary": "Hướng dẫn theo dõi xổ nhụy, hỗ trợ thụ phấn, giữ ẩm và hạn chế rụng trái non trong giai đoạn nhạy cảm.",
            "content": """
Mục tiêu
Tăng tỷ lệ đậu trái có chất lượng, giảm trái méo và hạn chế rụng sinh lý. Giai đoạn này cần thao tác nhẹ, đúng thời điểm và giữ cây ổn định.
Khi nào áp dụng
Áp dụng khi vườn bước vào xổ nhụy, thời tiết thất thường, thiếu côn trùng thụ phấn hoặc giống có tỷ lệ đậu tự nhiên không cao.
Cách làm tại vườn
- Theo dõi giờ xổ nhụy của từng giống để bố trí nhân công hỗ trợ đúng lúc.
- Chọn hoa khỏe, vị trí thuận lợi, không lấy phấn từ hoa bệnh hoặc hoa đã ẩm nước.
- Giữ ẩm đất ổn định trước và sau thụ phấn, tránh để cây sốc khô rồi tưới dồn.
- Không phun thuốc có nguy cơ ảnh hưởng hoa trong thời điểm thụ phấn.
- Sau đậu trái, đánh dấu cành mang trái để tiện theo dõi và tỉa trái theo sức cành.
Theo dõi sau khi làm
Kiểm tra tỷ lệ đậu sau 7-10 ngày, quan sát cuống trái, màu trái non và mức rụng. Nếu rụng hàng loạt, cần xem lại nước tưới, mưa, nấm bệnh và sức cây.
Lỗi cần tránh
- Thụ phấn quá muộn khi hoa đã giảm khả năng nhận phấn.
- Giữ quá nhiều trái non vì tiếc công thụ phấn.
- Phun thuốc hoặc dinh dưỡng mạnh ngay lúc hoa đang nhạy cảm.
Ghi chép nên có
Ghi ngày xổ nhụy, giống lấy phấn, số cành thao tác, tỷ lệ đậu và thời tiết trong 3 ngày quanh thụ phấn. Đây là cơ sở để cải thiện mùa sau.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-tia-trai-nuoi-trai",
            "title": "Tỉa trái và nuôi trái sầu riêng: giữ sản lượng vừa sức cây",
            "crop_type": "sau_rieng",
            "category": "Chăm sóc sầu riêng",
            "summary": "Quy trình chọn trái, phân bố trái trên cành và theo dõi dinh dưỡng để nâng chất lượng cơm, giảm suy cây sau thu hoạch.",
            "content": """
Mục tiêu
Giữ số trái phù hợp với tuổi cây, bộ lá và sức cành để trái lớn đều, ít méo và cây không suy nặng sau vụ. Năng suất tốt phải đi cùng khả năng phục hồi.
Khi nào áp dụng
Áp dụng từ khi trái non ổn định đến trước giai đoạn tăng cơm mạnh. Vườn đậu quá dày, cành nhỏ mang nhiều trái hoặc cây có dấu hiệu xuống lá cần tỉa sớm.
Cách làm tại vườn
- Loại trái méo, trái sâu bệnh, trái nằm sát thân khó chăm sóc hoặc vị trí dễ cọ xát.
- Phân bố trái đều trên cành cấp phù hợp; không để một cành yếu mang cụm trái quá nặng.
- Ưu tiên giữ trái có cuống khỏe, gai phát triển đều và vị trí thuận tiện chống đỡ.
- Tăng dinh dưỡng theo từng giai đoạn nuôi trái, tránh bón dồn làm sốc rễ.
- Dùng dây đỡ hoặc khung chống khi trái lớn, nhất là cành nằm ngang hoặc sau mưa gió.
Theo dõi sau khi làm
Theo dõi tốc độ lớn trái, màu lá, rụng sinh lý và hiện tượng nứt gai, thâm cuống. Nếu trái lớn chậm đồng loạt, cần kiểm tra nước, rễ và tải trái.
Lỗi cần tránh
- Giữ trái vượt sức cây vì giá thị trường đang cao.
- Tỉa quá muộn khiến cây đã tiêu hao dinh dưỡng cho trái phải bỏ.
- Bón phân theo một công thức chung cho mọi lô, mọi tuổi cây.
Ghi chép nên có
Ghi số trái giữ lại theo cây, ngày tỉa từng đợt, lượng phân, lượng nước và ảnh đại diện theo lô. Sau thu hoạch nên so sánh tỷ lệ loại đẹp, loại lỗi và sức phục hồi.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-phong-benh-thoi-re-xi-mu",
            "title": "Phòng bệnh thối rễ, xì mủ trên sầu riêng từ quản lý nước và cổ rễ",
            "crop_type": "sau_rieng",
            "category": "Chăm sóc sầu riêng",
            "summary": "Cách phát hiện sớm và giảm áp lực bệnh thối rễ, xì mủ bằng thoát nước, vệ sinh gốc và theo dõi sau mưa.",
            "content": """
Mục tiêu
Giảm nguy cơ bệnh rễ và xì mủ làm cây suy, rụng lá, rụng trái hoặc chết cục bộ. Trọng tâm là phòng từ điều kiện đất nước, không đợi cây bệnh nặng mới xử lý.
Khi nào áp dụng
Áp dụng quanh năm, đặc biệt trước và sau mùa mưa, ở vườn đất nặng, thoát nước chậm, phủ gốc dày hoặc từng có cây bị xì mủ.
Cách làm tại vườn
- Giữ cổ rễ thoáng, không đắp đất hoặc vật liệu hữu cơ sát thân.
- Khơi mương và rãnh thoát nước trước mùa mưa; sau mưa lớn phải kiểm tra điểm đọng nước.
- Vệ sinh tàn dư bệnh, cắt bỏ rễ thối lộ ra ngoài và xử lý dụng cụ sau khi làm cây bệnh.
- Theo dõi vết nứt, chảy nhựa, vỏ sẫm màu ở thân và cành; đánh dấu để kiểm tra lại.
- Khi cần dùng thuốc, xử lý đúng vị trí bệnh và theo khuyến cáo địa phương; không phun đại trà khi chưa xác định vấn đề.
Theo dõi sau khi làm
Quan sát vết xì mủ có khô lại không, lá có phục hồi màu không và cây có ra rễ non mới không. Nếu bệnh tiếp tục lan, cần tách khu vực, kiểm tra thoát nước và xem lại nguồn lây.
Lỗi cần tránh
- Phủ gốc quá kín làm cổ rễ ẩm liên tục.
- Chỉ bôi vết thân mà bỏ qua nguyên nhân úng rễ.
- Dùng chung dao, kéo từ cây bệnh sang cây khỏe mà không khử sạch.
Ghi chép nên có
Ghi vị trí cây bệnh, ngày phát hiện, triệu chứng, lượng mưa gần nhất, biện pháp đã làm và ảnh vết bệnh sau 3-7 ngày. Nhật ký này giúp nhận ra lô có nguy cơ cao.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-quan-ly-rep-sap-sau-duc-trai",
            "title": "Quản lý rệp sáp và sâu đục trái sầu riêng theo hướng IPM",
            "crop_type": "sau_rieng",
            "category": "Chăm sóc sầu riêng",
            "summary": "Cách thăm vườn, nhận diện điểm nóng và kết hợp vệ sinh tán, bao trái, thiên địch, thuốc đúng ngưỡng để giảm lỗi trái.",
            "content": """
Mục tiêu
Giảm thiệt hại trên trái và hạn chế dư lượng không cần thiết. IPM trên sầu riêng bắt đầu từ thăm vườn đều, phát hiện sớm và xử lý đúng điểm nóng.
Khi nào áp dụng
Áp dụng từ giai đoạn ra đọt, ra bông đến nuôi trái, nhất là vườn tán rậm, nhiều kiến, cỏ dại cao hoặc từng bị rệp sáp, sâu đục trái.
Cách làm tại vườn
- Kiểm tra mặt dưới lá, chùm bông, cuống trái và nơi kiến di chuyển; đây thường là điểm rệp sáp xuất hiện sớm.
- Tỉa tán thông thoáng, dọn trái rụng và cành khô để giảm nơi trú ẩn.
- Quản lý kiến vì kiến thường bảo vệ rệp sáp, làm mật số tăng nhanh.
- Bao trái hoặc che chắn khi phù hợp với giống và điều kiện vườn để giảm côn trùng chích, đục.
- Chỉ dùng thuốc khi mật số vượt ngưỡng chịu đựng; luân phiên hoạt chất và phun đúng vị trí.
Theo dõi sau khi làm
Sau xử lý 3-5 ngày, kiểm tra lại cùng vị trí đã đánh dấu. Nếu mật số không giảm, xem lại kỹ thuật phun, thời điểm phun, mưa sau phun và khả năng còn ổ trứng.
Lỗi cần tránh
- Thấy vài trái bị hại đã phun toàn vườn khi chưa kiểm tra mật số.
- Bỏ qua kiến và cỏ dại quanh gốc.
- Phun lúc tán quá rậm khiến thuốc không tới vị trí cần xử lý.
Ghi chép nên có
Ghi mật số, vị trí điểm nóng, biện pháp đã dùng, thời tiết sau xử lý và tỷ lệ trái bị lỗi khi thu hoạch. Dữ liệu này giúp giảm chi phí thuốc vụ sau.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-phuc-hoi-sau-thu-hoach",
            "title": "Phục hồi cây sầu riêng sau thu hoạch: rễ, lá và bộ khung vụ sau",
            "crop_type": "sau_rieng",
            "category": "Chăm sóc sầu riêng",
            "summary": "Khung chăm sóc sau thu hoạch để cây ra rễ mới, phục hồi tán và chuẩn bị cho chu kỳ ra hoa tiếp theo.",
            "content": """
Mục tiêu
Giúp cây trả lại sức sau khi mang trái, phục hồi rễ và lá trước khi tính chuyện làm vụ mới. Cây phục hồi tốt sẽ giảm rủi ro rụng bông, rụng trái và suy sau vụ sau.
Khi nào áp dụng
Áp dụng ngay sau thu hoạch, đặc biệt với cây mang trái nhiều, lá xuống màu, cành nhỏ khô hoặc vườn vừa trải qua mưa nắng cực đoan.
Cách làm tại vườn
- Thu gom trái rụng, dây buộc, vật tư và vệ sinh vườn để giảm nguồn sâu bệnh.
- Tỉa cành khô, cành sâu bệnh, cành khuất sáng; không cắt quá mạnh khi cây đang suy.
- Kiểm tra rễ và thoát nước trước khi bón phục hồi, vì rễ yếu thì bón nhiều cũng không hiệu quả.
- Bón hữu cơ hoai mục và dinh dưỡng khoáng chia nhỏ theo sức cây; ưu tiên phục hồi rễ trước khi thúc đọt mạnh.
- Giữ ẩm ổn định, che phủ vừa phải và theo dõi cơi đọt mới.
Theo dõi sau khi làm
Quan sát lá mới, rễ non, màu lá và mức rụng lá già. Cây phục hồi đúng hướng thường ra đọt khỏe, lá dày và tán sáng hơn sau vài tuần.
Lỗi cần tránh
- Vừa thu xong đã ép cây làm bông lại khi chưa phục hồi.
- Bón mạnh một lần vì muốn cây bật nhanh.
- Cắt tỉa quá nặng làm cây mất cân bằng tán.
Ghi chép nên có
Ghi sản lượng từng cây/lô, số trái giữ, thời điểm thu, biện pháp phục hồi và phản ứng sau 2-4 tuần. Đây là căn cứ để quyết định cây nào nên giảm tải vụ tới.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-thu-hoach-phan-loai",
            "title": "Thu hoạch và phân loại sầu riêng: giảm dập, giữ chất lượng lô hàng",
            "crop_type": "sau_rieng",
            "category": "Cẩm nang sầu riêng",
            "summary": "Quy trình xác định độ già, tổ chức thu hái, vận chuyển và phân loại để hạn chế lỗi cơm, dập gai và khiếu nại thương lái.",
            "content": """
Mục tiêu
Thu hoạch đúng độ già, giảm va đập và giữ lô hàng đồng đều. Khâu thu hoạch quyết định trực tiếp uy tín vườn, đặc biệt khi bán theo hợp đồng hoặc xuất khẩu.
Khi nào áp dụng
Áp dụng trước và trong thời gian thu hoạch, khi vườn có nhiều đợt xổ nhụy hoặc nhiều giống khác nhau. Cần chuẩn bị sớm để tránh hái gấp khi giá biến động.
Cách làm tại vườn
- Ghi ngày xổ nhụy theo lô để ước tính tuổi trái, không chỉ dựa vào cảm giác.
- Kiểm tra độ già theo giống, gai, cuống, âm thanh và yêu cầu của bên mua.
- Dùng dụng cụ cắt sạch, có người đỡ trái, tránh để trái rơi tự do làm dập cơm.
- Tập kết nơi râm mát, nền sạch, không chất đống quá cao.
- Phân loại theo giống, kích cỡ, độ đồng đều, lỗi vỏ, lỗi cuống và yêu cầu hợp đồng.
Theo dõi sau khi làm
Theo dõi tỷ lệ trái bị trả, lỗi cơm, nứt vỏ, dập gai và phản hồi của bên mua. Nếu lỗi tập trung ở một lô, cần truy lại ngày xổ nhụy, nước tưới và thao tác thu.
Lỗi cần tránh
- Hái đồng loạt khi trái chưa cùng độ già.
- Kéo, quăng hoặc lăn trái trên nền cứng.
- Trộn nhiều giống, nhiều độ già trong cùng một lô giao.
Ghi chép nên có
Ghi ngày thu, lô, giống, số trái, khối lượng, tỷ lệ loại 1-2-3, giá bán và phản hồi chất lượng. Dữ liệu này giúp thương lượng tốt hơn cho vụ sau.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
        {
            "slug": "sau-rieng-nhat-ky-vung-trong-truy-xuat",
            "title": "Nhật ký vùng trồng sầu riêng: dữ liệu cần có để truy xuất và bán hàng ổn định",
            "crop_type": "sau_rieng",
            "category": "Cẩm nang sầu riêng",
            "summary": "Mẫu dữ liệu tối thiểu cho vườn sầu riêng: lô, giống, vật tư, sâu bệnh, thu hoạch, mã vùng trồng và lịch chăm sóc.",
            "content": """
Mục tiêu
Chuẩn hóa ghi chép để vườn dễ truy xuất, kiểm soát chi phí và đáp ứng yêu cầu của bên mua. Nhật ký tốt không làm vườn phức tạp hơn; nó giúp người trồng nhớ đúng việc đã làm.
Khi nào áp dụng
Áp dụng cho vườn muốn bán ổn định, tham gia tổ hợp tác, hợp tác xã, làm mã vùng trồng hoặc theo dõi chi phí theo từng lô.
Cách làm tại vườn
- Chia vườn thành lô rõ ràng: diện tích, giống, tuổi cây, số cây, người phụ trách.
- Mỗi lần dùng vật tư phải ghi tên, liều lượng, ngày dùng, mục đích và lô áp dụng.
- Ghi sâu bệnh theo triệu chứng, mật số, vị trí, biện pháp xử lý và kết quả sau 3-7 ngày.
- Ghi thời tiết quan trọng: mưa lớn, hạn, ngập, gió mạnh, nắng nóng kéo dài.
- Khi thu hoạch, ghi ngày xổ nhụy, ngày cắt, sản lượng, phân loại, bên mua và phản hồi chất lượng.
Theo dõi sau khi làm
Mỗi tuần xem lại lô nào tốn nhiều vật tư, lô nào sâu bệnh lặp lại, lô nào có sản lượng hoặc chất lượng kém. Đó là tín hiệu để kiểm tra đất, nước, giống và kỹ thuật.
Lỗi cần tránh
- Ghi quá nhiều trường khó nhập rồi bỏ dở giữa vụ.
- Chỉ ghi chi phí mà không ghi tình trạng cây và kết quả sau xử lý.
- Không thống nhất tên vật tư, khiến cùng một loại bị ghi thành nhiều tên khác nhau.
Ghi chép nên có
Tối thiểu cần có ngày, lô, thao tác, vật tư, liều lượng, thời tiết, ảnh hiện trường, người thực hiện và kết quả. Khi dữ liệu đều, vườn dễ kiểm soát rủi ro và chứng minh chất lượng với bên mua.
""",
            "author": "Ban kỹ thuật Dự báo nông sản",
            "published_at": now,
        },
    ]


def _urban_ornamental_guides(now: datetime) -> list[dict]:
    return [
        _urban_guide(
            now,
            slug="do-thi-cam-nang-trau-ba",
            title="Cẩm nang trồng trầu bà trong căn hộ đô thị",
            category="Cẩm nang trầu bà",
            summary="Cách chọn vị trí, chậu, giá thể và dây leo cho trầu bà khi trồng trong nhà, ban công hoặc góc làm việc ít nắng.",
            content="""
Mục tiêu
Thiết lập một chậu trầu bà khỏe, lá xanh bền và dễ chăm trong điều kiện đô thị. Trọng tâm là ánh sáng tán xạ, giá thể thoát nước nhanh, chậu có lỗ đáy và cách bố trí để cây không bị úng trong phòng kín.
Khi nào áp dụng
Áp dụng khi bắt đầu mua cây mới, tách nhánh, chuyển cây từ bình nước sang chậu đất hoặc đưa cây vào không gian thiếu nắng trực tiếp như căn hộ, văn phòng, quán cà phê.
Cách làm tại vườn
- Chọn cây có rễ trắng ngà, thân chắc, lá không bị đốm nâu loang rộng hoặc mềm nhũn ở gốc.
- Dùng chậu có lỗ thoát nước; đường kính chậu chỉ nên lớn hơn bầu rễ khoảng 3-5 cm để giá thể không giữ ẩm quá lâu.
- Phối giá thể theo hướng tơi xốp: xơ dừa đã xử lý, vỏ thông nhỏ, đá perlite hoặc trấu hun; tránh dùng đất thịt nặng trong chậu nhỏ.
- Đặt cây ở nơi sáng tán xạ, gần cửa sổ có rèm hoặc ban công khuất nắng gắt buổi trưa.
- Nếu muốn cây leo, dùng cọc rêu hoặc lưới mảnh; buộc thân bằng dây mềm, không siết vào đốt thân.
Theo dõi sau khi làm
Quan sát độ căng của lá và độ khô của 2-3 cm mặt giá thể. Cây ổn định thường ra lá mới sau 2-4 tuần. Nếu lá vàng hàng loạt, cần kiểm tra lại thoát nước và lượng tưới trước khi nghĩ tới thiếu dinh dưỡng.
Lỗi cần tránh
- Tưới theo lịch cố định mỗi ngày dù giá thể còn ẩm.
- Đặt sát kính hướng Tây khiến lá cháy mép trong ngày nắng.
- Dùng chậu trang trí không có lỗ thoát nước nhưng vẫn tưới trực tiếp vào đó.
Ghi chép nên có
Ghi vị trí đặt cây, ngày thay chậu, loại giá thể, ngày tưới và phản ứng của lá trong 2 tuần đầu để tìm ra góc đặt phù hợp nhất.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cham-soc-trau-ba",
            title="Chăm sóc trầu bà: tưới nước, cắt tỉa và phục hồi lá vàng",
            category="Chăm sóc trầu bà",
            summary="Quy trình chăm trầu bà theo tuần, tập trung vào kiểm soát nước, vệ sinh lá, cắt tỉa dây leo và xử lý lá vàng do úng hoặc thiếu sáng.",
            content="""
Mục tiêu
Duy trì trầu bà xanh lá, ít sâu bệnh và ra đọt đều trong không gian đô thị. Bài này ưu tiên thao tác đơn giản, dễ lặp lại mỗi tuần.
Khi nào áp dụng
Áp dụng cho chậu trầu bà đã trồng ổn định, cây để trong phòng điều hòa, gần cửa sổ, hành lang chung cư hoặc ban công có mái che.
Cách làm tại vườn
- Chỉ tưới khi mặt giá thể đã se khô; tưới chậm đến khi nước thoát ra đáy rồi bỏ phần nước đọng ở đĩa lót.
- Lau bụi trên lá 1-2 lần/tháng bằng khăn mềm ẩm để lá nhận sáng tốt hơn.
- Cắt bỏ lá vàng, lá mềm nhũn và đoạn thân thối bằng kéo sạch; không giật lá làm rách thân.
- Xoay chậu mỗi 1-2 tuần để tán nhận sáng đều, hạn chế cây nghiêng hẳn về một phía.
- Khi dây quá dài, cắt phía trên một đốt thân khỏe để kích chồi mới; đoạn cắt có thể giâm lại trong nước sạch.
Theo dõi sau khi làm
Nếu lá vàng bắt đầu từ lá già đơn lẻ, cây có thể đang tự thay lá. Nếu vàng nhanh, lan từ gốc và giá thể có mùi chua, cần giảm tưới, kiểm tra rễ và thay phần giá thể bị bí.
Lỗi cần tránh
- Phun sương liên tục trong phòng thiếu gió, làm nấm lá dễ phát sinh.
- Bón phân đậm khi cây đang úng hoặc rễ yếu.
- Để nước đọng lâu trong chậu bọc ngoài.
Ghi chép nên có
Ghi ngày tưới, số lá vàng đã cắt, vị trí đặt cây và thời điểm cây ra lá mới. Sau 1 tháng sẽ thấy rõ cây hợp góc sáng nào.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cam-nang-luoi-ho",
            title="Cẩm nang trồng lưỡi hổ cho nhà phố và văn phòng",
            category="Cẩm nang lưỡi hổ",
            summary="Hướng dẫn chọn chậu, giá thể và vị trí đặt lưỡi hổ để cây đứng dáng, ít úng rễ và phù hợp môi trường trong nhà.",
            content="""
Mục tiêu
Trồng lưỡi hổ theo hướng bền, sạch và ít công chăm. Đây là nhóm cây chịu khô tốt, hợp căn hộ và văn phòng, nhưng rất dễ hỏng nếu chậu bí nước.
Khi nào áp dụng
Áp dụng khi mua cây mới, sang chậu, tách bụi hoặc bố trí cây ở sảnh, bàn làm việc, hành lang và ban công có mái che.
Cách làm tại vườn
- Chọn bụi có lá cứng, đứng, không có vết mềm nhũn ở cổ rễ.
- Chậu nên nặng vừa đủ để cây không đổ, có lỗ thoát nước rõ; không chọn chậu quá sâu nếu rễ còn nhỏ.
- Giá thể cần thoáng: đất sạch phối trấu hun, đá pumice/perlite hoặc cát hạt lớn; hạn chế xơ dừa giữ nước quá mạnh.
- Đặt cây ở nơi sáng vừa đến sáng mạnh tán xạ. Cây chịu được góc ít sáng, nhưng màu lá và tốc độ ra lá sẽ kém hơn.
- Sau khi sang chậu, để cây nghỉ 3-5 ngày rồi mới tưới đẫm lần đầu nếu giá thể còn ẩm.
Theo dõi sau khi làm
Lá lưỡi hổ khỏe sẽ giữ dáng cứng và không nhăn. Nếu lá mềm ở gốc, nghiêng dần hoặc có mùi ẩm, cần nhấc bầu kiểm tra rễ ngay.
Lỗi cần tránh
- Tưới ít nhưng tưới quá thường xuyên, làm vùng cổ rễ luôn ẩm.
- Đặt cây trong góc tối hoàn toàn nhiều tháng rồi kỳ vọng cây vẫn ra lá đẹp.
- Lấp giá thể quá cao che kín cổ rễ.
Ghi chép nên có
Ghi ngày sang chậu, thành phần giá thể, vị trí đặt cây và chu kỳ khô của chậu để điều chỉnh lịch tưới.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cham-soc-luoi-ho",
            title="Chăm sóc lưỡi hổ: chống úng rễ và giữ dáng lá",
            category="Chăm sóc lưỡi hổ",
            summary="Các bước tưới, vệ sinh lá, xử lý cây mềm gốc và tách bụi lưỡi hổ trong điều kiện nhà phố, văn phòng.",
            content="""
Mục tiêu
Giữ lưỡi hổ đứng lá, sạch bụi và không bị úng rễ. Với cây đô thị, chăm đúng nước quan trọng hơn bón nhiều phân.
Khi nào áp dụng
Áp dụng định kỳ cho chậu lưỡi hổ trong nhà hoặc khi cây có dấu hiệu lá nhăn, mềm gốc, vàng mép hay chậm ra cây con.
Cách làm tại vườn
- Kiểm tra độ khô bằng que gỗ hoặc ngón tay; chỉ tưới khi phần lớn giá thể đã khô.
- Tưới sát gốc, tránh để nước đọng lâu trong bẹ lá; sau tưới phải thấy nước thoát khỏi đáy chậu.
- Lau lá bằng khăn ẩm, không dùng dầu bóng lá nếu cây đặt trong phòng ít gió.
- Khi lá mềm gốc, lấy cây ra khỏi chậu, cắt bỏ rễ thối, để khô vết cắt rồi trồng lại vào giá thể mới thoáng hơn.
- Tách bụi khi cây con chen quá dày; mỗi bụi tách nên có rễ riêng và 2-3 lá khỏe.
Theo dõi sau khi làm
Sau xử lý úng, không tưới ngay quá nhiều. Theo dõi 7-10 ngày để xem lá còn mềm lan rộng hay không. Cây phục hồi tốt thường ngừng vàng và giữ lá cứng trở lại.
Lỗi cần tránh
- Để cây trong chậu sứ kín rồi tưới như cây ngoài trời.
- Bón phân khi rễ đang thối.
- Cắt lá bệnh bằng kéo bẩn rồi dùng tiếp cho cây khỏe.
Ghi chép nên có
Ghi số ngày từ lần tưới trước đến khi giá thể khô. Đây là chỉ số thực tế nhất để chăm lưỡi hổ theo từng căn phòng.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cam-nang-lan-y",
            title="Cẩm nang trồng lan ý trong nhà sáng tán xạ",
            category="Cẩm nang lan ý",
            summary="Cách chuẩn bị chậu, giá thể và ánh sáng cho lan ý, phù hợp căn hộ, văn phòng và khu vực có ánh sáng gián tiếp.",
            content="""
Mục tiêu
Trồng lan ý để cây giữ lá xanh, đứng tán và có điều kiện ra mo hoa. Lan ý ưa ẩm hơn lưỡi hổ, nhưng vẫn cần giá thể thoát nước và không khí lưu thông.
Khi nào áp dụng
Áp dụng khi mua lan ý mới, chuyển cây từ vườn ươm vào căn hộ hoặc thay chậu sau thời gian cây bó rễ.
Cách làm tại vườn
- Chọn cây có lá xanh đều, cuống lá chắc, không có mảng nâu nhũn ở gốc.
- Dùng chậu có lỗ thoát nước; nếu dùng chậu bọc ngoài, phải lấy chậu trồng ra khi tưới.
- Phối giá thể giữ ẩm vừa: đất sạch, xơ dừa đã xử lý, trấu hun và một phần vật liệu thoáng.
- Đặt cây ở nơi sáng tán xạ; tránh nắng trực tiếp buổi trưa vì lá dễ cháy.
- Sau khi đưa cây vào nhà, giữ vị trí ổn định 1-2 tuần để cây thích nghi.
Theo dõi sau khi làm
Lan ý thiếu nước thường rũ lá nhanh nhưng có thể hồi lại sau khi tưới đúng. Nếu lá rũ dù đất còn ướt, cần kiểm tra rễ và thoát nước.
Lỗi cần tránh
- Nghĩ cây rũ là luôn thiếu nước rồi tưới thêm khi giá thể đã ướt.
- Để cây sát máy lạnh hoặc nơi gió nóng thổi trực tiếp.
- Sang chậu quá lớn làm giá thể lâu khô.
Ghi chép nên có
Ghi thời điểm cây rũ lá, độ ẩm giá thể và vị trí đặt cây để phân biệt thiếu nước thật với úng rễ.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cham-soc-lan-y",
            title="Chăm sóc lan ý: giữ ẩm, phục hồi lá rũ và kích cây ra hoa",
            category="Chăm sóc lan ý",
            summary="Quy trình chăm lan ý theo tuần, tập trung vào tưới đúng ngưỡng, tăng ánh sáng tán xạ và xử lý lá cháy mép.",
            content="""
Mục tiêu
Duy trì lan ý khỏe trong nhà, hạn chế lá rũ, cháy mép và thối rễ. Bài này phù hợp cho cây trồng chậu trong căn hộ, sảnh nhỏ và văn phòng.
Khi nào áp dụng
Áp dụng khi cây đã ổn định trong chậu hoặc khi lan ý bắt đầu rũ lá, ít ra lá mới, mép lá nâu hoặc lâu không ra mo hoa.
Cách làm tại vườn
- Kiểm tra mặt giá thể; tưới khi lớp trên se khô nhưng bên dưới vẫn còn ẩm nhẹ.
- Tưới đẫm rồi để ráo, không để nước đọng trong đĩa lót quá lâu.
- Cắt lá già, lá cháy mép bằng kéo sạch để tán thông thoáng.
- Tăng ánh sáng tán xạ nếu cây xanh lá nhưng không ra hoa trong thời gian dài.
- Bón nhẹ bằng phân tan chậm hoặc dinh dưỡng loãng vào giai đoạn cây đang ra lá mới; không bón khi cây đang rũ do úng.
Theo dõi sau khi làm
Sau khi điều chỉnh nước và ánh sáng, theo dõi lá non. Lá non xanh, cuống đứng và ít cháy mép cho thấy cây đã cân bằng hơn.
Lỗi cần tránh
- Phun nước lên lá vào chiều tối trong phòng thiếu gió.
- Đưa cây từ trong nhà ra nắng gắt đột ngột.
- Dùng nước quá nhiều clo hoặc nước đọng lâu có mùi để tưới.
Ghi chép nên có
Ghi ngày tưới, ngày xoay chậu, số lá cháy đã cắt và thay đổi ánh sáng để biết cây phản ứng với điều chỉnh nào.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cam-nang-sen-da",
            title="Cẩm nang trồng sen đá ở ban công và bệ cửa sổ",
            category="Cẩm nang sen đá",
            summary="Hướng dẫn chọn chậu, giá thể khoáng và ánh sáng cho sen đá trong môi trường đô thị nhiều mưa hắt hoặc nắng gắt.",
            content="""
Mục tiêu
Trồng sen đá chắc cây, lên màu đẹp và hạn chế thối gốc. Với sen đá, ba yếu tố quan trọng nhất là nắng, gió và giá thể khô nhanh.
Khi nào áp dụng
Áp dụng khi mua sen đá mới, thay chậu sau vận chuyển, bố trí cây ở ban công, bệ cửa sổ hoặc kệ có đèn trồng cây.
Cách làm tại vườn
- Chọn cây có tâm lá chắc, không dập nước, không có mảng trong suốt ở lá dưới.
- Dùng chậu nông có lỗ thoát nước; chậu đất nung hoặc chậu thoáng khí thường dễ kiểm soát ẩm hơn chậu nhựa kín.
- Phối giá thể khoáng cao: đá pumice, perlite, akadama, sỏi nhẹ hoặc trấu hun; hạn chế đất hữu cơ giữ nước.
- Đặt cây nơi có nắng sáng hoặc ánh sáng mạnh tán xạ; nếu đưa ra nắng trực tiếp, tăng nắng từ từ trong 5-7 ngày.
- Sau khi thay chậu, chờ 2-3 ngày rồi mới tưới để vết rễ ổn định.
Theo dõi sau khi làm
Sen đá đủ sáng thường có tán gọn, lá không vươn dài. Nếu cây cao lên nhanh, lá thưa và màu nhạt, cần tăng sáng hoặc bổ sung đèn.
Lỗi cần tránh
- Tưới lên tâm cây rồi để qua đêm.
- Để cây ngoài mưa nhiều ngày trong chậu giữ nước.
- Chuyển cây từ nơi râm ra nắng gắt ngay lập tức.
Ghi chép nên có
Ghi hướng ban công, số giờ nắng, loại chậu và thời gian giá thể khô sau tưới để chọn vị trí phù hợp.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cham-soc-sen-da",
            title="Chăm sóc sen đá: tưới ít, đủ nắng và xử lý thối gốc",
            category="Chăm sóc sen đá",
            summary="Quy trình chăm sen đá theo mùa, cách tưới an toàn và xử lý sớm khi cây mềm lá, đen gốc hoặc vươn cao thiếu sáng.",
            content="""
Mục tiêu
Giữ sen đá khỏe trong điều kiện đô thị, nhất là ban công mưa hắt, phòng thiếu nắng hoặc khu vực nóng bí gió.
Khi nào áp dụng
Áp dụng định kỳ mỗi tuần hoặc khi cây có dấu hiệu lá mềm, gốc sẫm màu, lá dưới rụng nhiều, cây vươn cao bất thường.
Cách làm tại vườn
- Tưới theo chu kỳ khô của chậu, không tưới theo cảm giác thích cây; khi tưới nên tưới vào giá thể, tránh đọng nước ở tâm.
- Ưu tiên tưới buổi sáng để cây khô trước tối.
- Nhặt lá khô dưới gốc để giảm nơi trú của nấm và rệp.
- Nếu cây thối gốc, cắt phần ngọn còn khỏe, để khô vết cắt rồi giâm lại trên giá thể khô thoáng.
- Khi cây thiếu sáng, tăng sáng từ từ; không đưa ngay ra nắng trưa.
Theo dõi sau khi làm
Sau xử lý thối, không tưới sớm. Theo dõi vết cắt và độ cứng của lá trong 5-7 ngày. Cây ổn sẽ không tiếp tục mềm lan lên phần ngọn.
Lỗi cần tránh
- Xịt nước mỗi ngày vì nghĩ sen đá cần ẩm như cây lá.
- Để chậu quá sát nhau làm thiếu gió.
- Bón phân đậm khiến cây vươn mềm, dễ hỏng khi thiếu sáng.
Ghi chép nên có
Ghi ngày tưới, thời tiết mưa/nắng, vị trí đặt và tình trạng lá. Sau vài tuần sẽ xác định được chu kỳ tưới riêng cho từng ban công.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cam-nang-hoa-giay-ban-cong",
            title="Cẩm nang trồng hoa giấy ban công nhà phố",
            category="Cẩm nang hoa giấy",
            summary="Cách chọn chậu, hướng nắng, giá thể và khung đỡ cho hoa giấy trồng ban công, sân thượng hoặc sân nhỏ đô thị.",
            content="""
Mục tiêu
Thiết lập chậu hoa giấy có tán gọn, nhận đủ nắng và có khả năng ra hoa ổn định trong không gian hẹp. Hoa giấy hợp nơi nhiều nắng và không thích úng kéo dài.
Khi nào áp dụng
Áp dụng khi trồng hoa giấy mới ở ban công, sân thượng, hiên nhà hoặc khi chuyển cây từ chậu nhỏ sang chậu lớn.
Cách làm tại vườn
- Chọn vị trí có nắng trực tiếp tối thiểu vài giờ mỗi ngày; thiếu nắng cây thường nhiều lá, ít hoa.
- Dùng chậu chắc, có lỗ thoát lớn, kê cao đáy chậu để nước thoát nhanh sau mưa.
- Giá thể nên thoát nước tốt nhưng vẫn giữ đủ ẩm cho ngày nóng: đất sạch, trấu hun, xơ dừa xử lý và vật liệu khoáng.
- Cắm khung đỡ hoặc dây dẫn tán ngay từ đầu để cây không bò rối ra lan can.
- Sau khi trồng, cố định gốc và tưới đủ ẩm; tránh bón mạnh ngay khi cây chưa phục hồi rễ.
Theo dõi sau khi làm
Cây ổn định sẽ bật chồi mới và lá dày hơn sau vài tuần. Nếu cây chỉ tốt lá mà ít hoa, cần xem lại nắng, cắt tỉa và chế độ tưới.
Lỗi cần tránh
- Trồng trong chậu quá nhỏ nhưng để tán quá lớn, cây nhanh khô và dễ đổ.
- Đặt nơi thiếu nắng rồi tăng phân để ép hoa.
- Để nước mưa đọng lâu dưới đáy chậu.
Ghi chép nên có
Ghi hướng nắng, số giờ nắng, ngày cắt tỉa và thời điểm cây ra hoa để điều chỉnh lịch chăm theo mùa.
""",
        ),
        _urban_guide(
            now,
            slug="do-thi-cham-soc-hoa-giay-ban-cong",
            title="Chăm sóc hoa giấy ban công: cắt tỉa, tưới nước và kích hoa tự nhiên",
            category="Chăm sóc hoa giấy",
            summary="Quy trình chăm hoa giấy trong chậu đô thị, giúp kiểm soát tán, giảm rụng lá do sốc nước và tăng khả năng ra hoa.",
            content="""
Mục tiêu
Giữ hoa giấy gọn tán, ra hoa đều và không gây vướng ban công. Bài này ưu tiên kỹ thuật tưới, cắt tỉa và kiểm soát sức cây thay vì dùng biện pháp ép quá mạnh.
Khi nào áp dụng
Áp dụng cho hoa giấy đã trồng ổn định trong chậu, cây đang tốt lá nhưng ít hoa, hoặc cây sau một đợt hoa cần phục hồi.
Cách làm tại vườn
- Tưới đẫm rồi để giá thể khô tương đối trước lần tưới tiếp theo; không để cây úng kéo dài.
- Cắt tỉa sau đợt hoa, bỏ cành yếu, cành mọc vào trong và cành vượt quá không gian ban công.
- Dẫn tán theo khung, buộc dây mềm và kiểm tra định kỳ để dây không siết vào cành.
- Khi cây quá tốt lá, giảm tưới nhẹ và tăng nắng thay vì bón thêm đạm.
- Bổ sung dinh dưỡng vừa phải sau cắt tỉa để cây hồi sức trước chu kỳ hoa tiếp theo.
Theo dõi sau khi làm
Quan sát chồi mới và mầm hoa ở đầu cành. Nếu cây héo mạnh hoặc rụng lá nhiều, cần kiểm tra rễ, nhiệt sàn ban công và lượng nước tưới.
Lỗi cần tránh
- Cắt tỉa quá mạnh vào thời điểm cây đang yếu hoặc vừa thay chậu.
- Để cành vươn ra ngoài lan can gây mất an toàn.
- Ép khô kéo dài khiến cây suy, rụng lá và khó phục hồi.
Ghi chép nên có
Ghi ngày cắt tỉa, ngày tưới, thời tiết nắng nóng và thời điểm xuất hiện mầm hoa để xây lịch chăm phù hợp ban công của mình.
""",
        ),
    ]


def _urban_guide(now: datetime, slug: str, title: str, category: str, summary: str, content: str) -> dict:
    return {
        "slug": slug,
        "title": title,
        "crop_type": None,
        "category": category,
        "summary": summary,
        "content": _clean_multiline(content),
        "author": "Dự báo nông sản",
        "published_at": now,
    }


def _clean_multiline(value: str) -> str:
    return "\n".join(line.strip() for line in value.strip().splitlines() if line.strip())


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _strip_html(value: str) -> str:
    soup = BeautifulSoup(value or "", "html.parser")
    for tag in soup(["script", "style", "figure", "img"]):
        tag.decompose()
    return _clean(soup.get_text(" ", strip=True))


def _normalize_ascii(value: str) -> str:
    value = (value or "").replace("đ", "d").replace("Đ", "D")
    no_marks = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", no_marks.lower()).strip()


def _contains_any(value: str, terms: set[str]) -> bool:
    normalized_terms = {_normalize_ascii(term) for term in terms}
    return any(term in value for term in normalized_terms)


def _plant_from_fullname(fullname: str) -> str:
    parts = [part.strip() for part in (fullname or "").split(">") if part.strip()]
    if len(parts) >= 3:
        return parts[-2]
    if len(parts) >= 2 and parts[-1] in HAINONG_GUIDE_SECTIONS:
        return parts[0]
    return parts[-1] if parts else "Cây trồng"


def _plant_from_title(title: str) -> str:
    normalized = _normalize_ascii(title)
    title_map = {
        "ot": "Ớt",
        "lua": "Lúa",
        "ca phe": "Cà phê",
        "sau rieng": "Sầu riêng",
        "xoai": "Xoài",
        "cam": "Cam",
        "mit": "Mít",
        "thanh long": "Thanh long",
        "tieu": "Tiêu",
    }
    for key, label in title_map.items():
        if _has_normalized_term(normalized, {key}):
            return label
    return "Cây trồng"


def _crop_key(plant: str) -> str | None:
    normalized = _normalize_ascii(plant).replace(" ", "_")
    mapping = {
        "sau_rieng": "sau_rieng",
        "ca_phe": "ca_phe",
        "lua": "lua",
        "mit": "mit",
        "thanh_long": "thanh_long",
        "tieu": "ho_tieu",
        "ho_tieu": "ho_tieu",
        "cam": "cam",
        "xoai": "xoai",
        "chom_chom": "chom_chom",
    }
    return mapping.get(normalized, None)


def _slugify(value: str) -> str:
    normalized = _normalize_ascii(value)
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "bai-viet-ky-thuat"


def _guide_category(section: str, plant: str) -> str:
    if section == "Chăm sóc":
        return f"Chăm sóc {plant.lower()}"
    return f"Cẩm nang {plant.lower()}"


def _guide_title(title: str, plant: str) -> str:
    title = title.strip()
    if _mentions_plant(title, plant):
        return title
    return f"{title} cho {plant.lower()}"


def _guide_summary(title: str, plant: str) -> str:
    normalized = _normalize_ascii(title)
    if _has_normalized_term(normalized, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return f"Hướng dẫn nhận diện sớm, khoanh vùng và xử lý dịch hại trên {plant.lower()} theo hướng quản lý tổng hợp."
    if _has_normalized_term(normalized, {"tuoi", "nuoc", "han", "man"}):
        return f"Khung chăm sóc nước cho {plant.lower()}, giúp giữ ổn định sinh trưởng và giảm rủi ro trong giai đoạn thời tiết bất lợi."
    if _has_normalized_term(normalized, {"giong", "dat", "trong", "gieo", "u hat", "tai canh"}):
        return f"Các điểm cần kiểm tra trước khi trồng hoặc tái canh {plant.lower()}, từ giống, đất, mật độ đến quản lý lô vườn."
    if _has_normalized_term(normalized, {"tia", "tao tan", "thu phan", "ra hoa", "thu hoach"}):
        return f"Kỹ thuật thao tác trên tán, hoa, trái và thời điểm thu hoạch để vườn {plant.lower()} vận hành đồng đều hơn."
    return f"Bài hướng dẫn kỹ thuật cho {plant.lower()}, được biên tập lại thành các bước thực hành ngắn gọn để dùng tại vườn."


def _technical_guide_content(
    title: str,
    plant: str,
    source_url: str,
    source_text: str,
    image_urls: list[str] | None = None,
) -> str:
    normalized = _normalize_ascii(title)
    points = _guide_points(normalized, plant)
    field_note = _field_note_from_source(source_text)
    topic = title.strip() if _mentions_plant(title, plant) else f"{title.strip()} trên {plant.lower()}"
    when_to_apply = _when_to_apply(normalized, plant)
    follow_up = _follow_up_plan(normalized, plant)
    mistakes = _common_mistakes(normalized, plant)
    image_lines = [f"IMAGE::{url}" for url in (image_urls or [])[:3]]
    sections = [
        "Mục tiêu",
        f"Bài này giúp người trồng nắm nhanh cách xử lý chủ đề {topic.lower()}, tránh làm theo cảm tính và có cơ sở để kiểm tra lại hiệu quả sau khi áp dụng.",
        *image_lines,
        "Khi nào áp dụng",
        when_to_apply,
        "Cách làm tại vườn",
        *[f"- {point}" for point in points],
        "Theo dõi sau khi làm",
        follow_up,
        "Lỗi cần tránh",
        *[f"- {mistake}" for mistake in mistakes],
        "Ghi chép nên có",
        f"Ghi lại ngày thực hiện, lô vườn/ruộng, tình trạng cây trước khi xử lý, thao tác đã làm và kết quả sau 3-7 ngày. {field_note}",
    ]
    return "\n".join(sections)


def _extract_hainong_images(article: dict) -> list[str]:
    urls: list[str] = []
    main_image = article.get("image")
    if main_image:
        urls.append(str(main_image))
    soup = BeautifulSoup(article.get("content", "") or "", "html.parser")
    for image in soup.find_all("img"):
        src = image.get("src") or image.get("data-src")
        if src:
            urls.append(str(src))
    clean_urls = []
    seen = set()
    for url in urls:
        if not url.startswith(("http://", "https://")):
            continue
        if _is_excluded_guide_image(url):
            continue
        if url in seen:
            continue
        clean_urls.append(url)
        seen.add(url)
    return clean_urls


def _is_excluded_guide_image(url: str) -> bool:
    normalized = _normalize_ascii(url).lower()
    return any(term in normalized for term in HAINONG_EXCLUDED_IMAGE_TERMS)


def _mentions_plant(title: str, plant: str) -> bool:
    return _has_normalized_term(_normalize_ascii(title), {_normalize_ascii(plant)})


def _guide_points(normalized_title: str, plant: str) -> list[str]:
    plant_name = plant.lower()
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return [
            f"Đi thăm vườn/ruộng {plant_name} theo lô, ưu tiên khu vực ẩm thấp, tán rậm hoặc có cây suy yếu.",
            "Ghi lại triệu chứng, mật số và phạm vi xuất hiện trước khi quyết định xử lý.",
            "Kết hợp vệ sinh đồng ruộng, cắt bỏ bộ phận bệnh, quản lý nước và dùng thuốc đúng ngưỡng khi thật sự cần.",
            "Sau xử lý 3-5 ngày cần kiểm tra lại để đánh giá hiệu lực và tránh phun lặp không cần thiết.",
        ]
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        return [
            f"Kiểm tra ẩm độ đất quanh vùng rễ {plant_name} trước khi tưới, tránh tưới theo lịch cứng.",
            "Ưu tiên tưới chậm, đủ ẩm tầng rễ hoạt động và thoát nước nhanh sau mưa lớn.",
            "Trong hạn hoặc mặn, giữ tán cân bằng, giảm stress cho cây và theo dõi lá non sau mỗi đợt thời tiết cực đoan.",
            "Ghi nhật ký lượng nước, ngày tưới và phản ứng của cây để điều chỉnh cho các đợt sau.",
        ]
    if _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        return [
            f"Chọn giống {plant_name} khỏe, đúng nguồn gốc và loại bỏ cây có dấu hiệu sâu bệnh hoặc rễ yếu.",
            "Chuẩn bị đất/hố trồng thông thoáng, chủ động thoát nước và xử lý tàn dư cây bệnh trước khi xuống giống.",
            "Bố trí mật độ phù hợp để thuận tiện chăm sóc, phun tưới, thu hoạch và giảm áp lực sâu bệnh.",
            "Theo dõi cây sau trồng theo từng tuần, đặc biệt là bật chồi, rễ mới và tỷ lệ cây cần thay thế.",
        ]
    if _has_normalized_term(normalized_title, {"tia", "tao tan", "thu phan", "ra hoa", "thap den"}):
        return [
            f"Đánh giá sức cây {plant_name} trước khi xử lý ra hoa, tỉa cành hoặc tác động lên tán.",
            "Giữ tán thông thoáng, loại bỏ cành sâu bệnh, cành khuất sáng và phần sinh trưởng cạnh tranh.",
            "Khi xử lý hoa/trái, làm theo từng đợt nhỏ để cây không bị sốc và dễ theo dõi tỷ lệ đậu.",
            "Sau thao tác cần kiểm tra sâu bệnh, nước tưới và tình trạng lá để kịp thời điều chỉnh.",
        ]
    if _has_normalized_term(normalized_title, {"co dai", "ipm", "1 phai 5 giam"}):
        return [
            f"Chia khu sản xuất {plant_name} thành lô để theo dõi cỏ dại, dịch hại và chi phí theo từng giai đoạn.",
            "Ưu tiên biện pháp canh tác, vệ sinh đồng ruộng và quản lý nước trước khi dùng hóa chất.",
            "Khi cần xử lý, chọn đúng thời điểm, đúng đối tượng và ghi lại hiệu quả sau mỗi lần thực hiện.",
            "Duy trì nhật ký canh tác để so sánh chi phí, năng suất và rủi ro giữa các vụ.",
        ]
    if "thu hoach" in normalized_title:
        return [
            f"Xác định độ chín hoặc thời điểm thu hoạch {plant_name} theo giống, thị trường và mục tiêu chất lượng.",
            "Chuẩn bị nhân công, dụng cụ sạch và khu tập kết để giảm dập nát, lẫn tạp và thất thoát sau thu hoạch.",
            "Phân loại ngay tại vườn/ruộng, tách sản phẩm lỗi để tránh ảnh hưởng đến lô hàng chính.",
            "Ghi lại sản lượng, tỷ lệ loại bỏ và giá bán để phục vụ quyết định vụ sau.",
        ]
    return [
        f"Quan sát tình trạng sinh trưởng của {plant_name} trước khi áp dụng kỹ thuật.",
        "Xác định đúng giai đoạn mùa vụ, điều kiện đất nước và mức độ rủi ro sâu bệnh.",
        "Thực hiện từng bước nhỏ, có ghi nhật ký để dễ đánh giá hiệu quả.",
        "Theo dõi lại sau xử lý và điều chỉnh theo phản ứng thực tế của cây.",
    ]


def _when_to_apply(normalized_title: str, plant: str) -> str:
    plant_name = plant.lower()
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return f"Áp dụng khi vườn/ruộng {plant_name} bắt đầu có dấu hiệu bất thường, mật số dịch hại tăng hoặc thời tiết chuyển sang giai đoạn dễ phát sinh bệnh. Không nên chờ đến khi cả lô bị nặng mới xử lý."
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        return f"Áp dụng trong giai đoạn khô nóng, mưa thất thường, hạn mặn hoặc khi {plant_name} có biểu hiện thiếu nước như lá rũ, chồi non chậm phát triển, đất mặt khô nhanh."
    if _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        return f"Áp dụng trước khi xuống giống, tái canh hoặc mở lô mới. Đây là bước nên làm kỹ vì sai từ khâu đất, giống hoặc mật độ thường rất khó sửa về sau."
    if _has_normalized_term(normalized_title, {"tia", "tao tan", "thu phan", "ra hoa", "thap den", "buoc day"}):
        return f"Áp dụng khi {plant_name} bước vào giai đoạn cần điều chỉnh tán, xử lý ra hoa, nuôi trái hoặc giữ bộ khung ổn định để tiện chăm sóc và thu hoạch."
    if _has_normalized_term(normalized_title, {"thu hoach"}):
        return f"Áp dụng trước và trong thời điểm thu hoạch, đặc biệt khi cần giữ chất lượng lô hàng đồng đều, giảm thất thoát và chuẩn bị bán theo đơn đặt trước."
    return f"Áp dụng khi cần chuẩn hóa thao tác canh tác trên {plant_name}, nhất là với lô mới, lô đang phục hồi hoặc lô có biến động sinh trưởng không đồng đều."


def _follow_up_plan(normalized_title: str, plant: str) -> str:
    plant_name = plant.lower()
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return f"Sau khi xử lý, quay lại cùng vị trí đã kiểm tra ban đầu để so sánh mật số, vết bệnh và sức cây. Với {plant_name}, nên ưu tiên đánh giá xu hướng giảm/tăng của triệu chứng thay vì chỉ nhìn một cây riêng lẻ."
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        return f"Kiểm tra ẩm đất ở tầng rễ, màu lá, độ bật chồi và tình trạng rụng hoa/trái non. Nếu {plant_name} phục hồi chậm, giảm tác động mạnh lên cây và điều chỉnh lượng nước theo từng lô."
    if _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        return f"Theo dõi tỷ lệ sống, rễ mới, chồi mới và cây chậm phát triển trong 2-4 tuần đầu. Những điểm yếu của lô {plant_name} cần được đánh dấu sớm để dặm cây hoặc cải tạo cục bộ."
    if _has_normalized_term(normalized_title, {"tia", "tao tan", "thu phan", "ra hoa", "thap den", "buoc day"}):
        return f"Quan sát phản ứng của tán, lá non, hoa và trái sau mỗi lần thao tác. Nếu {plant_name} có dấu hiệu sốc, nên giãn lịch xử lý và ưu tiên ổn định nước, ánh sáng, thông thoáng."
    return f"Sau mỗi thao tác, nên có một lần kiểm tra ngắn để xem {plant_name} phản ứng thế nào. Cách làm nào cho kết quả tốt cần được ghi lại thành quy trình riêng của trang trại."


def _common_mistakes(normalized_title: str, plant: str) -> list[str]:
    plant_name = plant.lower()
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return [
            "Chỉ xử lý phần thấy rõ triệu chứng mà bỏ qua nguồn lây ở tàn dư, cỏ dại, nước tưới hoặc cây sát bên.",
            "Phun/xử lý lặp lại quá nhanh khi chưa kiểm tra hiệu quả thực tế.",
            "Không ghi vị trí phát sinh nên lần sau khó biết bệnh đang lan hay đã được khống chế.",
        ]
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        return [
            "Tưới nhiều một lần để bù thiếu nước, làm rễ bị sốc hoặc đất bí.",
            "Không kiểm tra thoát nước sau mưa lớn, khiến rễ yếu và bệnh đất dễ bùng lên.",
            f"Áp dụng cùng một lịch tưới cho mọi lô {plant_name} dù đất, tuổi cây và tán cây khác nhau.",
        ]
    if _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        return [
            "Chọn giống theo giá rẻ hoặc nguồn quen biết mà bỏ qua sức cây, rễ và hồ sơ giống.",
            "Xuống giống khi đất chưa ổn định nước hoặc còn tồn dư cây bệnh.",
            "Trồng quá dày, về sau tốn công tỉa sửa và tăng áp lực sâu bệnh.",
        ]
    if _has_normalized_term(normalized_title, {"tia", "tao tan", "thu phan", "ra hoa", "thap den", "buoc day"}):
        return [
            "Làm quá mạnh trong một lần, khiến cây mất cân bằng tán hoặc rụng hoa/trái non.",
            "Không khử vệ sinh dụng cụ khi cắt tỉa trên lô có dấu hiệu bệnh.",
            f"Chỉ nhìn một vài cây khỏe rồi áp dụng chung cho cả vườn {plant_name}.",
        ]
    return [
        "Làm theo kinh nghiệm truyền miệng mà không kiểm tra điều kiện cụ thể của lô.",
        "Không ghi lại kết quả, khiến vụ sau phải thử lại từ đầu.",
        f"Áp dụng đồng loạt trên diện tích lớn trước khi thử ở một phần nhỏ của lô {plant_name}.",
    ]


def _has_normalized_term(value: str, terms: set[str]) -> bool:
    for term in terms:
        escaped = re.escape(term)
        if " " in term:
            pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
        else:
            pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
        if re.search(pattern, value):
            return True
    return False


def _guide_needs_depth_upgrade(content: str | None) -> bool:
    text = content or ""
    return len(text.split()) < GUIDE_TARGET_MIN_WORDS or GUIDE_DEPTH_MARKER not in text


def _guide_plant_label(row: GuidePost) -> str:
    crop_map = {
        "sau_rieng": "Sầu riêng",
        "ca_phe": "Cà phê",
        "lua": "Lúa",
        "ho_tieu": "Hồ tiêu",
        "mit": "Mít",
        "thanh_long": "Thanh long",
        "cam": "Cam",
        "xoai": "Xoài",
        "chom_chom": "Chôm chôm",
    }
    if row.crop_type in crop_map:
        return crop_map[row.crop_type]
    plant = _plant_from_title(f"{row.title} {row.category} {row.summary}")
    return plant if plant != "Cây trồng" else "Cây trồng"


def _technical_guide_content(
    title: str,
    plant: str,
    source_url: str,
    source_text: str,
    image_urls: list[str] | None = None,
) -> str:
    image_lines = [f"IMAGE::{url}" for url in (image_urls or [])[:3]]
    return _expanded_guide_content(
        title=title,
        plant=plant,
        summary=_guide_summary(title, plant),
        existing_content="\n".join([*image_lines, source_text or ""]),
        source_text=source_text,
        source_url=source_url,
    )


def _expanded_guide_content(
    title: str,
    plant: str,
    summary: str,
    existing_content: str | None = None,
    source_text: str | None = None,
    source_url: str | None = None,
) -> str:
    normalized = _normalize_ascii(f"{title} {summary}")
    plant_name = plant.lower()
    topic = title.strip() if _mentions_plant(title, plant) else f"{title.strip()} cho {plant_name}"
    image_lines = _preserved_image_lines(existing_content)
    field_note = _field_note_from_source(source_text or existing_content or "")
    sections = [
        "Mục tiêu thực hành",
        (
            f"Bài này hướng dẫn người trồng triển khai chủ đề {topic.lower()} theo dạng quy trình có thể làm ngay tại vườn. "
            f"Trọng tâm không chỉ là biết nên làm gì, mà còn biết làm lúc nào, kiểm tra bằng dấu hiệu nào và khi nào cần dừng để tránh làm cây bị sốc. "
            f"{summary.strip()}"
        ),
        *image_lines,
        "Khi nào áp dụng",
        _when_to_apply(normalized, plant),
        "Chuẩn bị trước khi làm",
        *[f"- {point}" for point in _preparation_points(normalized, plant)],
        "Quy trình làm tại vườn",
        *[f"- {point}" for point in _execution_steps(normalized, plant)],
        GUIDE_DEPTH_MARKER,
        *[f"- {point}" for point in _checkpoints(normalized, plant)],
        "Lịch theo dõi sau khi làm",
        *[f"- {point}" for point in _follow_up_schedule(normalized, plant)],
        "Lỗi thường gặp và cách sửa",
        *[f"- {point}" for point in _common_mistakes(normalized, plant)],
        "Vật tư và dụng cụ nên chuẩn bị",
        *[f"- {point}" for point in _supply_points(normalized, plant)],
        "Ghi chép bắt buộc",
        (
            f"Ghi ngày thực hiện, lô vườn/ruộng, tuổi cây, giống, tình trạng trước khi làm, thao tác đã thực hiện, vật tư đã dùng và kết quả sau 3-7 ngày. "
            f"Với {plant_name}, nên chụp cùng một góc trước và sau xử lý để so sánh màu lá, tán, rễ, hoa hoặc trái. "
            f"{field_note}"
        ),
        "Khi nào cần dừng và hỏi kỹ thuật viên",
        (
            "Dừng mở rộng ra toàn bộ diện tích nếu cây héo nhanh, rụng hoa/trái non nhiều, vết bệnh lan nhanh, rễ có mùi hôi hoặc đất bị úng kéo dài. "
            "Trong trường hợp phải dùng thuốc bảo vệ thực vật, chỉ dùng sản phẩm còn được phép lưu hành, đúng đối tượng, đúng thời gian cách ly và theo hướng dẫn trên nhãn hoặc khuyến cáo địa phương."
        ),
    ]
    if source_url:
        sections.extend(
            [
                "Ghi chú nguồn tham khảo",
                f"Nội dung được biên tập thành quy trình thực hành riêng cho Dự báo nông sản; không thay thế khuyến cáo chính thức tại địa phương. Tham khảo thêm: {source_url}",
            ]
        )
    return "\n".join(sections)


def _preserved_image_lines(content: str | None) -> list[str]:
    lines = []
    for line in (content or "").splitlines():
        line = line.strip()
        if line.startswith("IMAGE::") and line.removeprefix("IMAGE::").strip() and line not in lines:
            lines.append(line)
        if len(lines) >= 3:
            break
    return lines


def _preparation_points(normalized_title: str, plant: str) -> list[str]:
    plant_name = plant.lower()
    points = [
        f"Chia khu {plant_name} thành từng lô nhỏ để kiểm tra; không đánh giá cả vườn bằng một vài cây ở mép đường hoặc gần nguồn nước.",
        "Chuẩn bị sổ ghi chép, điện thoại chụp ảnh, thước đo hoặc que đánh dấu vị trí để quay lại đúng điểm kiểm tra sau xử lý.",
        "Kiểm tra thời tiết 3-5 ngày tới; tránh thao tác mạnh ngay trước mưa lớn, nắng gắt kéo dài hoặc giai đoạn cây đang suy rõ.",
    ]
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        points.extend(
            [
                "Đánh dấu cây bị nặng, cây mới chớm và cây khỏe để so sánh; cách này giúp biết biện pháp đang chặn được bệnh hay chỉ làm sạch phần nhìn thấy.",
                "Vệ sinh dụng cụ cắt tỉa, chuẩn bị bao thu gom bộ phận bệnh và tránh kéo mầm bệnh từ lô này sang lô khác.",
            ]
        )
    elif _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        points.extend(
            [
                "Kiểm tra nguồn giống, bầu rễ, cổ rễ và dấu hiệu sâu bệnh trước khi đưa cây ra ruộng/vườn.",
                "Đào thử một vài điểm để xem tầng đất, độ thoát nước và tàn dư rễ cũ; không xuống giống đại trà khi đất còn úng hoặc còn nguồn bệnh rõ.",
            ]
        )
    elif _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        points.extend(
            [
                "Kiểm tra ẩm độ ở tầng rễ hoạt động thay vì chỉ nhìn mặt đất; mặt đất khô chưa chắc tầng rễ đã thiếu nước.",
                "Dọn thông rãnh thoát, điểm gom nước và khu vực quanh gốc trước khi tưới hoặc trước đợt mưa lớn.",
            ]
        )
    else:
        points.extend(
            [
                "Chọn một lô nhỏ để làm trước, ghi kết quả rồi mới mở rộng; cách này giảm rủi ro khi điều kiện vườn không đồng đều.",
                "Tra lại lịch bón phân, tưới nước, phun thuốc và thời điểm ra hoa/thu hoạch gần nhất để tránh thao tác chồng chéo.",
            ]
        )
    return points


def _execution_steps(normalized_title: str, plant: str) -> list[str]:
    base = _guide_points(normalized_title, plant)
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return [
            *base,
            "Xử lý theo thứ tự: khoanh vùng, vệ sinh nguồn bệnh, điều chỉnh nước/tán/cỏ dại, sau đó mới cân nhắc biện pháp hóa học khi mật số hoặc tốc độ lan vượt ngưỡng chịu đựng.",
            "Không trộn nhiều loại thuốc hoặc tăng liều theo cảm tính; nếu cần dùng thuốc, chọn hoạt chất đúng đối tượng, luân phiên nhóm tác động và tuân thủ thời gian cách ly.",
            "Sau xử lý, giữ lại một vài điểm đối chứng nhỏ nếu an toàn để biết biện pháp nào thực sự có hiệu quả trong điều kiện vườn của mình.",
        ]
    if _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        return [
            *base,
            "Làm đất/hố theo hướng thoát nước trước, dinh dưỡng sau; cây lâu năm chết nhiều trong năm đầu thường do úng, rễ yếu hoặc đất chưa ổn định hơn là thiếu phân.",
            "Xuống giống vào thời điểm đất đủ ẩm nhưng không sũng nước; sau trồng cần che nắng, cố định cây và kiểm tra nghiêng đổ sau mưa gió.",
            "Dặm cây sớm khi cây chết hoặc chậm phát triển rõ, tránh để khoảng trống lâu làm vườn không đồng đều về sau.",
        ]
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        return [
            *base,
            "Tưới chậm để nước thấm vào vùng rễ, tránh tưới mạnh làm trôi mặt đất hoặc tạo vũng quanh cổ rễ.",
            "Khi gặp mặn hoặc hạn, ưu tiên giữ ẩm ổn định, che phủ và giảm thao tác gây sốc; không ép cây ra đọt/ra hoa khi nền nước chưa ổn.",
            "Sau mưa lớn, kiểm tra thoát nước ngay trong 24 giờ đầu vì nhiều bệnh rễ bùng lên từ giai đoạn đất bí khí kéo dài.",
        ]
    if _has_normalized_term(normalized_title, {"tia", "tao tan", "thu phan", "ra hoa", "thap den", "buoc day"}):
        return [
            *base,
            "Làm từng lượt nhẹ, ưu tiên phần bệnh, phần khuất sáng hoặc phần cạnh tranh rõ; không thay đổi quá mạnh bộ tán trong một lần.",
            "Với thao tác liên quan hoa/trái, ghi ngày bắt đầu, tỷ lệ đậu và vị trí cành mang trái để quyết định giữ hay tỉa ở đợt sau.",
            "Dụng cụ cắt, buộc, thụ phấn hoặc đỡ trái cần sạch và thao tác dứt khoát để giảm vết thương không cần thiết.",
        ]
    if _has_normalized_term(normalized_title, {"thu hoach"}):
        return [
            *base,
            "Lên lịch thu theo lô và theo độ chín, không gom tất cả về một ngày nếu nhân công, điểm tập kết hoặc xe vận chuyển chưa sẵn.",
            "Phân loại ngay tại vườn/ruộng theo kích cỡ, độ chín, lỗi cơ học và lỗi sâu bệnh để tránh làm giảm giá cả lô hàng.",
            "Ghi sản lượng theo từng lô để mùa sau biết lô nào cần cải tạo đất, nước, giống hoặc quy trình chăm sóc.",
        ]
    return [
        *base,
        "Thực hiện theo thứ tự quan sát - xử lý nhỏ - theo dõi - mở rộng; tránh làm đồng loạt khi chưa biết phản ứng của cây.",
        "Nếu có nhiều cách làm, chỉ thay đổi một yếu tố chính trong mỗi lần thử để biết nguyên nhân tạo ra kết quả.",
        "Luôn giữ một khoảng thời gian theo dõi sau thao tác trước khi bón/phun/tưới thêm, vì cây cần thời gian phản ứng.",
    ]


def _checkpoints(normalized_title: str, plant: str) -> list[str]:
    plant_name = plant.lower()
    if _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        return [
            "Tỷ lệ cây có triệu chứng mới phải giảm hoặc ít nhất không lan nhanh sau 3-7 ngày.",
            "Vết bệnh cũ có thể chưa mất ngay, nhưng mép vết bệnh không nên tiếp tục mở rộng mạnh.",
            "Mật số sâu/rệp/mọt ở điểm đánh dấu phải giảm rõ so với trước xử lý; nếu không giảm, cần xem lại đúng đối tượng và cách phun/xử lý.",
            f"Cây {plant_name} không được héo thêm, cháy lá hoặc rụng hoa/trái non bất thường sau khi can thiệp.",
        ]
    if _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        return [
            "Sau 7-14 ngày, cây phải đứng vững, lá không héo kéo dài và bầu rễ không bị úng/thối.",
            "Tỷ lệ cây chết hoặc chậm phát triển cần được ghi theo lô; nếu tập trung ở một vùng, ưu tiên kiểm tra đất và nước tại vùng đó.",
            "Cây mới trồng không nên bị nắng táp, gió lay mạnh hoặc đọng nước quanh cổ rễ.",
            "Nếu lô có trên một nhóm cây xấu giống nhau, chưa vội bón thêm phân mà kiểm tra rễ, đất và nguồn giống trước.",
        ]
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        return [
            "Đất vùng rễ đủ ẩm nhưng không bết dính, không có mùi yếm khí và không đọng nước lâu quanh gốc.",
            "Lá phục hồi độ căng trong ngày mát; nếu vẫn rũ sau tưới, cần kiểm tra rễ hoặc bệnh đất.",
            "Đọt non/hoa/trái non không rụng tăng bất thường sau thay đổi lịch tưới.",
            "Rãnh thoát hoạt động tốt sau mưa, không để nước đứng quá lâu ở vùng rễ.",
        ]
    return [
        f"Cây {plant_name} giữ màu lá ổn định, không xuất hiện triệu chứng sốc mới sau thao tác.",
        "Kết quả phải đo được bằng số liệu đơn giản: tỷ lệ cây đạt, tỷ lệ bệnh, số trái giữ lại, sản lượng hoặc chi phí theo lô.",
        "Nếu kết quả khác nhau giữa các lô, ưu tiên tìm nguyên nhân ở đất, nước, tuổi cây, giống và lịch chăm sóc trước đó.",
        "Chỉ mở rộng quy trình khi lô thử nghiệm cho kết quả ổn định qua ít nhất một lần kiểm tra lại.",
    ]


def _follow_up_schedule(normalized_title: str, plant: str) -> list[str]:
    plant_name = plant.lower()
    return [
        "Sau 24 giờ: kiểm tra nhanh dấu hiệu sốc, úng, héo, cháy lá hoặc tổn thương cơ học do thao tác.",
        "Sau 3-5 ngày: quay lại đúng điểm đã chụp ảnh ban đầu, so sánh triệu chứng, màu lá, độ ẩm đất và mức lan của vấn đề.",
        "Sau 7-14 ngày: đánh giá hiệu quả bằng số liệu theo lô; nếu chưa đạt, điều chỉnh nguyên nhân chính thay vì làm thêm nhiều biện pháp cùng lúc.",
        f"Cuối tháng hoặc cuối giai đoạn: tổng hợp chi phí, công lao động và kết quả để biến kinh nghiệm trên {plant_name} thành quy trình riêng của trang trại.",
    ]


def _supply_points(normalized_title: str, plant: str) -> list[str]:
    supplies = [
        "Sổ hoặc file ghi chép lô vườn, điện thoại chụp ảnh, bút đánh dấu và thẻ ghi ngày xử lý.",
        "Dụng cụ vệ sinh, kéo/cưa/túi thu gom tàn dư nếu có thao tác cắt tỉa hoặc loại bỏ bộ phận bệnh.",
        "Đồ bảo hộ cá nhân khi tiếp xúc đất, phân, thuốc hoặc vật tư có nguy cơ kích ứng.",
    ]
    if _has_normalized_term(normalized_title, {"tuoi", "nuoc", "han", "man"}):
        supplies.append("Dụng cụ kiểm tra ẩm đất đơn giản hoặc que thăm đất, vật liệu che phủ sạch và dụng cụ khơi rãnh thoát nước.")
    elif _has_normalized_term(normalized_title, {"giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong"}):
        supplies.append("Cây giống/giống có nguồn rõ, vật liệu cố định cây, vật liệu che nắng tạm thời và dụng cụ kiểm tra rễ/bầu.")
    elif _has_normalized_term(normalized_title, {"phong tru", "benh", "rep", "ray", "mot", "oc", "chuot"}):
        supplies.append("Kính lúp cầm tay nếu có, túi mẫu bệnh, bẫy/biện pháp cơ học phù hợp và danh sách thuốc được phép dùng tại địa phương.")
    else:
        supplies.append("Bản đồ lô hoặc sơ đồ vườn để đánh dấu vị trí đã xử lý và vị trí cần kiểm tra lại.")
    return supplies


def _field_note_from_source(source_text: str) -> str:
    if len(source_text) < 80:
        return "Một số bài nguồn chủ yếu là hình ảnh, vì vậy nên đối chiếu thêm tài liệu địa phương trước khi áp dụng đại trà."
    if len(source_text) > 1200:
        return "Bài nguồn có nhiều chi tiết kỹ thuật; khi triển khai nên thử trên một lô nhỏ, ghi kết quả rồi mới mở rộng."
    return "Nội dung đã được biên tập lại theo hướng thực hành; cần điều chỉnh theo giống, đất, thời tiết và khuyến cáo địa phương."


def _looks_like_article(url: str) -> bool:
    return _is_article_url(url)


def _is_article_url(url: str) -> bool:
    lowered = url.lower()
    if any(token in lowered for token in ("tag", "danh-sach", "chuyen-muc", "category")):
        return False
    if lowered.endswith(("/", "#")):
        return False
    return lowered.endswith((".htm", ".html")) or bool(re.search(r"-d\d+(?:\.html?)?$", lowered))


def _is_supported_news_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return not host.endswith("botruong.mae.gov.vn")


def _is_vietnamese_text(value: str) -> bool:
    vietnamese_marks = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    value_lower = value.lower()
    return any(mark in value_lower for mark in vietnamese_marks)


def _is_relevant_market_news(value: str) -> bool:
    normalized = _normalize_ascii(value)
    if _is_off_topic_news(normalized):
        return False
    if not _has_normalized_term(normalized, AGRI_NEWS_KEYWORDS):
        return False
    return _news_relevance_score(normalized) >= 3


def _human_summary(value: str) -> str:
    cleaned = _clean(value)
    cleaned = re.sub(r"^\s*\d{1,2}[:h]\d{2}\s+", "", cleaned)
    cleaned = re.sub(r"^(Thị trường|Kinh tế|Tin tức)\s+\d{1,2}/\d{1,2}/\d{4}\s+-\s+", "", cleaned)
    cleaned = re.sub(r"\s+(Thị trường|Kinh tế|Tin tức)\s+\d{1,2}/\d{1,2}/\d{4}\s+-\s+", " ", cleaned)
    cleaned = re.sub(r"\s+Xem thêm.*$", "", cleaned)
    return cleaned


def _compact_news_title(value: str, limit: int = 118) -> str:
    cleaned = _human_summary(value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–|")
    if not cleaned:
        return ""

    words = cleaned.split()
    if len(words) >= 8:
        prefix = " ".join(words[:4])
        repeated_at = cleaned.find(prefix, len(prefix) + 1)
        if repeated_at > 36:
            cleaned = cleaned[:repeated_at].strip(" -–,.;:")

    for marker in (
        " Đây là ",
        " Với vai trò ",
        " Trong giai đoạn ",
        " Theo đó ",
        " Bên cạnh đó ",
        " Quý I/",
        " Việt Nam và ",
    ):
        marker_at = cleaned.find(marker)
        if marker_at > 46:
            cleaned = cleaned[:marker_at].strip(" -–,.;:")
            break

    return _truncate_words(cleaned, limit)


def _summary_without_title(summary: str, title: str) -> str:
    cleaned = _human_summary(summary)
    if title and cleaned.startswith(title):
        cleaned = cleaned[len(title) :].strip(" -–:,.")
    if not cleaned or cleaned == title:
        return title
    return cleaned


def _truncate_words(value: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", _clean(value)).strip()
    if len(cleaned) <= limit:
        return cleaned
    clipped = cleaned[:limit].rsplit(" ", 1)[0].strip(" -–,.;:")
    return clipped or cleaned[:limit].strip(" -–,.;:")


def _nearby_text(link) -> str:
    parent = link.find_parent(["article", "li", "div"]) or link.parent
    return parent.get_text(" ", strip=True) if parent else link.get_text(" ", strip=True)


def _nearby_image(link, base_url: str) -> str | None:
    parent = link.find_parent(["article", "li", "div"]) or link.parent
    image = parent.find("img") if parent else None
    if not image:
        return None
    src = image.get("src") or image.get("data-src")
    return _clean_image_url(urljoin(base_url, src)) if src else None


def _listing_urls(source: dict) -> list[str]:
    base_url = source["url"]
    pages = max(1, int(source.get("pages", 1)))
    urls = [base_url]
    if pages <= 1:
        return urls
    base = base_url.rstrip("/")
    urls.extend(f"{base}/p{page}" for page in range(2, pages + 1))
    return urls


def _article_meta_image(url: str) -> str | None:
    return _article_metadata(url)[1]


def _article_published_at(url: str) -> datetime | None:
    return _article_metadata(url)[0]


def _article_metadata(url: str) -> tuple[datetime | None, str | None]:
    if not url.startswith(("http://", "https://")):
        return None, None
    try:
        response = requests.get(
            url,
            timeout=NEWS_HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": "Mozilla/5.0 MarketAI/1.0"},
        )
        response.raise_for_status()
    except Exception:
        return None, None
    soup = BeautifulSoup(response.text, "html.parser")
    published_at = None
    for attrs in (
        {"property": "article:published_time"},
        {"name": "article:published_time"},
        {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attrs)
        published_at = _parse_iso_datetime(tag.get("content") if tag else None)
        if published_at:
            break
    if published_at is None:
        published_at = _parse_date(soup.get_text(" ", strip=True)[:600])

    image_url = None
    for attrs in (
        {"property": "og:image"},
        {"property": "og:image:url"},
        {"name": "twitter:image"},
        {"name": "twitter:image:src"},
    ):
        tag = soup.find("meta", attrs=attrs)
        content = tag.get("content") if tag else None
        cleaned = _clean_image_url(urljoin(url, content)) if content else None
        if cleaned:
            image_url = cleaned
            break
    if image_url is None:
        image = soup.find("img")
        src = image.get("src") or image.get("data-src") if image else None
        image_url = _clean_image_url(urljoin(url, src)) if src else None
    return published_at, image_url


def _clean_image_url(url: str) -> str | None:
    cleaned = (url or "").strip()
    if not cleaned.startswith(("http://", "https://")):
        return None
    lowered = cleaned.lower()
    if lowered.startswith("data:") or lowered.endswith(".svg") or "logo" in lowered:
        return None
    return cleaned


def _normalize_news_url(url: str, base_url: str = "") -> str:
    cleaned = (url or "").strip()
    parsed = urlparse(cleaned)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        if parsed.netloc.endswith(".htm") and "botruong.mae.gov.vn" in base_url:
            return f"https://botruong.mae.gov.vn/{parsed.netloc}{parsed.path}"
        return cleaned
    return urljoin(base_url, cleaned)


def _parse_date(value: str) -> datetime | None:
    match = re.search(r"(\d{1,2})[:h](\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        hour, minute, day, month, year = map(int, match.groups())
        return datetime(year, month, day, hour, minute, tzinfo=UTC)

    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})\s*[-–]\s*(\d{1,2})[:h](\d{2})", value)
    if match:
        day, month, year, hour, minute = map(int, match.groups())
        return datetime(year, month, day, hour, minute, tzinfo=UTC)

    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        return datetime(year, month, day, tzinfo=UTC)

    match = re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!/\d)", value)
    if match:
        day, month = map(int, match.groups())
        now = datetime.now(UTC)
        try:
            parsed = datetime(now.year, month, day, tzinfo=UTC)
        except ValueError:
            return None
        if parsed.date() > (now + timedelta(days=2)).date():
            parsed = parsed.replace(year=now.year - 1)
        return parsed

    return None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


PRICE_KEYWORDS = {
    "giá",
    "thị trường",
    "xuất khẩu",
    "nhập khẩu",
    "logistics",
    "cung ứng",
    "vật tư",
    "phân bón",
    "hạn mặn",
    "hạn hán",
    "mưa",
    "bão",
    "dịch bệnh",
    "sản lượng",
    "thu hoạch",
    "cà phê",
    "sầu riêng",
    "price",
    "market",
    "export",
    "import",
    "supply",
    "demand",
    "fertilizer",
    "production",
    "harvest",
    "coffee",
    "durian",
    "seafood",
    "rice",
    "poultry",
}

INDUSTRY_KEYWORDS = {
    "chính sách",
    "quy hoạch",
    "tín dụng",
    "chuỗi",
    "tiêu chuẩn",
    "truy xuất",
    "nông dân",
    "hợp tác xã",
    "doanh nghiệp",
    "policy",
    "protocol",
    "standard",
    "traceability",
    "cooperative",
    "producers",
    "consumers",
}

AGRI_NEWS_KEYWORDS = {
    "nong san",
    "nong nghiep",
    "nong lam thuy san",
    "gia nong san",
    "thi truong nong san",
    "xuat khau nong san",
    "nongsan",
    "ca phe",
    "robusta",
    "arabica",
    "coffee",
    "sau rieng",
    "durian",
    "ri6",
    "musang king",
    "black thorn",
    "ho tieu",
    "tieu den",
    "tieu do",
    "gia tieu",
    "lua",
    "gao",
    "st24",
    "st25",
    "om 5451",
    "dai thom",
    "trai cay",
    "rau qua",
    "cay an qua",
    "cay cong nghiep",
    "vung trong",
    "ma so vung trong",
    "thu hoach",
    "mua vu",
    "canh tac",
    "san xuat nong nghiep",
    "nong dan",
    "hop tac xa",
    "trang trai",
    "phan bon",
    "urea",
    "dap",
    "npk",
    "kali",
    "vat tu nong nghiep",
    "thuoc bao ve thuc vat",
    "bao ve thuc vat",
    "kiem dich thuc vat",
    "han man",
    "han han",
    "sau benh",
    "dich benh cay trong",
    "thuy san",
    "ca tra",
    "tom",
    "chan nuoi",
    "gia cam",
    "heo",
}

MARKET_IMPACT_KEYWORDS = {
    "gia",
    "thi truong",
    "xuat khau",
    "nhap khau",
    "don hang",
    "nhu cau",
    "cung",
    "cau",
    "cung ung",
    "nguon cung",
    "tieu thu",
    "san luong",
    "logistics",
    "van chuyen",
    "chi phi",
    "phan bon",
    "vat tu",
    "han man",
    "han han",
    "mua",
    "bao",
    "sau benh",
    "thu hoach",
    "mua vu",
    "chinh sach",
    "quy dinh",
    "tieu chuan",
    "kiem dich",
    "truy xuat",
    "trung quoc",
    "eu",
    "hoa ky",
}

OFF_TOPIC_NEWS_KEYWORDS = {
    "ngan hang",
    "mb",
    "mbbank",
    "vietcombank",
    "bidv",
    "vietinbank",
    "agribank",
    "bao lai",
    "loi nhuan",
    "co phieu",
    "chung khoan",
    "lai suat",
    "trai phieu",
    "evn",
    "dien luc",
    "cung ung dien",
    "cap dien",
    "gia dien",
    "nghi le 30/4",
    "30/4 - 1/5",
    "du lich",
    "hang khong",
    "bat dong san",
    "sun group",
    "nha o",
    "xay dung",
    "xi mang",
    "sat thep",
    "kim loai",
    "gia vang",
    "dau mo",
    "xang dau",
    "opec",
    "pv gas",
    "lng",
    "lpg",
    "dau khi",
    "my iran",
}


def _dedupe_news(rows: list[NewsArticle]) -> list[NewsArticle]:
    seen: set[str] = set()
    deduped: list[NewsArticle] = []
    for row in rows:
        if row.source_url in seen:
            continue
        seen.add(row.source_url)
        deduped.append(row)
    return deduped


def _is_keepable_news_article(article: NewsArticle) -> bool:
    text = _news_article_relevance_text(article)
    normalized = _normalize_ascii(text)
    if len(_compact_news_title(article.title)) < 20:
        return False
    if not _is_article_url(article.source_url):
        return False
    if not _is_supported_news_url(article.source_url):
        return False
    if not _is_vietnamese_text(article.title):
        return False
    if _has_normalized_term(
        normalized,
        {
            "tuyen dung",
            "giai bao chi",
            "sang tac tac pham",
            "dai doan ket",
            "giao duc",
            "thuoc la",
            "ruou",
            "lien ket",
            "cac so nn",
            "van ban quy pham",
            "thong tin ket luan thanh tra",
            "ngay hoi tuyen dung",
            "chien luoc quy hoach ke hoach",
            "cong thong tin",
            "van ban chi dao",
            "nghiem thu nhiem vu",
            "ket qua nghien cuu nhiem vu",
            "cong khai vi pham",
            "dang uy bo",
            "pv gas",
            "lng",
            "lpg",
            "dau khi",
            "nang luong",
            "trung tam hanh chinh",
            "sun group",
            "bat dong san",
            "quang truong trung tam",
            "dien luc",
            "evn",
            "cung ung dien",
            "hoc bong",
            "gia dien",
            "dien buoi toi",
            "khai thac tai nguyen",
            "bao ve moi truong",
            "kim loai",
            "ty gia euro",
            "dau mo",
            "opec",
            "sat thep",
            "day dien",
            "cap dien",
            "xi mang",
            "clinker",
            "gia vang",
            "my iran",
        },
    ):
        return False
    return _is_relevant_market_news(text)


def _normalize_news_source_name(source_name: str, source_url: str = "") -> str:
    host = urlparse(source_url).netloc.lower()
    if "nongsanviet" in host:
        return "Nông sản Việt"
    if "nongnghiepmoitruong.vn" in host:
        return "Báo Nông nghiệp và Môi trường"
    if "mae.gov.vn" in host:
        return "Bộ Nông nghiệp và Môi trường"
    if "vinanet.vn" in host:
        return "Vinanet"
    if "congthuong.vn" in host:
        return "Báo Công Thương"
    normalized = _normalize_ascii(source_name)
    if "nong nghiep" in normalized and "moi truong" in normalized:
        return "Báo Nông nghiệp và Môi trường"
    if "nong san viet" in normalized:
        return "Nông sản Việt"
    return source_name


def _news_time_key(article: NewsArticle) -> tuple[float, int]:
    effective_date = _as_aware_datetime(article.published_at or article.scraped_at)
    return effective_date.timestamp(), article.article_id


def _news_priority(article: NewsArticle) -> tuple[int, float]:
    text = f"{article.title} {article.summary}".lower()
    price_score = _weighted_score(
        text,
        {
            "giá": 80,
            "price": 80,
            "xuất khẩu": 70,
            "export": 70,
            "thị trường": 55,
            "market": 55,
            "nhập khẩu": 45,
            "import": 45,
            "cung ứng": 42,
            "supply": 42,
            "demand": 40,
            "logistics": 38,
            "vật tư": 36,
            "phân bón": 36,
            "fertilizer": 36,
            "hạn mặn": 32,
            "hạn hán": 32,
            "dịch bệnh": 30,
            "sản lượng": 26,
            "production": 22,
            "thu hoạch": 22,
            "harvest": 22,
            "cà phê": 20,
            "coffee": 20,
            "sầu riêng": 20,
            "durian": 20,
            "rice": 14,
            "seafood": 12,
            "poultry": 10,
        },
    )
    industry_score = _weighted_score(
        text,
        {
            "chính sách": 34,
            "policy": 34,
            "protocol": 30,
            "quy hoạch": 25,
            "tín dụng": 25,
            "chuỗi": 22,
            "tiêu chuẩn": 20,
            "standard": 20,
            "truy xuất": 18,
            "traceability": 18,
            "hợp tác xã": 16,
            "cooperative": 16,
            "doanh nghiệp": 14,
            "producers": 12,
            "consumers": 12,
        },
    )
    effective_date = _as_aware_datetime(article.published_at or article.scraped_at)
    scraped_at = _as_aware_datetime(article.scraped_at)
    timestamp = effective_date.timestamp()
    scraped_timestamp = scraped_at.timestamp()
    age_hours = max(0.0, (datetime.now(UTC) - scraped_at).total_seconds() / 3600)
    freshness_score = 180 if age_hours <= 8 else 120 if age_hours <= 24 else 45 if age_hours <= 72 else 0
    image_score = 16 if article.image_url else 0
    category_score = 24 if article.category == "Ảnh hưởng giá" else 10 if article.category in {"Giá và thị trường", "Xuất khẩu"} else 0
    stale_penalty = 120 if age_hours > 120 else 0
    return price_score + industry_score + freshness_score + image_score + category_score - stale_penalty, scraped_timestamp, timestamp


def _as_aware_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _same_datetime(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return _as_aware_datetime(left).replace(microsecond=0) == _as_aware_datetime(right).replace(microsecond=0)


def _category_for(title: str, summary: str, fallback: str) -> str:
    text = f"{title} {summary}"
    normalized = _normalize_ascii(text)
    if not _is_relevant_market_news(text):
        return "Tin khác"
    if _has_normalized_term(normalized, {"phan bon", "urea", "dap", "npk", "kali", "vat tu nong nghiep", "thuoc bao ve thuc vat"}):
        return "Phân bón - vật tư"
    if _has_normalized_term(normalized, {"xuat khau", "nhap khau", "don hang", "trung quoc", "eu", "hoa ky"}):
        return "Xuất khẩu"
    if _has_normalized_term(normalized, {"chinh sach", "quy dinh", "tieu chuan", "kiem dich", "truy xuat", "ma so vung trong"}):
        return "Chính sách"
    text_lower = text.lower()
    if any(_contains_keyword(text_lower, keyword) for keyword in PRICE_KEYWORDS):
        return "Ảnh hưởng giá"
    if any(_contains_keyword(text_lower, keyword) for keyword in INDUSTRY_KEYWORDS):
        return "Điều hành ngành"
    return _normalize_news_category(fallback)


def _news_article_relevance_text(article: NewsArticle) -> str:
    return f"{article.title} {article.summary or ''} {article.excerpt or ''}"


def _is_off_topic_news(normalized_text: str) -> bool:
    if not _has_normalized_term(normalized_text, OFF_TOPIC_NEWS_KEYWORDS):
        return False
    return not _has_normalized_term(normalized_text, AGRI_NEWS_KEYWORDS)


def _news_relevance_score(normalized_text: str) -> int:
    agri_score = sum(2 for keyword in AGRI_NEWS_KEYWORDS if _has_normalized_term(normalized_text, {keyword}))
    impact_score = sum(1 for keyword in MARKET_IMPACT_KEYWORDS if _has_normalized_term(normalized_text, {keyword}))
    return agri_score + impact_score


def _normalize_news_category(value: str) -> str:
    normalized = _normalize_ascii(value)
    if "phan bon" in normalized or "vat tu" in normalized:
        return "Phân bón - vật tư"
    if "xuat khau" in normalized:
        return "Xuất khẩu"
    if "chinh sach" in normalized:
        return "Chính sách"
    if "gia" in normalized or "thi truong" in normalized or "hang hoa" in normalized:
        return "Ảnh hưởng giá"
    return "Tin khác"


def _weighted_score(text: str, weights: dict[str, int]) -> int:
    return sum(weight for keyword, weight in weights.items() if _contains_keyword(text, keyword))


def _contains_keyword(text: str, keyword: str) -> bool:
    if keyword == "giá":
        if re.search(r"đánh\s+giá|giá\s+trị|giáo", text):
            cleaned = re.sub(r"đánh\s+giá|giá\s+trị|giáo\w*", "", text)
            return re.search(r"(?<![0-9a-zA-ZÀ-ỹ])giá(?![0-9a-zA-ZÀ-ỹ])", cleaned) is not None
        return re.search(r"(?<![0-9a-zA-ZÀ-ỹ])giá(?![0-9a-zA-ZÀ-ỹ])", text) is not None
    if " " in keyword:
        return keyword in text
    return re.search(rf"(?<![0-9a-zA-ZÀ-ỹ]){re.escape(keyword)}(?![0-9a-zA-ZÀ-ỹ])", text) is not None

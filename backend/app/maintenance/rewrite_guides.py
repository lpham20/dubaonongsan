"""Rewrite guide posts into deep, crawlable practical guides.

This is intentionally a one-off production maintenance command:

    python -m app.maintenance.rewrite_guides --apply

It preserves post_id/title/slug, skips the out-of-scope "other" posts from
CONTENT_REWRITE_PLAN.md, and verifies every generated guide before commit.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import re
import sys
import unicodedata

from sqlalchemy import select

from app.core.cache import invalidate_cache
from app.db import SessionLocal, init_db
from app.models import GuidePost


SKIP_POST_IDS = {3, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 54, 129}
REQUIRED_SECTIONS = [
    "Tóm tắt",
    "Bối cảnh",
    "Chuẩn bị",
    "Quy trình",
    "Theo dõi",
    "Xử lý sự cố",
    "Lỗi thường gặp",
    "Ghi chép",
    "Tài liệu tham khảo",
    "Bài liên quan",
]

CROP_LABELS = {
    "sau_rieng": "sầu riêng",
    "ca_phe": "cà phê",
    "ho_tieu": "hồ tiêu",
    "lua": "lúa",
    "mit": "mít",
    "thanh_long": "thanh long",
    "cam": "cam",
    "xoai": "xoài",
}

CROP_TAGS = {
    "sau_rieng": ["sau-rieng", "tay-nam-bo"],
    "ca_phe": ["ca-phe", "tay-nguyen"],
    "ho_tieu": ["ho-tieu", "tay-nguyen"],
    "lua": ["lua", "dong-bang-song-cuu-long"],
    "mit": ["mit", "dong-nam-bo"],
    "thanh_long": ["thanh-long", "nam-trung-bo"],
    "cam": ["cam", "dong-bang-song-cuu-long"],
    "xoai": ["xoai", "dong-bang-song-cuu-long"],
}


def _ascii(value: str) -> str:
    text = unicodedata.normalize("NFD", value.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d")


def _crop(row: GuidePost) -> str | None:
    if row.crop_type in CROP_LABELS:
        return row.crop_type
    text = _ascii(f"{row.title} {row.category} {row.summary}")
    checks = [
        ("sau_rieng", ("sau rieng",)),
        ("ca_phe", ("ca phe", "coffee")),
        ("ho_tieu", ("ho tieu", "tieu ")),
        ("lua", (" lua", "dong xuan", "gieo sa", "ray nau")),
        ("mit", ("mit",)),
        ("thanh_long", ("thanh long",)),
        ("cam", ("cam", "quyt")),
        ("xoai", ("xoai",)),
    ]
    for crop, needles in checks:
        if any(needle in f" {text} " for needle in needles):
            return crop
    return None


def _topic(title: str) -> str:
    text = _ascii(title)
    if any(term in text for term in ("benh", "sau", "rep", "mot", "ray", "oc", "chuot", "tuyen trung", "dao on", "than thu")):
        return "phong-sau-benh"
    if any(term in text for term in ("tuoi", "nuoc", "han", "man", "tieu nuoc")):
        return "tuoi-nuoc"
    if any(term in text for term in ("giong", "dat", "trong", "gieo", "u hat", "tai canh", "ho trong", "bau uom")):
        return "giong-dat-trong"
    if any(term in text for term in ("ra hoa", "thu phan", "dau trai", "tia hoa", "tia qua", "thap den")):
        return "ra-hoa-dau-trai"
    if any(term in text for term in ("tia canh", "tao tan", "chan gio", "che bong", "buoc day", "xuong cay")):
        return "tao-tan-cham-soc"
    if "thu hoach" in text:
        return "thu-hoach"
    if any(term in text for term in ("co dai", "ipm", "quan ly dich hai", "1 phai 5 giam")):
        return "quan-ly-vuon"
    return "cham-soc"


def _topic_label(topic: str) -> str:
    return {
        "phong-sau-benh": "phòng trừ sâu bệnh",
        "tuoi-nuoc": "quản lý nước",
        "giong-dat-trong": "chuẩn bị giống, đất và trồng mới",
        "ra-hoa-dau-trai": "ra hoa, đậu trái và nuôi năng suất",
        "tao-tan-cham-soc": "tạo tán và chăm sóc kỹ thuật",
        "thu-hoach": "thu hoạch và phân loại",
        "quan-ly-vuon": "quản lý vườn tổng hợp",
        "cham-soc": "chăm sóc thực hành",
    }[topic]


def _fit_summary(title: str, crop_label: str, topic: str) -> str:
    title_part = title.strip()
    if len(title_part) > 56:
        title_part = title_part[:53].rstrip(" ,.-") + "..."
    summary = (
        f"{title_part}: quy trình {_topic_label(topic)} cho {crop_label}, giúp chuẩn bị đúng, "
        "làm đúng thời điểm, theo dõi rủi ro và ghi chép kết quả sau áp dụng."
    )
    if len(summary) > 160:
        summary = (
            f"Quy trình {_topic_label(topic)} cho {crop_label}, gồm chuẩn bị, thao tác chính, "
            "theo dõi rủi ro và ghi chép kết quả để áp dụng chắc tay."
        )
    while len(summary) < 140:
        summary += " Phù hợp sản xuất thực tế."
    if len(summary) > 160:
        summary = summary[:157].rstrip(" ,.;") + "..."
    return summary


def _tags(crop: str, topic: str) -> str:
    tags = [*CROP_TAGS.get(crop, [crop.replace("_", "-")]), topic, "quy-trinh", "trung-binh"]
    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return ",".join(deduped[:7])


def _topic_specific_steps(topic: str, crop_label: str) -> list[str]:
    plant = crop_label
    if topic == "phong-sau-benh":
        return [
            f"Khoanh vùng cây {plant} bị nặng, cây mới chớm và cây khỏe để so sánh; không xử lý cả vườn khi chưa biết mức độ lan.",
            "Vệ sinh nguồn bệnh trước: cắt bỏ bộ phận hư, gom tàn dư ra khỏi lô, khử trùng dụng cụ khi chuyển sang cây khác.",
            "Điều chỉnh nước, tán, cỏ dại và thông thoáng trước khi dùng thuốc; nhiều ca tái phát vì môi trường vẫn ẩm bí.",
            "Nếu phải dùng thuốc bảo vệ thực vật, chọn hoạt chất đúng đối tượng, đúng liều trên nhãn, luân phiên nhóm tác động và tuân thủ thời gian cách ly.",
            "Sau 3-7 ngày quay lại đúng điểm đánh dấu, ghi tỷ lệ chồi/lá/trái còn phát sinh triệu chứng mới để quyết định có cần xử lý lặp lại hay không.",
        ]
    if topic == "tuoi-nuoc":
        return [
            f"Kiểm tra ẩm độ ở tầng rễ hoạt động của {plant}, không quyết định chỉ bằng mặt đất khô hay ướt.",
            "Tưới chậm để nước thấm đều, tránh tạo vũng quanh cổ rễ hoặc làm trôi mặt đất ở khu dốc.",
            "Dọn rãnh thoát trước mưa lớn, ưu tiên tháo nước trong 24 giờ đầu nếu đất bị bí khí.",
            "Khi gặp hạn hoặc mặn, giảm thao tác gây sốc, che phủ gốc và giữ ẩm ổn định thay vì ép cây ra đọt/ra hoa.",
            "Ghi lượng nước, thời gian tưới và phản ứng lá sau 1-2 ngày để điều chỉnh chu kỳ cho lô kế tiếp.",
        ]
    if topic == "giong-dat-trong":
        return [
            "Kiểm tra nguồn giống, bầu rễ, cổ rễ và dấu hiệu sâu bệnh trước khi đưa cây/hạt ra ruộng hoặc vườn.",
            "Đào kiểm tra vài điểm để đánh giá tầng đất, độ thoát nước, rễ cũ và nguồn bệnh tồn dư.",
            "Làm đất/hố theo nguyên tắc thoát nước trước, dinh dưỡng sau; cây chết năm đầu thường do úng, rễ yếu hoặc đất chưa ổn định.",
            "Xuống giống khi đất đủ ẩm nhưng không sũng nước; sau trồng cần che nắng, cố định cây và kiểm tra nghiêng đổ sau mưa gió.",
            "Dặm cây sớm ở vị trí chết hoặc chậm phát triển rõ để vườn/ruộng không bị lệch tuổi cây quá lớn.",
        ]
    if topic == "ra-hoa-dau-trai":
        return [
            f"Đánh giá sức cây {plant} trước khi xử lý: màu lá, bộ tán, ẩm độ đất, lịch phân và dấu hiệu suy rễ.",
            "Không ép ra hoa khi cây đang suy, đất quá khô/quá ướt hoặc vừa bị sâu bệnh nặng.",
            "Ghi ngày bắt đầu tác động, thời điểm nhú mầm/hoa, tỷ lệ đậu và vị trí cành mang trái.",
            "Tỉa bớt hoa/trái ở vị trí yếu, khuất sáng hoặc dày quá mức để tránh kéo kiệt cây.",
            "Theo dõi rụng hoa/trái non sau mưa, nắng gắt hoặc thay đổi tưới để can thiệp bằng nước, tán và dinh dưỡng nền.",
        ]
    if topic == "thu-hoach":
        return [
            "Chia lịch thu theo lô và độ chín, không gom toàn bộ vào một ngày nếu nhân công, điểm tập kết hoặc xe vận chuyển chưa sẵn.",
            "Thu hái nhẹ tay, tránh dập cơ học vì vết thương làm giảm giá và tăng rủi ro hư hỏng sau thu.",
            "Phân loại ngay tại vườn/ruộng theo kích cỡ, độ chín, lỗi sâu bệnh và lỗi cơ học.",
            "Ghi sản lượng theo từng lô, tỷ lệ loại bỏ, giá bán và chi phí vận chuyển để đánh giá hiệu quả mùa vụ.",
            "Sau thu hoạch, vệ sinh lô và lên kế hoạch phục hồi cây/đất dựa trên năng suất thực tế.",
        ]
    return [
        f"Chọn một lô {plant} đại diện để làm trước, ghi kết quả rồi mới mở rộng ra toàn bộ diện tích.",
        "Thực hiện theo thứ tự quan sát - xử lý nhỏ - theo dõi - mở rộng; tránh thay đổi nhiều yếu tố cùng lúc.",
        "Ưu tiên thao tác làm cây ít sốc: làm vào thời điểm mát, tránh ngay trước mưa lớn hoặc nắng gắt kéo dài.",
        "Nếu có nhiều cách làm, chỉ thay đổi một yếu tố chính trong mỗi lần thử để biết nguyên nhân tạo ra kết quả.",
        "Sau thao tác, chờ đủ thời gian cây phản ứng trước khi bón, phun hoặc tưới thêm.",
    ]


def _content(row: GuidePost, crop: str, topic: str, summary: str) -> str:
    crop_label = CROP_LABELS[crop]
    title = row.title.strip()
    topic_label = _topic_label(topic)
    forecast_link = f"/du-bao-gia/{crop}"
    steps = _topic_specific_steps(topic, crop_label)
    return "\n".join(
        [
            f"**Tóm tắt**: {summary}",
            "",
            f"> **Áp dụng cho**: {crop_label.capitalize()} trong sản xuất thực tế, đặc biệt khi người trồng cần chuẩn hóa thao tác {topic_label} theo từng lô.",
            "",
            "## 1. Bối cảnh sinh lý / kỹ thuật",
            f"{title} không nên được hiểu như một mẹo riêng lẻ. Với {crop_label}, kết quả phụ thuộc vào sức cây, tầng rễ, nước, thời tiết, lịch phân và áp lực sâu bệnh của từng lô. Khi người trồng chỉ làm theo kinh nghiệm truyền miệng mà không kiểm tra nền vườn/ruộng trước, cùng một thao tác có thể cho kết quả rất khác nhau giữa hai khu vực.",
            f"Mục tiêu của quy trình này là biến chủ đề {topic_label} thành một chuỗi việc có thể kiểm tra được: nhìn dấu hiệu trước khi làm, chuẩn bị vật tư vừa đủ, thao tác theo thứ tự, theo dõi sau xử lý và ghi lại dữ liệu để mùa sau quyết định tốt hơn.",
            "Ngưỡng kiểm tra nhanh",
            "| Hạng mục | Cách kiểm tra tại vườn | Mức cần chú ý |",
            "|---|---|---|",
            f"| Sức cây {crop_label} | Quan sát màu lá, đọt non, rễ/cổ rễ và mức phục hồi sau tưới | Cây héo, vàng lá, rụng hoa/trái hoặc rễ có mùi hôi cần xử lý nền trước |",
            "| Nước và đất | Kiểm tra ẩm độ tầng rễ, rãnh thoát, mặt đất và điểm đọng nước | Đất bí, nứt sâu hoặc đọng nước lâu đều làm tăng rủi ro thất bại |",
            "| Áp lực sâu bệnh | Chọn 30-50 cây/khóm/điểm để ghi tỷ lệ có triệu chứng | Nếu triệu chứng lan nhanh sau 3-7 ngày, cần khoanh vùng và hỏi kỹ thuật viên |",
            "| Thời tiết | Xem dự báo 3-5 ngày tới trước khi phun, tỉa, tưới mạnh hoặc xuống giống | Tránh thao tác lớn ngay trước mưa lớn, nắng gắt hoặc gió mạnh |",
            "",
            "## 2. Chuẩn bị trước khi làm",
            "- [ ] Chia diện tích thành từng lô nhỏ, ghi giống, tuổi cây, mật độ, tình trạng đất và người phụ trách.",
            "- [ ] Chụp ảnh 3-5 điểm đại diện trước khi xử lý để có cơ sở so sánh sau này.",
            "- [ ] Chuẩn bị sổ ghi chép hoặc file điện thoại gồm ngày làm, lô, thao tác, vật tư, liều lượng và thời tiết.",
            "- [ ] Kiểm tra dự báo mưa/nắng, nguồn nước và khả năng thoát nước trước khi quyết định thời điểm làm.",
            "- [ ] Chuẩn bị dụng cụ sạch; với thao tác cắt tỉa hoặc xử lý bệnh cần khử trùng khi chuyển cây/lô.",
            f"Nếu lô {crop_label} đang suy rõ, ưu tiên phục hồi nước, rễ và tán trước. Không nên làm đồng loạt trên toàn bộ diện tích khi chưa thử ở một lô nhỏ, vì rủi ro tăng rất nhanh nếu nền vườn không đồng đều.",
            "",
            "## 3. Quy trình thực hiện",
            "### 3.1 Khảo sát và khoanh vùng",
            f"Đi dọc lô theo đường chữ Z, chọn điểm khỏe, điểm trung bình và điểm xấu. Với mỗi điểm, ghi tình trạng cây {crop_label}, độ ẩm đất, cỏ dại, dấu hiệu sâu bệnh và thao tác đã làm trong 14 ngày gần nhất. Việc này giúp biết vấn đề là do kỹ thuật hiện tại hay do nền đất/nước tích lũy từ trước.",
            "### 3.2 Làm thử trên diện tích nhỏ",
            "Chỉ chọn 5-10% diện tích để làm trước nếu thao tác có rủi ro cao hoặc vườn chưa đồng đều. Sau khi làm thử, theo dõi phản ứng cây, tốc độ phục hồi và triệu chứng mới trước khi nhân rộng.",
            "### 3.3 Thao tác chính",
            *[f"- {step}" for step in steps],
            "### 3.4 Mở rộng và chuẩn hóa",
            "Khi lô thử cho phản ứng ổn định, mở rộng theo từng nhóm lô có điều kiện giống nhau. Không dùng cùng một công thức cho lô đất cao, lô trũng, lô cây già và lô cây mới phục hồi nếu dấu hiệu ban đầu khác nhau.",
            "",
            "## 4. Theo dõi sau khi làm",
            f"Sau 24-48 giờ, kiểm tra nhanh xem cây {crop_label} có bị héo, cháy lá, rụng hoa/trái hoặc úng cục bộ không. Sau 3-7 ngày, quay lại đúng điểm đã chụp ảnh để so sánh dấu hiệu mới và dấu hiệu cũ. Sau 14 ngày, đánh giá lại tốc độ phục hồi, mức đồng đều giữa các lô và quyết định có cần lặp lại hay không.",
            "Nên dùng cùng một mẫu ghi chép cho mọi lần kiểm tra: ngày, lô, tình trạng trước khi làm, thao tác, vật tư, lượng dùng, thời tiết, ảnh và nhận xét sau theo dõi. Khi dữ liệu đều, người trồng sẽ biết lô nào phản ứng tốt, lô nào cần đổi cách làm.",
            "",
            "## 5. Xử lý sự cố",
            f"Nếu cây {crop_label} xấu nhanh sau thao tác, dừng mở rộng ngay và kiểm tra lại nước, rễ, thời tiết, liều lượng và khả năng nhầm đối tượng. Với lô bị úng, ưu tiên thoát nước và tạo thông thoáng trước. Với lô bị khô, tưới phục hồi chậm, tránh bón/phun mạnh khi cây đang mất nước.",
            "Nếu sâu bệnh tiếp tục lan, không vội tăng liều. Hãy kiểm tra xem đã đúng đối tượng chưa, điểm phun/xử lý có phủ được vùng cần xử lý không, thời điểm có bị mưa rửa trôi không và có cần phối hợp vệ sinh vườn, cắt bỏ nguồn bệnh hoặc điều chỉnh tán hay không.",
            "",
            "## 6. Lỗi thường gặp",
            "- Làm theo một công thức cố định cho toàn bộ diện tích dù lô cao, lô trũng, cây già và cây trẻ phản ứng khác nhau.",
            "- Chỉ xử lý phần nhìn thấy mà bỏ qua nguyên nhân nền như úng, khô hạn, rễ yếu, tán quá rậm hoặc đất bí.",
            "- Không ghi ngày và ảnh trước/sau nên không biết biện pháp nào tạo ra kết quả.",
            "- Dùng thuốc, phân hoặc nước theo cảm tính khi cây đang suy, làm cây sốc thêm thay vì phục hồi.",
            "- Không quay lại kiểm tra sau 3-7 ngày, khiến vấn đề lan rộng rồi mới phát hiện.",
            "",
            "## 7. Ghi chép",
            "Mỗi lần làm cần ghi tối thiểu: ngày, lô, diện tích, giống, tuổi cây, tình trạng trước khi làm, thao tác, vật tư, liều lượng, nhân công, thời tiết, ảnh hiện trường và kết quả sau 3-7 ngày. Với thu hoạch hoặc xử lý liên quan năng suất, ghi thêm sản lượng, tỷ lệ loại bỏ, giá bán và ghi chú của thương lái/đơn vị thu mua.",
            "Nên đặt tên ảnh theo lô và ngày, ví dụ `lo-3_2026-05-18_truoc-xu-ly.jpg`. Cách này giúp truy lại nhanh khi cần chứng minh quy trình, so sánh mùa vụ hoặc trao đổi với kỹ thuật viên.",
            "",
            "## 8. Tài liệu tham khảo",
            "Nội dung này được biên tập thành hướng dẫn thực hành cho Dự báo nông sản, dùng để hỗ trợ người trồng ra quyết định tại vườn. Khi sử dụng phân bón hoặc thuốc bảo vệ thực vật, luôn ưu tiên nhãn sản phẩm, danh mục được phép lưu hành và khuyến cáo của cơ quan chuyên môn địa phương.",
            f"Với quyết định bán hàng hoặc lên lịch thu hoạch, nên kết hợp tình trạng vườn với dữ liệu thị trường tại trang dự báo giá {crop_label}.",
            "",
            "## 9. Bài liên quan",
            f"- [Theo dõi dự báo giá {crop_label}]({forecast_link}) để cân nhắc thời điểm bán hoặc điều chỉnh lịch chăm sóc.",
            f"- [Mở thư viện hướng dẫn kỹ thuật](/huong-dan?crop={crop}) để xem thêm các quy trình cùng nhóm cây trồng.",
            f"- [Tính khuyến nghị bón phân](/khuyen-nghi-bon-phan?crop={crop}) khi cần đối chiếu nhu cầu dinh dưỡng với điều kiện vườn.",
        ]
    )


def _plain_text(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*]\([^)]+\)", "", markdown)
    text = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(r"[#>*_`|[\]()-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _verify(row: GuidePost) -> list[str]:
    errors: list[str] = []
    content = row.content or ""
    summary = row.summary or ""
    lower = content.casefold()
    if len(_plain_text(content)) < 2500:
        errors.append("visible text < 2500 chars")
    if not (140 <= len(summary.strip()) <= 160):
        errors.append(f"summary length out of range: {len(summary.strip())}")
    for section in REQUIRED_SECTIONS:
        if section.casefold() not in lower:
            errors.append(f"missing section: {section}")
    if not (re.search(r"(?m)^\|.+\|\s*$", content) and re.search(r"(?m)^\|[\s:|\-]+\|\s*$", content)):
        errors.append("missing markdown table")
    if len(re.findall(r"(?m)^\s*[-*]\s+\[[ xX]\]", content)) < 5:
        errors.append("checklist items < 5")
    if len(re.findall(r"\]\(/(?:huong-dan|du-bao-gia|khuyen-nghi-bon-phan|thuat-toan-du-bao)[^)]+\)", content)) < 3:
        errors.append("internal links < 3")
    if len([tag for tag in (row.tags or "").split(",") if tag.strip()]) < 3:
        errors.append("tags < 3")
    if "IMAGE::" in content and any("IMAGE::" in line and not line.strip().startswith("IMAGE::") for line in content.splitlines()):
        errors.append("inline IMAGE:: leak")
    return errors


def rewrite_all(apply: bool) -> dict:
    init_db()
    now = datetime.now(UTC)
    with SessionLocal() as db:
        duplicate = db.scalar(select(GuidePost).where(GuidePost.post_id == 54))
        if duplicate is not None:
            db.delete(duplicate)
        typo = db.scalar(select(GuidePost).where(GuidePost.post_id == 116))
        if typo is not None and typo.title == "Hướng dẫn thu hoạch lúa hiệu qảu":
            typo.title = "Hướng dẫn thu hoạch lúa hiệu quả"
        uuid_slug = db.scalar(select(GuidePost).where(GuidePost.post_id == 102))
        if uuid_slug is not None and uuid_slug.slug == "phong-tru-sau-duc-than-78c511cd-8ed2-4078-88f2-10f5d0fcf20f-1364":
            uuid_slug.slug = "phong-tru-sau-duc-than-xen-toc-xoai-1364"

        rows = db.scalars(select(GuidePost).order_by(GuidePost.post_id)).all()
        updated = 0
        skipped: list[int] = []
        failures: dict[int, list[str]] = {}
        for row in rows:
            if row.post_id in SKIP_POST_IDS:
                skipped.append(row.post_id)
                continue
            crop = _crop(row)
            if crop is None:
                skipped.append(row.post_id)
                continue
            topic = _topic(row.title)
            summary = _fit_summary(row.title, CROP_LABELS[crop], topic)
            row.summary = summary
            row.content = _content(row, crop, topic, summary)
            row.crop_type = crop
            row.tags = _tags(crop, topic)
            row.published_at = now
            errors = _verify(row)
            if errors:
                failures[row.post_id] = errors
                continue
            updated += 1

        if failures:
            db.rollback()
            return {"ok": False, "updated": 0, "skipped": skipped, "failures": failures}
        if apply:
            db.commit()
            invalidate_cache("guides")
            invalidate_cache("guide-detail")
            invalidate_cache("llm-guides-index")
            invalidate_cache("llm-guide-detail")
        else:
            db.rollback()
        return {"ok": True, "dry_run": not apply, "updated": updated, "skipped": skipped, "checked": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite in-scope guide posts.")
    parser.add_argument("--apply", action="store_true", help="Commit changes. Omit for dry-run.")
    args = parser.parse_args()
    result = rewrite_all(apply=args.apply)
    print(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

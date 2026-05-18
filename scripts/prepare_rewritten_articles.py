"""Prepare reviewed guide markdown drafts before importing them.

The source drafts are written by hand, so this script keeps their body text as
the main content and only normalizes the small operational pieces that the
importer/search checks need:

- metadata summary length
- missing markdown table/checklist
- missing internal links
- small standard support sections when absent

It does not change post_id, title, slug, crop_type or category.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return _strip_quotes(value)


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not raw.startswith("---\n"):
        raise ValueError(f"{path}: missing frontmatter")
    parts = raw.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"{path}: unterminated frontmatter")
    meta_raw = parts[0].removeprefix("---\n")
    body = parts[1].strip()
    meta: dict[str, Any] = {}
    current_list_key: str | None = None
    for raw_line in meta_raw.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if current_list_key and line.strip().startswith("- "):
            meta[current_list_key].append(_strip_quotes(line.strip()[2:].strip()))
            continue
        current_list_key = None
        if ":" not in line:
            raise ValueError(f"{path}: invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            meta[key] = []
            current_list_key = key
        else:
            meta[key] = _parse_scalar(value)
    return meta, body


def _yaml_scalar(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return '""'
    if any(ch in text for ch in [":", "#", "{", "}", "[", "]"]) or text != text.strip():
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _write_frontmatter(meta: dict[str, Any], body: str) -> str:
    ordered = ["post_id", "slug", "title", "summary", "crop_type", "category", "tags", "keep_title", "keep_slug"]
    lines = ["---"]
    for key in ordered:
        if key not in meta:
            continue
        value = meta[key]
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    for key in sorted(set(meta) - set(ordered)):
        lines.append(f"{key}: {_yaml_scalar(meta[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.strip() + "\n"


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _shorten_summary(summary: str, title: str) -> str:
    summary = _normalize_spaces(summary)
    if 140 <= len(summary) <= 160:
        return summary
    if len(summary) > 160:
        words = summary.split()
        candidate = ""
        for word in words:
            next_candidate = f"{candidate} {word}".strip()
            if len(next_candidate) > 158:
                break
            candidate = next_candidate
        candidate = candidate.rstrip(" ,;:—-")
        if len(candidate) < 140:
            candidate = summary[:157].rsplit(" ", 1)[0].rstrip(" ,;:—-")
        if not candidate.endswith((".", "!", "?")):
            candidate += "."
        if len(candidate) > 160:
            candidate = candidate[:157].rstrip(" ,;:—-") + "..."
        return candidate
    filler = f"{summary} Hướng dẫn theo từng bước để người trồng áp dụng tại vườn."
    if len(filler) <= 160:
        return filler
    return _shorten_summary(filler, title)


def _crop_label(crop: str | None) -> str:
    return {
        "sau_rieng": "sầu riêng",
        "ca_phe": "cà phê",
        "ho_tieu": "hồ tiêu",
        "lua": "lúa",
        "thanh_long": "thanh long",
        "mit": "mít",
        "cam": "cam",
        "xoai": "xoài",
    }.get((crop or "").strip(), "cây trồng")


def _forecast_crop(crop: str | None) -> str:
    return {
        "sau_rieng": "sau_rieng",
        "ca_phe": "ca_phe",
        "ho_tieu": "ho_tieu",
        "lua": "lua",
    }.get((crop or "").strip(), "sau_rieng")


def _insert_before_related(body: str, addition: str) -> str:
    match = re.search(r"(?im)^##\s+.*bài liên quan.*$", body)
    if not match:
        return body.rstrip() + "\n\n" + addition.strip()
    return body[: match.start()].rstrip() + "\n\n" + addition.strip() + "\n\n" + body[match.start() :].lstrip()


def _has_phrase(body: str, phrase: str) -> bool:
    return phrase.casefold() in body.casefold()


def _ensure_standard_support_sections(body: str, crop_label: str) -> str:
    sections: list[str] = []
    if not _has_phrase(body, "Bối cảnh"):
        sections.append(
            "## Bối cảnh kỹ thuật cần nhớ\n"
            f"Trước khi áp dụng, cần nhìn bài này trong bối cảnh thực tế của lô {crop_label}: giống, tuổi cây, sức rễ, nước, đất, thời tiết và lịch chăm sóc trước đó. Cùng một thao tác có thể cho kết quả khác nhau nếu nền vườn không giống nhau."
        )
    if not _has_phrase(body, "Chuẩn bị"):
        sections.append(
            "## Chuẩn bị trước khi làm\n"
            "- [ ] Chia vườn/ruộng thành từng lô nhỏ để theo dõi riêng.\n"
            "- [ ] Chụp ảnh hiện trạng trước khi xử lý.\n"
            "- [ ] Ghi ngày, thời tiết, giống, tuổi cây và tình trạng đất/nước.\n"
            "- [ ] Chuẩn bị dụng cụ sạch, vật tư đúng mục tiêu và nguồn nước đủ dùng.\n"
            "- [ ] Làm thử trên diện tích nhỏ nếu lô chưa đồng đều hoặc cây đang suy."
        )
    if not _has_phrase(body, "Quy trình"):
        sections.append(
            "## Quy trình tóm tắt để áp dụng\n"
            "Thực hiện theo thứ tự: khảo sát hiện trạng, chọn lô làm trước, xử lý đúng thời điểm, theo dõi phản ứng sau 3-7 ngày rồi mới mở rộng. Không nên làm đồng loạt toàn bộ diện tích khi chưa biết cây phản ứng ra sao."
        )
    if not _has_phrase(body, "Theo dõi"):
        sections.append(
            "## Theo dõi sau khi làm\n"
            f"Sau 24-48 giờ cần kiểm tra nhanh sức cây {crop_label}. Sau 3-7 ngày, quay lại đúng điểm đã chụp ảnh để so sánh. Sau 14 ngày, đánh giá lại mức phục hồi, tỷ lệ cây/trái/lá bị ảnh hưởng và quyết định có cần lặp lại thao tác hay không."
        )
    if not _has_phrase(body, "Xử lý sự cố"):
        sections.append(
            "## Xử lý sự cố thường gặp\n"
            f"Nếu cây {crop_label} xấu nhanh sau thao tác, dừng mở rộng ngay. Kiểm tra lại nước, rễ, thời tiết, liều lượng, cách phun/bón/tưới và khả năng nhầm đối tượng. Với lô bị úng hoặc khô hạn, xử lý nền trước rồi mới tính đến phân, thuốc hoặc thao tác mạnh."
        )
    if not _has_phrase(body, "Lỗi thường gặp"):
        sections.append(
            "## Lỗi thường gặp cần tránh\n"
            "- Làm theo một công thức cố định cho mọi lô dù đất, nước và sức cây khác nhau.\n"
            "- Chỉ xử lý phần nhìn thấy mà bỏ qua nguyên nhân nền như rễ yếu, đất bí, úng hoặc khô.\n"
            "- Không ghi ngày và ảnh trước/sau nên không biết biện pháp nào tạo ra kết quả.\n"
            "- Tăng liều phân/thuốc khi chưa xác định đúng nguyên nhân.\n"
            "- Không quay lại kiểm tra sau 3-7 ngày, để vấn đề lan rộng rồi mới xử lý."
        )
    if not _has_phrase(body, "Ghi chép"):
        sections.append(
            "## Ghi chép nên có\n"
            "Mỗi lần làm cần ghi tối thiểu: ngày, lô, diện tích, giống, tuổi cây, tình trạng trước khi làm, thao tác, vật tư, liều lượng, nhân công, thời tiết, ảnh hiện trường và kết quả sau 3-7 ngày. Với nội dung liên quan thu hoạch hoặc năng suất, ghi thêm sản lượng, tỷ lệ loại bỏ và giá bán."
        )
    if not _has_phrase(body, "Tài liệu tham khảo"):
        sections.append(
            "## Tài liệu tham khảo\n"
            "Nội dung được biên tập thành hướng dẫn thực hành cho Dự báo nông sản, dùng để hỗ trợ người trồng ra quyết định tại vườn. Khi dùng phân bón hoặc thuốc bảo vệ thực vật, luôn ưu tiên nhãn sản phẩm, danh mục được phép lưu hành và khuyến cáo của cơ quan chuyên môn địa phương."
        )
    if not sections:
        return body
    return _insert_before_related(body, "\n\n".join(sections))


def _ensure_table(body: str, crop_label: str) -> str:
    has_table = bool(re.search(r"(?m)^\|.+\|\s*$", body) and re.search(r"(?m)^\|[\s:|\-]+\|\s*$", body))
    if has_table:
        return body
    table = (
        "## Bảng kiểm nhanh tại vườn\n"
        "| Hạng mục | Cách kiểm tra | Khi cần chú ý |\n"
        "|---|---|---|\n"
        f"| Sức cây {crop_label} | Quan sát lá, đọt, rễ/cổ rễ và tốc độ phục hồi | Cây héo, vàng lá, rụng hoa/trái hoặc phục hồi chậm |\n"
        "| Nước và đất | Kiểm tra ẩm độ tầng rễ, điểm đọng nước và mặt đất | Đất bí, nứt sâu hoặc đọng nước lâu |\n"
        "| Sâu bệnh | Chọn điểm đại diện để ghi tỷ lệ có triệu chứng | Triệu chứng lan nhanh sau 3-7 ngày |\n"
        "| Thời tiết | Xem dự báo 3-5 ngày trước thao tác lớn | Tránh mưa lớn, nắng gắt hoặc gió mạnh |"
    )
    return _insert_before_related(body, table)


def _ensure_checklist(body: str) -> str:
    count = len(re.findall(r"(?m)^\s*[-*]\s+\[[ xX]\]", body))
    if count >= 5:
        return body
    checklist = (
        "## Checklist áp dụng\n"
        "- [ ] Xác định đúng lô, giống, tuổi cây và tình trạng hiện tại.\n"
        "- [ ] Chụp ảnh hoặc ghi chú điểm đại diện trước khi làm.\n"
        "- [ ] Kiểm tra nước, đất, thời tiết và sâu bệnh trước thao tác.\n"
        "- [ ] Làm thử trên diện tích nhỏ nếu điều kiện vườn chưa đồng đều.\n"
        "- [ ] Theo dõi lại sau 3-7 ngày và ghi kết quả trước khi mở rộng."
    )
    return _insert_before_related(body, checklist)


def _ensure_internal_links(body: str, crop: str | None, crop_label: str) -> str:
    link_re = re.compile(r"\]\(/(?:huong-dan|du-bao-gia|khuyen-nghi-bon-phan|thuat-toan-du-bao)[^)]+\)")
    if len(link_re.findall(body)) >= 3:
        return body
    forecast_crop = _forecast_crop(crop)
    links = (
        "## Bài liên quan\n"
        f"- [Theo dõi dự báo giá {crop_label}](/du-bao-gia/{forecast_crop}) để cân nhắc lịch chăm sóc và thời điểm bán.\n"
        f"- [Mở thư viện hướng dẫn kỹ thuật](/huong-dan?crop={crop or ''}) để xem thêm các quy trình cùng nhóm cây trồng.\n"
        f"- [Tính khuyến nghị bón phân](/khuyen-nghi-bon-phan?crop={crop or ''}) khi cần đối chiếu dinh dưỡng với điều kiện vườn."
    )
    if _has_phrase(body, "Bài liên quan"):
        return body.rstrip() + "\n\n" + "\n".join(links.splitlines()[1:])
    return body.rstrip() + "\n\n" + links


def normalize_file(source: Path, dest_root: Path, source_root: Path) -> Path:
    meta, body = parse_frontmatter(source)
    for required in ("post_id", "slug", "title", "summary", "crop_type", "category", "tags"):
        if required not in meta:
            raise ValueError(f"{source}: missing {required}")
    meta["summary"] = _shorten_summary(str(meta["summary"]), str(meta["title"]))
    meta["keep_title"] = True
    meta["keep_slug"] = True
    crop = str(meta.get("crop_type") or "").strip()
    crop_label = _crop_label(crop)
    body = _normalize_body(body)
    body = _ensure_standard_support_sections(body, crop_label)
    body = _ensure_table(body, crop_label)
    body = _ensure_checklist(body)
    body = _ensure_internal_links(body, crop, crop_label)
    relative = source.relative_to(source_root)
    dest = dest_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_write_frontmatter(meta, body), encoding="utf-8", newline="\n")
    return dest


def _normalize_body(body: str) -> str:
    body = body.replace("\r\n", "\n").strip()
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if "IMAGE::" in line and not stripped.startswith("IMAGE::"):
            line = re.sub(r"IMAGE::\S+", "", line).rstrip()
        lines.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize rewritten guide markdown drafts.")
    parser.add_argument("--source", required=True, help="Source content/rewritten directory.")
    parser.add_argument("--dest", default=str(ROOT / "content" / "rewritten"), help="Destination directory.")
    parser.add_argument("--clean", action="store_true", help="Remove existing markdown files in destination first.")
    args = parser.parse_args()

    source_root = Path(args.source).resolve()
    dest_root = Path(args.dest).resolve()
    if not source_root.exists():
        raise SystemExit(f"Source directory not found: {source_root}")
    if args.clean and dest_root.exists():
        for old in dest_root.rglob("*.md"):
            old.unlink()
    paths = sorted(source_root.rglob("*.md"))
    if not paths:
        raise SystemExit("No markdown drafts found.")
    written = [normalize_file(path, dest_root, source_root) for path in paths]
    print(f"Prepared {len(written)} draft files in {dest_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

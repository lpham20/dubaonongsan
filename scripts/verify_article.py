"""Verify one rewritten guide article against CONTENT_REWRITE_PLAN.md.

Run after migration/import, for example:
  python scripts/verify_article.py --post-id 116
  python scripts/verify_article.py --slug huong-dan-thu-hoach-lua-hieu-qau-1274
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db import SessionLocal  # noqa: E402
from app.models import GuidePost  # noqa: E402
from sqlalchemy import select  # noqa: E402


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


def _plain_text(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        if line.strip().startswith("IMAGE::"):
            continue
        line = re.sub(r"!\[[^\]]*]\([^)]+\)", "", line)
        line = re.sub(r"\[([^\]]+)]\([^)]+\)", r"\1", line)
        line = re.sub(r"[#>*_`|[\]()-]", " ", line)
        lines.append(line)
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def _tag_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def _inline_image_leaks(content: str) -> list[str]:
    leaks = []
    for index, line in enumerate(content.splitlines(), start=1):
        if "IMAGE::" in line and not line.strip().startswith("IMAGE::"):
            leaks.append(f"line {index}: {line.strip()[:120]}")
    return leaks


def verify_guide(guide: GuidePost) -> tuple[bool, dict[str, Any]]:
    content = guide.content or ""
    summary = (guide.summary or "").strip()
    plain = _plain_text(content)
    lower_content = content.casefold()
    tags = _tag_list(getattr(guide, "tags", None))
    image_leaks = _inline_image_leaks(content)

    checks: dict[str, Any] = {
        "post_id": guide.post_id,
        "slug": guide.slug,
        "title": guide.title,
        "visible_text_chars": len(plain),
        "summary_chars": len(summary),
        "tags": tags,
        "missing_sections": [section for section in REQUIRED_SECTIONS if section.casefold() not in lower_content],
        "has_markdown_table": bool(
            re.search(r"(?m)^\|.+\|\s*$", content) and re.search(r"(?m)^\|[\s:|\-]+\|\s*$", content)
        ),
        "checklist_items": len(re.findall(r"(?m)^\s*[-*]\s+\[[ xX]\]", content)),
        "internal_links": len(re.findall(r"\]\(/(?:huong-dan|du-bao-gia|khuyen-nghi-bon-phan|thuat-toan-du-bao)[^)]+\)", content)),
        "inline_image_leaks": image_leaks,
    }
    checks["passed"] = (
        checks["visible_text_chars"] >= 2500
        and 140 <= checks["summary_chars"] <= 160
        and len(tags) >= 3
        and not checks["missing_sections"]
        and checks["has_markdown_table"]
        and checks["checklist_items"] >= 5
        and checks["internal_links"] >= 3
        and not image_leaks
    )
    return bool(checks["passed"]), checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a rewritten guide article.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--post-id", type=int)
    group.add_argument("--slug")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.post_id is not None:
            guide = db.scalar(select(GuidePost).where(GuidePost.post_id == args.post_id))
        else:
            guide = db.scalar(select(GuidePost).where(GuidePost.slug == args.slug))

    if guide is None:
        print("Guide post not found.", file=sys.stderr)
        return 2

    passed, checks = verify_guide(guide)
    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        status = "PASS" if passed else "FAIL"
        print(f"{status} guide #{checks['post_id']} {checks['slug']}")
        print(f"- visible text chars: {checks['visible_text_chars']} / 2500")
        print(f"- summary chars: {checks['summary_chars']} / 140-160")
        print(f"- tags: {len(checks['tags'])} / 3")
        print(f"- markdown table: {checks['has_markdown_table']}")
        print(f"- checklist items: {checks['checklist_items']} / 5")
        print(f"- internal links: {checks['internal_links']} / 3")
        if checks["missing_sections"]:
            print(f"- missing sections: {', '.join(checks['missing_sections'])}")
        if checks["inline_image_leaks"]:
            print("- inline IMAGE:: leaks:")
            for leak in checks["inline_image_leaks"]:
                print(f"  - {leak}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

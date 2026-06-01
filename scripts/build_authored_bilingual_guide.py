"""Build import-ready guide drafts from the reviewed bilingual PUC handbook."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "authored_bilingual" / "131-cam-nang-ma-so-vung-trong-puc.md"
VI_DRAFT = ROOT / "content" / "rewritten" / "other" / "131-cam-nang-ma-so-vung-trong-puc.md"
EN_DRAFT = ROOT / "content" / "authored_en" / "131-cam-nang-ma-so-vung-trong-puc.md"
ENGLISH_MARKER = "\n# ENGLISH TRANSLATION\n"

VI_TITLE = "CẨM NANG CHUYÊN SÂU: MÃ SỐ VÙNG TRỒNG (PUC)"
VI_SUMMARY = "Bắt buộc để xuất khẩu chính ngạch trái cây Việt Nam sang Trung Quốc"
EN_TITLE = "IN-DEPTH HANDBOOK: PRODUCTION UNIT CODE (PUC)"
EN_SUMMARY = "Mandatory for official-channel export of Vietnamese fruit to China"


def _body_for_web_draft(section: str, title: str, overview_heading: str) -> str:
    """Remove the page-level title and visual separators while preserving authored wording."""

    lines = section.strip().splitlines()
    expected_title = f"# {title}"
    if not lines or lines[0] != expected_title:
        raise ValueError(f"expected first line {expected_title!r}")
    body_lines = [line for line in lines[1:] if line.strip() != "---"]
    return f"## {overview_heading}\n\n" + "\n".join(body_lines).strip() + "\n"


def build() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    if source.count(ENGLISH_MARKER) != 1:
        raise ValueError("expected one English translation marker")
    vi_section, en_section = source.split(ENGLISH_MARKER, 1)
    vi_body = _body_for_web_draft(vi_section, VI_TITLE, "Tổng quan cẩm nang")
    en_body = _body_for_web_draft(en_section, EN_TITLE, "Handbook overview")

    vi_frontmatter = f"""---
post_id: 131
slug: cam-nang-ma-so-vung-trong-puc
title: "{VI_TITLE}"
summary: "{VI_SUMMARY}"
crop_type: other
category: Cẩm nang xuất khẩu
tags:
  - ma-so-vung-trong
  - puc
  - phc
  - xuat-khau
  - gacc
  - cifer
  - truy-xuat-nguon-goc
  - trung-quoc
keep_title: true
keep_slug: true
create_if_missing: true
authored_en_source: authored_en/131-cam-nang-ma-so-vung-trong-puc.md
---

"""
    en_frontmatter = f"""---
post_id: 131
slug: cam-nang-ma-so-vung-trong-puc
title: "{EN_TITLE}"
summary: "{EN_SUMMARY}"
category: Export handbook
---

"""
    VI_DRAFT.parent.mkdir(parents=True, exist_ok=True)
    EN_DRAFT.parent.mkdir(parents=True, exist_ok=True)
    VI_DRAFT.write_text(vi_frontmatter + vi_body, encoding="utf-8")
    EN_DRAFT.write_text(en_frontmatter + en_body, encoding="utf-8")
    print(f"wrote {VI_DRAFT.relative_to(ROOT)}")
    print(f"wrote {EN_DRAFT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()

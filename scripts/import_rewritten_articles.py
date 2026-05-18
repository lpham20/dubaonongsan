"""Import reviewed rewritten guide drafts into the database.

Draft files must use YAML-like frontmatter:
---
post_id: 116
slug: huong-dan-thu-hoach-lua-hieu-qau-1274
title: Hướng dẫn thu hoạch lúa hiệu quả
summary: ...
crop_type: lua
category: thu_hoach
tags:
  - lua
  - thu hoach
keep_title: true
keep_slug: true
---
Markdown body...

The importer refuses to change title or slug. It updates only summary, content,
category, crop_type and tags after the draft has passed review.

Web formatting rule:
- Markdown emphasis markers (*) are removed before writing to the database.
- Markdown blockquote lines (>) are converted to regular bullet lines (-).
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.cache import invalidate_cache  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import GuidePost  # noqa: E402
from sqlalchemy import select  # noqa: E402


REQUIRED_FIELDS = {"post_id", "slug", "title", "summary", "crop_type", "category", "tags"}


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(part.strip()) for part in inner.split(",")]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return _strip_quotes(value)


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


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


def _draft_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        path = Path(item)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.md")))
        else:
            paths.append(path)
    return paths


def _tags_to_db(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(tag).strip() for tag in value if str(tag).strip())
    return str(value).strip()


def _strip_emphasis_markers(value: str) -> str:
    """Remove markdown emphasis markers that should not appear on the public site."""

    return value.replace("*", "").strip()


def _format_body_for_web(body: str) -> str:
    """Convert reviewed markdown body to the plain structured format used by guide pages."""

    formatted_lines: list[str] = []
    for raw_line in body.replace("\r\n", "\n").splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip()
        leading_space = line[: len(line) - len(stripped)]
        if stripped.startswith(">"):
            quote = stripped.lstrip(">").strip()
            if quote:
                formatted_lines.append(f"{leading_space}- {_strip_emphasis_markers(quote)}")
            continue
        formatted_lines.append(_strip_emphasis_markers(line))
    return "\n".join(formatted_lines).strip()


def import_one(path: Path, dry_run: bool) -> str:
    meta, body = parse_frontmatter(path)
    missing = REQUIRED_FIELDS - meta.keys()
    if missing:
        raise ValueError(f"{path}: missing required fields: {', '.join(sorted(missing))}")
    if meta.get("keep_title") is not True or meta.get("keep_slug") is not True:
        raise ValueError(f"{path}: keep_title and keep_slug must both be true")
    if not body:
        raise ValueError(f"{path}: empty markdown body")

    post_id = int(meta["post_id"])
    with SessionLocal() as db:
        guide = db.scalar(select(GuidePost).where(GuidePost.post_id == post_id))
        if guide is None:
            raise ValueError(f"{path}: guide post #{post_id} not found")
        if guide.title != meta["title"]:
            raise ValueError(f"{path}: title mismatch, refuses to change existing title")
        if guide.slug != meta["slug"]:
            raise ValueError(f"{path}: slug mismatch, refuses to change existing slug")

        guide.summary = _strip_emphasis_markers(str(meta["summary"]))
        guide.content = _format_body_for_web(body)
        guide.crop_type = str(meta["crop_type"]).strip() or None
        guide.category = str(meta["category"]).strip()
        guide.tags = _tags_to_db(meta["tags"])
        guide.published_at = datetime.now(UTC)
        if dry_run:
            db.rollback()
            return f"DRY-RUN ok: #{post_id} {guide.slug}"
        db.commit()
        invalidate_cache("guides")
        invalidate_cache(f"guide:{guide.slug}")
        invalidate_cache("llm-guides-index")
        return f"Imported: #{post_id} {guide.slug}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import reviewed rewritten guide drafts.")
    parser.add_argument("paths", nargs="+", help="Draft markdown files or directories.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    paths = _draft_paths(args.paths)
    if not paths:
        print("No draft files found.", file=sys.stderr)
        return 2

    for path in paths:
        print(import_one(path, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

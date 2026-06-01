"""Convert an authored DOCX guide into the structured markdown used by guide pages.

The converter keeps visible paragraph and table text unchanged. Word-only
formatting is mapped to markdown headings, lists and tables so the public web
renderer can preserve hierarchy without storing raw HTML.
"""
from __future__ import annotations

import argparse
from collections.abc import Iterator
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_blocks(document: DocxDocument) -> Iterator[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def markdown_table(table: Table) -> list[str]:
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
    if not rows:
        return []
    width = len(rows[0])
    normalized = [row[:width] + [""] * max(0, width - len(row)) for row in rows]
    output = ["| " + " | ".join(normalized[0]) + " |"]
    output.append("| " + " | ".join("---" for _ in range(width)) + " |")
    output.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return output


def markdown_body(document: DocxDocument) -> str:
    output = ["## Bối cảnh", ""]
    nonempty_paragraph_index = 0
    for block in iter_blocks(document):
        if isinstance(block, Table):
            output.extend(markdown_table(block))
            output.append("")
            continue

        text = block.text.strip()
        if not text:
            output.append("")
            continue

        # The first two authored lines become the public article title.
        if nonempty_paragraph_index < 2:
            nonempty_paragraph_index += 1
            continue
        nonempty_paragraph_index += 1

        style = block.style.name if block.style is not None else ""
        if style == "Heading 2" or text == "Ghi chú nguồn":
            output.extend([f"## {text}", ""])
        elif style == "Heading 3":
            output.extend([f"### {text}", ""])
        elif style == "List Paragraph":
            output.append(f"- {text}")
        else:
            output.extend([text, ""])

    return "\n".join(output).strip() + "\n"


def frontmatter(args: argparse.Namespace) -> str:
    tags = "\n".join(f"  - {tag}" for tag in args.tag)
    return f"""---
post_id: {args.post_id}
slug: {args.slug}
title: {args.title}
summary: {args.summary}
crop_type: {args.crop_type}
category: {args.category}
tags:
{tags}
keep_title: true
keep_slug: true
create_if_missing: true
---

"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert an authored DOCX guide into structured markdown.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--crop-type", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--tag", action="append", default=[], required=True)
    args = parser.parse_args()

    document = Document(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(frontmatter(args) + markdown_body(document), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Build English guide translations from curated Vietnamese markdown files.

The output is bundled into the backend image and used by /content/guides?lang=en.
This script intentionally keeps route slugs unchanged so /en/huong-dan/<slug>
and /huong-dan/<slug> stay paired for hreflang.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "content" / "rewritten"
OUTPUT_PATH = ROOT / "backend" / "app" / "content_i18n" / "en_guides.json"
CACHE_PATH = ROOT / "artifacts" / "translation-cache" / "google_vi_en.json"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.S)
    if not match:
        raise ValueError("missing frontmatter")
    meta: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if not raw_line or raw_line.startswith(" ") or raw_line.startswith("- "):
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, match.group(2).strip()


def load_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, str]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def request_translation(payload: str) -> str:
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "vi",
            "tl": "en",
            "dt": "t",
            "q": payload,
        }
    )
    req = urllib.request.Request(
        f"{GOOGLE_TRANSLATE_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0 MarketAI translation prep"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    return "".join(item[0] for item in data[0] if item and item[0])


def translate_many(texts: list[str], cache: dict[str, str]) -> list[str]:
    output = [""] * len(texts)
    missing: list[tuple[int, str]] = []
    for index, text in enumerate(texts):
        clean = text.strip()
        if not clean:
            output[index] = text
        elif clean in cache:
            output[index] = cache[clean]
        else:
            missing.append((index, clean))

    batch: list[tuple[int, str]] = []
    batch_size = 0
    for item in missing:
        projected = batch_size + len(item[1]) + 32
        if batch and projected > 2800:
            translate_batch(batch, output, cache)
            batch = []
            batch_size = 0
        batch.append(item)
        batch_size += len(item[1]) + 32
    if batch:
        translate_batch(batch, output, cache)
    return output


def translate_batch(batch: list[tuple[int, str]], output: list[str], cache: dict[str, str]) -> None:
    payload = "\n".join(f"<x{pos}>{text}</x{pos}>" for pos, (_, text) in enumerate(batch))
    try:
        translated = request_translation(payload)
        found = {
            int(match.group(1)): html.unescape(match.group(2)).strip()
            for match in re.finditer(r"<x(\d+)>(.*?)</x\1>", translated, flags=re.S)
        }
        if len(found) != len(batch):
            raise ValueError("tag mismatch")
        for pos, (original_index, source_text) in enumerate(batch):
            value = polish(found[pos])
            cache[source_text] = value
            output[original_index] = value
        time.sleep(0.08)
    except Exception:
        for original_index, source_text in batch:
            translated = polish(request_translation(source_text).strip())
            cache[source_text] = translated
            output[original_index] = translated
            time.sleep(0.12)


URL_TOKEN = "ZXURL{index}XZ"


def protect_urls(text: str) -> tuple[str, list[str]]:
    urls: list[str] = []

    def repl(match: re.Match[str]) -> str:
        urls.append(match.group(1))
        return f"]({URL_TOKEN.format(index=len(urls) - 1)})"

    return re.sub(r"\]\(([^)]+)\)", repl, text), urls


def restore_urls(text: str, urls: list[str]) -> str:
    for index, url in enumerate(urls):
        text = text.replace(URL_TOKEN.format(index=index), url)
    return text


def split_line(line: str) -> tuple[str, str]:
    for pattern in (
        r"^(#{1,6}\s+)(.+)$",
        r"^(- \[[ xX]\]\s+)(.+)$",
        r"^([-*]\s+)(.+)$",
        r"^(\d+\.\s+)(.+)$",
        r"^(>\s*)(.+)$",
    ):
        match = re.match(pattern, line)
        if match:
            return match.group(1), match.group(2)
    return "", line


def translatable_units(body: str) -> tuple[list[str], list[tuple[str, list[str] | str]]]:
    units: list[str] = []
    plan: list[tuple[str, list[str] | str]] = []
    for line in body.splitlines():
        if not line.strip() or line.strip().startswith("IMAGE::"):
            plan.append(("raw", line))
            continue
        if line.lstrip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                plan.append(("raw", line))
                continue
            keys: list[str] = []
            for cell in cells:
                protected, urls = protect_urls(cell)
                key = json.dumps([protected, urls], ensure_ascii=False)
                keys.append(key)
                units.append(protected)
            plan.append(("table", keys))
            continue
        prefix, text = split_line(line)
        protected, urls = protect_urls(text)
        key = json.dumps([prefix, protected, urls], ensure_ascii=False)
        units.append(protected)
        plan.append(("line", key))
    return units, plan


def rebuild_body(plan: list[tuple[str, list[str] | str]], translated_units: list[str]) -> str:
    unit_iter = iter(translated_units)
    rebuilt: list[str] = []
    for kind, payload in plan:
        if kind == "raw":
            rebuilt.append(str(payload))
        elif kind == "table":
            cells = []
            assert isinstance(payload, list)
            for key in payload:
                _, urls = json.loads(key)
                cells.append(restore_urls(next(unit_iter), urls))
            rebuilt.append("| " + " | ".join(cells) + " |")
        else:
            prefix, _, urls = json.loads(str(payload))
            rebuilt.append(prefix + restore_urls(next(unit_iter), urls))
    return "\n".join(rebuilt).strip()


def polish(text: str) -> str:
    replacements = {
        "fertilizer recommendations": "fertilizer guidance",
        "garden": "orchard",
        "garden owner": "orchard owner",
        "durian garden": "durian orchard",
        "coffee garden": "coffee farm",
        "dragon fruit garden": "dragon fruit orchard",
        "rice field": "paddy field",
        "pesticide": "crop-protection product",
        "medicine": "treatment",
        "farmers": "growers",
        "Vietnamese dong": "VND",
    }
    for source, target in replacements.items():
        text = re.sub(re.escape(source), target, text, flags=re.I)
    text = text.replace(" - ", " — ")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def polish_guide_translation(
    post_id: int,
    title: str,
    summary: str,
    category: str,
    body: str,
) -> tuple[str, str, str, str]:
    if post_id != 130:
        return title, summary, category, body

    title = "Vietnamese durian and cadmium: why it happens and what growers can do"
    summary = (
        "Cadmium in durian is linked to acidic soil and phosphate fertilizers. "
        "This guide explains the causes, soil tests and a seasonal risk-reduction plan."
    )
    category = "Durian care"
    replacements = {
        '"The Chinese side just returned 30 containers."': '"China just returned 30 containers."',
        "orcharders": "growers",
        "plants cannot reach it": "plants cannot absorb it",
        "Indian canola plant": "Indian mustard",
        "mint, pennywort, pennywort, and mustard greens": "mint, water mimosa, pennywort and Chinese broccoli",
        "This is a long-distance flag, not an immediate salvation.": "This is a long-term strategy, not an immediate fix.",
        "the final blow before the fruit ripens": "a final measure before the fruit ripens",
        "fruit zones": "durian flesh",
        "This is the data base to know where your orchard is.": "This is the baseline data needed to understand the orchard.",
        "certified low Cd variety": "certified low-Cd fertilizer",
        "Take fruit samples at least 7 days before breaking.": "Take fruit samples at least 7 days before harvest.",
        "Inject AMF or Bacillus preparations": "Apply AMF or Bacillus products",
        "who tests stool?": "who tests fertilizer?",
        "Cd survey in Punjab feces and soil": "Cd survey of fertilizers and soil in Punjab",
    }
    for source, target in replacements.items():
        body = body.replace(source, target)
    return title, summary, category, body


def build() -> None:
    cache = load_cache()
    guides: dict[str, dict[str, str | int | None]] = {}
    files = sorted(SOURCE_DIR.rglob("*.md"))
    for offset, path in enumerate(files, start=1):
        print(f"translating {offset}/{len(files)} {path.relative_to(ROOT)}", flush=True)
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        units, plan = translatable_units(body)
        title, summary, category = translate_many(
            [meta.get("title", ""), meta.get("summary", ""), meta.get("category", "")],
            cache,
        )
        translated_body = rebuild_body(plan, translate_many(units, cache))
        post_id = int(meta["post_id"])
        slug = meta["slug"]
        title, summary, category, translated_body = polish_guide_translation(
            post_id,
            title,
            summary,
            category,
            translated_body,
        )
        guides[str(post_id)] = {
            "post_id": post_id,
            "slug": slug,
            "title": title,
            "summary": summary,
            "category": category,
            "content": translated_body,
            "author": "Agri Price Forecast technical desk",
        }
        save_cache(cache)
        if offset % 8 == 0:
            print(f"translated {offset}/{len(files)}", flush=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(guides, ensure_ascii=False, indent=2), encoding="utf-8")
    save_cache(cache)
    print(f"wrote {len(guides)} guides to {OUTPUT_PATH}")


if __name__ == "__main__":
    build()

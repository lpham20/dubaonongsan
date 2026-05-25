from __future__ import annotations

import html
import json
import re
import threading
from functools import lru_cache
from pathlib import Path

import requests


GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
_MACHINE_CACHE: dict[str, str] = {}
_MACHINE_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def guide_translations_en() -> dict[str, dict]:
    path = Path(__file__).with_name("en_guides.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def localized_language(lang: str | None) -> str:
    return "en" if (lang or "").lower() == "en" else "vi"


def guide_translation_for(post_id: int) -> dict | None:
    return guide_translations_en().get(str(post_id))


def machine_translate_en(text: str | None) -> str:
    if not text:
        return ""
    return machine_translate_many_en([text])[0]


def machine_translate_many_en(texts: list[str | None]) -> list[str]:
    normalized = [(text or "").strip() for text in texts]
    output = [""] * len(normalized)
    missing: list[tuple[int, str]] = []
    with _MACHINE_LOCK:
        for index, text in enumerate(normalized):
            if not text:
                continue
            cached = _MACHINE_CACHE.get(text)
            if cached is not None:
                output[index] = cached
            else:
                missing.append((index, text))

    batch: list[tuple[int, str]] = []
    batch_size = 0
    for item in missing:
        projected = batch_size + len(item[1]) + 32
        if batch and projected > 2400:
            _translate_batch(batch, output)
            batch = []
            batch_size = 0
        batch.append(item)
        batch_size += len(item[1]) + 32
    if batch:
        _translate_batch(batch, output)
    return [value or source for value, source in zip(output, normalized, strict=False)]


def _translate_batch(batch: list[tuple[int, str]], output: list[str]) -> None:
    payload = "\n".join(f"<x{pos}>{text}</x{pos}>" for pos, (_, text) in enumerate(batch))
    translated = _request_translation(payload)
    found = {
        int(match.group(1)): _polish(html.unescape(match.group(2)).strip())
        for match in re.finditer(r"<x(\d+)>(.*?)</x\1>", translated, flags=re.S)
    }
    if len(found) != len(batch):
        for original_index, source in batch:
            output[original_index] = source
        return
    with _MACHINE_LOCK:
        for pos, (original_index, source) in enumerate(batch):
            value = found[pos]
            _MACHINE_CACHE[source] = value
            output[original_index] = value


def _request_translation(payload: str) -> str:
    try:
        response = requests.get(
            GOOGLE_TRANSLATE_URL,
            params={"client": "gtx", "sl": "vi", "tl": "en", "dt": "t", "q": payload},
            headers={"User-Agent": "Mozilla/5.0 MarketAI content localization"},
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        return "".join(item[0] for item in data[0] if item and item[0])
    except Exception:
        return payload


def _polish(text: str) -> str:
    replacements = {
        "Agricultural Forecast": "Agri Price Forecast",
        "Dự báo nông sản": "Agri Price Forecast",
        "garden owner": "orchard owner",
        "durian garden": "durian orchard",
        "coffee garden": "coffee farm",
        "farmers": "growers",
        "Vietnamese dong": "VND",
    }
    for source, target in replacements.items():
        text = re.sub(re.escape(source), target, text, flags=re.I)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

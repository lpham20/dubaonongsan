from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
import re
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import zipfile

import requests

from app.ingestion.http import DEFAULT_HEADERS, fetch_html
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult


SOURCE = "worldbank_pinksheet"
INDEX_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
FALLBACK_EXCEL_URLS = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
    "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx",
)

XLSX_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RELS_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}

COMMODITY_COLUMNS = {
    "dap": {
        "match": ("dap",),
        "quote_type": "FOB US Gulf",
        "slug": "dap",
        "confidence": 0.95,
    },
    "urea": {
        "match": ("urea", "urea_ee_bulk"),
        "quote_type": "FOB Middle East",
        "slug": "urea",
        "confidence": 0.95,
    },
    "potash": {
        "match": ("potassium chloride", "potash", "kcl"),
        "quote_type": "Brazil CFR / FOB Vancouver",
        "slug": "kali_mop",
        "confidence": 0.95,
    },
}


class WorldBankPinkSheetScraper:
    source = SOURCE
    source_url = INDEX_PAGE

    def scrape(self) -> WorldFertilizerScrapeResult:
        excel_url = self._find_pink_sheet_excel_url()
        response = requests.get(excel_url, headers=DEFAULT_HEADERS, timeout=60)
        response.raise_for_status()
        observations = parse_world_bank_pink_sheet_xlsx(response.content, source_url=excel_url)
        return WorldFertilizerScrapeResult(source=self.source, source_url=excel_url, observations=observations)

    def _find_pink_sheet_excel_url(self) -> str:
        try:
            html = fetch_html(INDEX_PAGE, timeout=30)
            links = re.findall(
                r"href=[\"']([^\"']*CMO-Historical-Data-Monthly\.xlsx[^\"']*)[\"']",
                html,
                flags=re.IGNORECASE,
            )
            if links:
                return urljoin(INDEX_PAGE, links[0])
        except requests.RequestException:
            pass
        return FALLBACK_EXCEL_URLS[0]


def parse_world_bank_pink_sheet_xlsx(content: bytes, *, source_url: str) -> list[WorldFertilizerObservation]:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        shared_strings = _shared_strings(archive)
        sheet_path = _sheet_path(archive, "Monthly Prices")
        root = ET.fromstring(archive.read(sheet_path))
        rows = root.findall(".//a:sheetData/a:row", XLSX_NS)
        headers = _row_values(rows, "5", shared_strings)
        codes = _row_values(rows, "7", shared_strings)
        updated_text = _row_values(rows, "4", shared_strings).get("A", "")
        targets = _target_columns(headers, codes)
        observations: list[WorldFertilizerObservation] = []
        for row in rows:
            row_index = int(row.attrib.get("r", "0"))
            if row_index < 8:
                continue
            values = _cell_map(row, shared_strings)
            observed_at = _parse_month(values.get("A"))
            if observed_at is None:
                continue
            for column, meta in targets.items():
                value = _parse_float(values.get(column))
                if value is None or value <= 0:
                    continue
                observations.append(
                    WorldFertilizerObservation(
                        observed_at=observed_at,
                        commodity_slug=meta["slug"],
                        quote_type=meta["quote_type"],
                        source=SOURCE,
                        source_url=source_url,
                        price_usd_per_tonne=round(value, 2),
                        confidence_score=meta["confidence"],
                        raw_json={
                            "series_code": codes.get(column),
                            "commodity_name": headers.get(column),
                            "updated_text": updated_text,
                        },
                    )
                )
        return observations


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("a:si", XLSX_NS):
        values.append("".join(node.text or "" for node in item.findall(".//a:t", XLSX_NS)))
    return values


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("r:Relationship", RELS_NS)}
    for sheet in workbook.findall(".//a:sheet", XLSX_NS):
        if sheet.attrib.get("name") != sheet_name:
            continue
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = relmap.get(rel_id or "")
        if not target:
            break
        return target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
    raise ValueError(f"Sheet not found in World Bank Pink Sheet: {sheet_name}")


def _row_values(rows: list[ET.Element], row_number: str, shared_strings: list[str]) -> dict[str, str]:
    for row in rows:
        if row.attrib.get("r") == row_number:
            return _cell_map(row, shared_strings)
    return {}


def _cell_map(row: ET.Element, shared_strings: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for cell in row.findall("a:c", XLSX_NS):
        reference = cell.attrib.get("r", "")
        match = re.match(r"([A-Z]+)", reference)
        if not match:
            continue
        values[match.group(1)] = _cell_value(cell, shared_strings)
    return values


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.find("a:v", XLSX_NS)
    text = value.text if value is not None and value.text is not None else ""
    if cell.attrib.get("t") == "s" and text:
        return shared_strings[int(text)]
    return text


def _target_columns(headers: dict[str, str], codes: dict[str, str]) -> dict[str, dict]:
    targets: dict[str, dict] = {}
    used_slugs: set[str] = set()
    for column, header in headers.items():
        haystack = f"{header} {codes.get(column, '')}".lower().strip()
        for meta in COMMODITY_COLUMNS.values():
            if meta["slug"] in used_slugs:
                continue
            if any(term in haystack for term in meta["match"]):
                targets[column] = meta
                used_slugs.add(meta["slug"])
                break
    return targets


def _parse_month(value: str | None) -> datetime | None:
    if not value:
        return None
    match = re.match(r"^(\d{4})M(\d{2})$", value.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return datetime(int(match.group(1)), int(match.group(2)), 1, tzinfo=UTC)


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None

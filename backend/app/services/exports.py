from __future__ import annotations

import io
import zipfile
from html import escape
from unicodedata import normalize


def rows_to_xlsx(rows: list[dict], sheet_name: str = "Du lieu") -> bytes:
    headers = [
        ("timestamp", "Ngày"),
        ("province", "Tỉnh"),
        ("region", "Vùng"),
        ("variety", "Giống"),
        ("quality_grade", "Loại"),
        ("min_price_vnd", "Thấp nhất"),
        ("max_price_vnd", "Cao nhất"),
        ("volume_traded_tons", "Tấn"),
        ("data_kind", "Kiểu dữ liệu"),
    ]
    sheet_rows = [_xlsx_row([label for _, label in headers], 1)]
    for index, row in enumerate(rows, start=2):
        sheet_rows.append(_xlsx_row([row.get(key) for key, _ in headers], index))
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(sheet_rows)
        + "</sheetData></worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    with io.BytesIO() as output:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", _content_types())
            archive.writestr("_rels/.rels", _root_rels())
            archive.writestr("xl/workbook.xml", workbook)
            archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels())
            archive.writestr("xl/worksheets/sheet1.xml", worksheet)
        return output.getvalue()


def rows_to_pdf(rows: list[dict], title: str = "Bao cao gia nong san") -> bytes:
    lines = [_ascii(title), "Ngay | Tinh | Giong | Loai | Gia cao nhat"]
    for row in rows[:36]:
        lines.append(
            " | ".join(
                _ascii(str(value or ""))
                for value in [
                    row.get("timestamp"),
                    row.get("province") or row.get("region"),
                    row.get("variety"),
                    row.get("quality_grade"),
                    row.get("max_price_vnd"),
                ]
            )
        )
    content = "BT /F1 10 Tf 46 790 Td " + " Tj 0 -16 Td ".join(f"({_pdf_escape(line[:110])})" for line in lines) + " Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream".encode("latin-1"),
    ]
    return _pdf(objects)


def _xlsx_row(values: list, row_index: int) -> str:
    cells = []
    for column_index, value in enumerate(values, start=1):
        ref = f"{_column_name(column_index)}{row_index}"
        if isinstance(value, (int, float)) and value is not None:
            cells.append(f'<c r="{ref}"><v>{value}</v></c>')
        else:
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value or ""))}</t></is></c>')
    return f'<row r="{row_index}">{"".join(cells)}</row>'


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _content_types() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )


def _root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )


def _ascii(value: str) -> str:
    return normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf(objects: list[bytes]) -> bytes:
    output = io.BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(obj)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
    return output.getvalue()

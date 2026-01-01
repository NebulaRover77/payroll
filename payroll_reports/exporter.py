from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable, Dict, Any, List

ReportRow = Dict[str, Any]


def _stringify(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def export_csv(rows: Iterable[ReportRow], output_path: Path) -> Path:
    rows = list(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        if not rows:
            return output_path
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _stringify(value) for key, value in row.items()})
    return output_path


def _build_pdf_stream(rows: List[ReportRow], title: str) -> str:
    lines: List[str] = []
    y = 760
    lines.append("BT /F1 16 Tf 50 {} Td ({} ) Tj ET".format(y, title))
    y -= 24
    if rows:
        headers = list(rows[0].keys())
        header_text = " | ".join(headers)
        lines.append(f"BT /F1 12 Tf 50 {y} Td ({header_text}) Tj ET")
        y -= 18
        for row in rows:
            row_text = " | ".join(_stringify(row.get(h, "")) for h in headers)
            lines.append(f"BT /F1 10 Tf 50 {y} Td ({row_text}) Tj ET")
            y -= 14
            if y < 50:
                break
    else:
        lines.append(f"BT /F1 12 Tf 50 {y} Td (No rows returned) Tj ET")

    return "\n".join(lines)


def export_pdf(rows: Iterable[ReportRow], output_path: Path, title: str) -> Path:
    rows_list = list(rows)
    stream = _build_pdf_stream(rows_list, title)
    stream_length = len(stream.encode("utf-8"))

    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
        f"4 0 obj << /Length {stream_length} >> stream\n{stream}\nendstream endobj",
        "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
    ]

    header = "%PDF-1.4\n"
    offsets = []
    position = len(header)
    for obj in objects:
        offsets.append(position)
        position += len(obj.encode("utf-8")) + 1

    xref_lines = ["xref", "0 6", "0000000000 65535 f "]
    for offset in offsets:
        xref_lines.append(f"{offset:010} 00000 n ")
    xref_block = "\n".join(xref_lines)

    startxref = position
    trailer = f"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF"

    pdf_body = header + "\n".join(objects) + "\n" + xref_block + "\n" + trailer
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_body.encode("utf-8"))
    return output_path


def export_report(rows: Iterable[ReportRow], output_path: Path, title: str) -> Path:
    if output_path.suffix.lower() == ".csv":
        return export_csv(rows, output_path)
    if output_path.suffix.lower() == ".pdf":
        return export_pdf(rows, output_path, title=title)
    raise ValueError("Unsupported export format. Use .csv or .pdf")

"""PDF letterhead generator for signed audit reports.

Produces a single-page PDF with the Thirsty's Projects LLC letterhead,
the entity number, the Salt Lake City address, and an SHA-256
attestation of the audit body. Renders with reportlab when available;
falls back to a minimal hand-rolled PDF when reportlab is not installed
(keeps the dev environment dep-light and matches the CBEP plan's
"dependency light" discipline).
"""
from __future__ import annotations

import hashlib
import io
import json
from typing import Any

from .ownership import (
    COPYRIGHT_LINE,
    ENTITY_NAME,
    ENTITY_NUMBER,
    PRINCIPAL_OFFICE,
    REGISTERED_AGENT,
)


def _hash_attestation(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _build_minimal_pdf(title: str, lines: list[str]) -> bytes:
    """Hand-rolled one-page PDF (no external dep)."""
    buffer = io.BytesIO()
    objects: list[bytes] = []

    def obj(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    obj(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    content_lines: list[bytes] = []
    for i, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(
            f"BT /F1 12 Tf 50 {770 - 20 * i} Td ({safe}) Tj ET".encode("latin-1")
        )
    content_body = b"\n".join(content_lines)
    obj(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    obj(
        b"<< /Length "
        + str(len(content_body)).encode("ascii")
        + b" >>\nstream\n"
        + content_body
        + b"\nendstream"
    )
    obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, content in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("ascii") + content + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return bytes(out)


def render_audit_report(
    title: str,
    body: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render a signed audit report.

    Returns a dict with:
      - `pdf_bytes`: the raw PDF bytes
      - `sha256`: hash of the body (attestation)
      - `title`, `body`, `metadata`: the inputs
    """
    sha = _hash_attestation(body)
    metadata_json = json.dumps(metadata or {}, sort_keys=True, default=str)
    lines = [
        title,
        "",
        f"From: {ENTITY_NAME} (Entity #{ENTITY_NUMBER})",
        f"Office: {PRINCIPAL_OFFICE}",
        f"Registered agent: {REGISTERED_AGENT}",
        "",
        COPYRIGHT_LINE,
        "",
        f"SHA-256 attestation: {sha}",
        "",
        "---",
        "",
    ]
    for line in body.splitlines():
        if len(line) <= 90:
            lines.append(line)
        else:
            for chunk in [line[i : i + 90] for i in range(0, len(line), 90)]:
                lines.append(chunk)
    lines.extend(["", "---", f"metadata: {metadata_json}"])
    try:
        from reportlab.pdfgen import canvas  # type: ignore[import-untyped]

        # Real reportlab path. Kept for the future; the minimal PDF
        # path below is the default.
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer)
        c.setTitle(title)
        y = 770
        for line in lines:
            c.drawString(50, y, line[:200])
            y -= 14
            if y < 50:
                c.showPage()
                y = 770
        c.save()
        pdf_bytes = buffer.getvalue()
    except ImportError:
        pdf_bytes = _build_minimal_pdf(title, lines)
    return {
        "pdf_bytes": pdf_bytes,
        "sha256": sha,
        "title": title,
        "body": body,
        "metadata": metadata or {},
    }

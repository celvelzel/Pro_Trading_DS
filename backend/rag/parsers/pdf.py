"""Text PDF parser with explicit OCR_REQUIRED diagnostics."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from ..schemas import DocumentValidationError, ParsedSection, MAX_PAGES, text_quality


def parse_pdf(content: bytes) -> list[ParsedSection]:
    try:
        reader = PdfReader(BytesIO(content))
    except Exception as exc:
        raise DocumentValidationError("INVALID_PDF", "PDF 文件损坏或无法读取") from exc
    if len(reader.pages) > MAX_PAGES:
        raise DocumentValidationError("TOO_MANY_PAGES", "PDF 超过 200 页限制")
    sections: list[ParsedSection] = []
    cursor = 0
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            text_quality(text)
            sections.append(ParsedSection(text, None, page_number, cursor, cursor + len(text)))
            cursor += len(text) + 1
    if not sections:
        raise DocumentValidationError("OCR_REQUIRED", "该 PDF 没有可提取文本，不支持扫描件 OCR")
    return sections

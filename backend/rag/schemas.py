"""RAG validation and normalized parser contracts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


DocumentStatus = Literal["uploaded", "parsing", "chunking", "embedding", "ready", "failed", "deleted"]
MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
ALLOWED_EXTENSIONS = {".md": "markdown", ".markdown": "markdown", ".pdf": "pdf"}


class DocumentValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ParsedSection:
    text: str
    section: str | None
    page: int | None
    char_start: int
    char_end: int


@dataclass(frozen=True)
class DocumentChunkData:
    text: str
    section: str | None
    page: int | None
    char_start: int
    char_end: int
    token_count: int
    content_hash: str


def validate_upload(filename: str, content: bytes, content_type: str | None = None) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()
    document_type = ALLOWED_EXTENSIONS.get(extension)
    if document_type is None:
        raise DocumentValidationError("UNSUPPORTED_TYPE", "仅支持 .md、.markdown 和文本型 .pdf")
    if len(content) == 0:
        raise DocumentValidationError("EMPTY_DOCUMENT", "文档内容为空")
    if len(content) > MAX_BYTES:
        raise DocumentValidationError("FILE_TOO_LARGE", "文档超过 10 MB 限制")
    if content_type and document_type == "pdf" and content_type not in {"application/pdf", "application/octet-stream"}:
        raise DocumentValidationError("MIME_MISMATCH", "PDF MIME 类型不匹配")
    if content_type and document_type == "markdown" and content_type not in {"text/markdown", "text/plain", "application/octet-stream"}:
        raise DocumentValidationError("MIME_MISMATCH", "Markdown MIME 类型不匹配")
    return document_type, hashlib.sha256(content).hexdigest()


def text_quality(text: str) -> None:
    if not text.strip():
        raise DocumentValidationError("EMPTY_TEXT", "文档解析后没有文本")
    replacement_ratio = text.count("\ufffd") / max(1, len(text))
    if replacement_ratio > 0.02:
        raise DocumentValidationError("INVALID_TEXT", "文档乱码比例过高")
